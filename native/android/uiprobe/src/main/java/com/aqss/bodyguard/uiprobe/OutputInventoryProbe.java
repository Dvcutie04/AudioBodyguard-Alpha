package com.aqss.bodyguard.uiprobe;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.Context;
import android.content.Intent;
import android.media.AudioDeviceCallback;
import android.media.AudioDeviceInfo;
import android.media.AudioManager;
import android.os.Bundle;
import android.os.SystemClock;
import android.widget.TextView;
import android.widget.Button;
import java.lang.reflect.Field;

/** Test APK only. Delivers synthetic change callbacks with real OS descriptors.
 * This tests invalidation/lifecycle, not actual peripheral removal or routing. */
public final class OutputInventoryProbe extends CameraCaptureProbe {
    private static final String IDLE = "Not read yet. Tap Refresh outputs.";
    private static final String CHANGED = "Output list needs a fresh check. Tap Refresh outputs.";
    private String phase = "launch";
    private int refreshCount;

    @Override public void onStart() {
        Bundle result = new Bundle();
        Activity overlay = null;
        try {
            Intent launch = new Intent().setClassName(getTargetContext().getPackageName(),
                    "com.aqss.bodyguard.prototype.OutputInventoryActivity")
                    .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TASK);
            activity = startActivitySync(launch);
            waitForIdleSync(); waitForText(IDLE);
            refresh();
            String original = details();
            require(original.contains("Advertised sample rates:"), "Actual inventory rows missing");
            recordScreen("output-freshness-read");

            Field callbackField;
            try { callbackField = field("deviceCallback"); }
            catch (NoSuchFieldException error) {
                throw new AssertionError("No device-change observer is registered; a refreshed output list cannot be invalidated");
            }
            AudioDeviceCallback callback = (AudioDeviceCallback) callbackField.get(activity);
            require(callback != null, "Foreground output change observer missing");
            AudioManager manager = (AudioManager) getTargetContext().getSystemService(Context.AUDIO_SERVICE);
            AudioDeviceInfo[] outputs = manager.getDevices(AudioManager.GET_DEVICES_OUTPUTS);
            AudioDeviceInfo[] inputs = manager.getDevices(AudioManager.GET_DEVICES_INPUTS);
            require(outputs.length > 0 && inputs.length > 0, "Configured emulator needs output/input descriptors");

            phase = "remove notice";
            runOnMainSync(() -> callback.onAudioDevicesRemoved(outputs));
            assertCleared(); recordScreen("output-freshness-removed");
            // Repeated notifications cannot replace the guidance or reread.
            runOnMainSync(() -> callback.onAudioDevicesAdded(outputs));
            assertCleared();
            refresh();
            require(original.equals(details()), "Explicit refresh did not reread the unchanged OS inventory");
            runOnMainSync(() -> callback.onAudioDevicesAdded(outputs));
            assertCleared(); recordScreen("output-freshness-added");
            refresh();
            String refreshed = details();
            runOnMainSync(() -> {
                callback.onAudioDevicesAdded(inputs);
                callback.onAudioDevicesRemoved(inputs);
                callback.onAudioDevicesAdded(new AudioDeviceInfo[0]);
                callback.onAudioDevicesRemoved(new AudioDeviceInfo[0]);
            });
            require(refreshed.equals(details()), "Input-only or empty notifications invalidated outputs");

            phase = "open review";
            waitForInventoryFocus();
            runOnMainSync(() -> require(click(activity.getWindow().getDecorView(), "Review output report"), "Review control missing"));
            waitForIdleSync();
            AlertDialog review = (AlertDialog) field("reportDialog").get(activity);
            require(review != null && review.isShowing(), "Review must open an actual native dialog");
            TextView preview = (TextView) review.getWindow().getDecorView().findViewWithTag("output-report-preview");
            require(preview != null, "Native report preview missing");
            String[] frozen = new String[1];
            runOnMainSync(() -> frozen[0] = preview.getText().toString());
            require(frozen[0].startsWith("Audio Bodyguard output inventory (v1)"), "Report envelope missing");
            phase = "notice during review";
            runOnMainSync(() -> callback.onAudioDevicesRemoved(outputs));
            assertCleared();
            runOnMainSync(() -> require(frozen[0].equals(preview.getText().toString()), "Notice rewrote the historical report under review"));
            require(review.isShowing(), "A notice unexpectedly navigated away from the reviewed copy");
            runOnMainSync(review::dismiss);
            recordScreen("output-freshness-report-cleared");
            refresh();

            phase = "pause and resume";
            overlay = startActivitySync(new Intent().setClassName(getTargetContext().getPackageName(),
                    "com.aqss.bodyguard.prototype.SetupGuideActivity").addFlags(Intent.FLAG_ACTIVITY_NEW_TASK));
            waitForIdleSync();
            require(!field("visible").getBoolean(activity), "Inventory did not pause behind the guide");
            require(callbackField.get(activity) == null, "Paused screen retained its active callback");
            require(IDLE.equals(details()), "Pause retained old device details");
            runOnMainSync(() -> callback.onAudioDevicesRemoved(outputs));
            require(IDLE.equals(details()), "Retired callback changed the paused screen");
            Activity closing = overlay;
            runOnMainSync(closing::finish); overlay = null;
            waitForIdleSync(); waitForText(IDLE);
            waitForInventoryFocus();
            AudioDeviceCallback current = (AudioDeviceCallback) callbackField.get(activity);
            require(current != null && current != callback, "Resume reused a retired callback");
            refresh();
            String resumed = details();
            runOnMainSync(() -> callback.onAudioDevicesRemoved(outputs));
            require(resumed.equals(details()), "Late old callback cleared a newer foreground snapshot");
            recordScreen("output-freshness-resumed");
            runOnMainSync(() -> current.onAudioDevicesRemoved(outputs));
            assertCleared();
            phase = "closed inventory cleanup";
            runOnMainSync(() -> activity.finish()); waitForIdleSync();
            // finish() requests a lifecycle transition; an idle app queue can
            // precede the system's pause/destroy transaction. Assert cleanup
            // after actual destruction rather than treating the request as it.
            long closedDeadline = SystemClock.uptimeMillis() + 5000;
            boolean[] destroyed = new boolean[1];
            while (SystemClock.uptimeMillis() < closedDeadline) {
                runOnMainSync(() -> destroyed[0] = activity.isDestroyed());
                if (destroyed[0]) break;
                SystemClock.sleep(50);
            }
            require(destroyed[0], "Inventory finish request did not reach destruction");
            require(callbackField.get(activity) == null, "Closed screen retained its active callback");
            runOnMainSync(() -> current.onAudioDevicesAdded(outputs));
            require(IDLE.equals(details()), "Callback changed closed inventory details");

            result.putString("output_inventory", "passed: synthetic output add/remove callbacks clear real inventory and disable new Review; an already reviewed historical copy stays immutable; no automatic reread; explicit refresh; input-only/empty ignored; pause unregisters; resume renews; old and closed callbacks ignored; route/format remain unknown. No physical disconnect or route qualification.");
            finish(Activity.RESULT_OK, result);
        } catch (Exception | AssertionError error) {
            result.putString("output_inventory_error", phase + ": " + error);
            if (activity != null) {
                try {
                    result.putString("output_inventory_details", details());
                    boolean[] focus = new boolean[1];
                    runOnMainSync(() -> focus[0] = activity.hasWindowFocus());
                    result.putBoolean("output_inventory_focus", focus[0]);
                    recordScreen("output-freshness-failure");
                } catch (Exception | AssertionError diagnostic) {
                    result.putString("output_inventory_diagnostic", diagnostic.toString());
                }
            }
            finish(Activity.RESULT_CANCELED, result);
        } finally {
            if (overlay != null) { Activity closing = overlay; runOnMainSync(closing::finish); }
            if (activity != null && !activity.isFinishing()) runOnMainSync(() -> activity.finish());
        }
    }

    private Field field(String name) throws NoSuchFieldException {
        Field value = activity.getClass().getDeclaredField(name);
        value.setAccessible(true); return value;
    }
    private String details() throws Exception {
        TextView view = (TextView) field("results").get(activity);
        String[] value = new String[1];
        runOnMainSync(() -> value[0] = view.getText().toString());
        return value[0];
    }
    private void refresh() {
        phase = "refresh " + (++refreshCount);
        waitForIdleSync();
        waitForInventoryFocus();
        runOnMainSync(() -> require(click(activity.getWindow().getDecorView(), "Refresh outputs"), "Refresh button missing"));
        waitForText("Snapshot only.");
    }
    private void waitForInventoryFocus() {
        long deadline = SystemClock.uptimeMillis() + 5000;
        while (SystemClock.uptimeMillis() < deadline) {
            boolean[] focused = new boolean[1];
            runOnMainSync(() -> focused[0] = !activity.isFinishing() && !activity.isDestroyed() && activity.hasWindowFocus());
            if (focused[0]) return;
            SystemClock.sleep(50);
        }
        throw new AssertionError("Inventory window never became interactive before the test click");
    }
    private void assertCleared() throws Exception {
        waitForText(CHANGED);
        require(CHANGED.equals(details()), "Old output rows remained after invalidation");
        require(field("reportSnapshot").get(activity) == null, "A withdrawn inventory retained a new-report payload");
        require(!((Button) field("reviewButton").get(activity)).isEnabled(), "Withdrawn inventory left Review enabled");
        waitForText("Selected playback route: Unknown"); waitForText("Negotiated format: Unknown");
    }
}
