package com.aqss.bodyguard.uiprobe;

import android.app.Activity;
import android.app.AlertDialog;
import android.app.Instrumentation;
import android.content.Intent;
import android.graphics.Bitmap;
import android.media.AudioManager;
import android.media.AudioRouting;
import android.os.Bundle;
import android.os.SystemClock;
import android.util.Base64;
import android.widget.Button;
import android.widget.TextView;
import java.io.File;
import java.io.FileOutputStream;
import java.lang.reflect.Field;
import java.util.List;
import java.util.concurrent.atomic.AtomicBoolean;

/** Observer APK only: real framework check plus explicitly synthetic admission/callback tests. */
public final class QuietOutputProbe extends CameraCaptureProbe {
    private String phase = "inventory entry";
    private Object microphone;
    private Object inputLease;
    private static Object read(Object object, String name) throws Exception {
        Field field = object.getClass().getDeclaredField(name); field.setAccessible(true); return field.get(object);
    }
    private static Object get(Object object, String name) throws Exception { return object.getClass().getMethod(name).invoke(object); }
    private void focus(Activity target) {
        long end = SystemClock.uptimeMillis() + 5000; boolean[] ready = new boolean[1];
        while (SystemClock.uptimeMillis() < end) {
            runOnMainSync(() -> ready[0] = target.hasWindowFocus());
            if (ready[0]) return;
            SystemClock.sleep(25);
        }
        throw new AssertionError("Expected focused foreground activity");
    }
    private void press(String label) {
        focus(activity);
        boolean[] clicked = {false};
        runOnMainSync(() -> clicked[0] = click(activity.getWindow().getDecorView(), label));
        require(clicked[0], "Missing control: " + label);
        waitForIdleSync();
    }
    private Object completed() throws Exception {
        long end = SystemClock.uptimeMillis() + 10000;
        while (SystemClock.uptimeMillis() < end) {
            Object capture = read(activity, "capture");
            if (capture != null && ((AtomicBoolean) get(capture, "getCompleted")).get()) {
                waitForIdleSync();
                if (read(activity, "lastResult") != null) return read(activity, "lastResult");
            }
            SystemClock.sleep(25);
        }
        throw new AssertionError("Worker did not publish a bounded check result");
    }
    private void shot(String name) throws Exception {
        waitForIdleSync(); SystemClock.sleep(150);
        Bitmap bitmap = getUiAutomation().takeScreenshot(); require(bitmap != null, "No native screenshot");
        try (FileOutputStream out = new FileOutputStream(new File(getTargetContext().getFilesDir(), name + ".png"))) {
            require(bitmap.compress(Bitmap.CompressFormat.PNG, 100, out), "Cannot retain native screenshot");
        } finally { bitmap.recycle(); }
    }
    @Override public void onStart() {
        Bundle receipt = new Bundle(); Activity inventory = null; ActivityMonitor chooser = null;
        try {
            inventory = startActivitySync(new Intent().setClassName(getTargetContext().getPackageName(),
                    "com.aqss.bodyguard.prototype.OutputInventoryActivity")
                    .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TASK));
            activity = inventory; waitForIdleSync(); focus(inventory);
            ActivityMonitor open = addMonitor("com.aqss.bodyguard.prototype.QuietOutputCheckActivity", null, false);
            press("Quiet output check");
            Activity quiet = waitForMonitorWithTimeout(open, 5000); removeMonitor(open);
            require(quiet != null, "Output inventory did not open the quiet check");
            activity = quiet; waitForIdleSync(); waitForText("Ready for a quiet check");
            require(read(activity, "capture") == null, "Entering the screen started a backend");

            phase = "synthetic input admission";
            ClassLoader loader = getTargetContext().getClassLoader();
            Class<?> gateType = loader.loadClass("com.aqss.nativefeedback.ForegroundMicrophoneGate");
            Object companion = gateType.getField("Companion").get(null);
            microphone = get(companion, "getProcess"); inputLease = get(microphone, "acquire");
            require(inputLease != null, "Fixture input reservation unavailable");
            press("Start quiet check"); Object busy = completed();
            require(!((Boolean) get(busy, "getAllocationEntered")), "Busy input allocated a native track");
            require(((List<?>) get(busy, "getTrace")).isEmpty(), "Busy admission entered backend work");
            shot("quiet-output-busy");
            require((Boolean) microphone.getClass().getMethod("release", inputLease.getClass(), boolean.class)
                    .invoke(microphone, inputLease, true), "Fixture lease did not release"); inputLease = null;

            phase = "real framework output";
            press("Start quiet check"); Object result = completed();
            require((Boolean) get(result, "getTrackOpened"), "Reference emulator could not construct the requested stream");
            require(Boolean.TRUE.equals(get(result, "getZeroGainAccepted")), "Zero app gain was not accepted");
            require((Boolean) get(result, "getCleanupSucceeded"), "Native cleanup remained unresolved");
            require(!((Boolean) get(result, "getPhysicalOutputVerified")), "Framework check claimed physical output");
            int accepted = (Integer) get(result, "getAcceptedSamples");
            int attempts = (Integer) get(result, "getAttempts");
            require(accepted >= 0 && accepted <= 256 && attempts <= 8, "Unbounded accounting");
            shot("quiet-output-main");

            phase = "review and exact share intent";
            press("Review check report");
            AlertDialog dialog = (AlertDialog) read(activity, "reportDialog");
            require(dialog != null && dialog.isShowing(), "Native report dialog missing");
            TextView preview = dialog.getWindow().getDecorView().findViewWithTag("quiet-output-report-preview");
            require(preview != null, "Report text missing");
            String frozen = preview.getText().toString();
            require(frozen.startsWith("Audio Bodyguard quiet output check (v1)"), "Report envelope missing");
            require(frozen.contains("Physical output and protection: Not verified"), "Physical uncertainty missing");
            require(frozen.contains("Control clock: elapsed realtime milliseconds (includes sleep)"), "Clock domain missing");
            shot("quiet-output-report");
            final int[] sent = {0};
            chooser = new ActivityMonitor() {
                @Override public ActivityResult onStartActivity(Intent intent) {
                    if (!Intent.ACTION_CHOOSER.equals(intent.getAction())) return null;
                    Intent send = intent.getParcelableExtra(Intent.EXTRA_INTENT);
                    require(send != null && Intent.ACTION_SEND.equals(send.getAction()), "Missing native send intent");
                    require("text/plain".equals(send.getType()), "Unexpected report MIME type");
                    require(frozen.equals(send.getStringExtra(Intent.EXTRA_TEXT)), "Share differs from frozen preview");
                    sent[0]++; return new ActivityResult(Activity.RESULT_CANCELED, null);
                }
            };
            addMonitor(chooser);
            runOnMainSync(() -> require(click(dialog.getWindow().getDecorView(), "Share check report"), "Share control missing"));
            waitForIdleSync(); require(sent[0] == 1, "Expected one exact share intent");
            require(frozen.equals(preview.getText().toString()), "Cancelled share changed reviewed text");
            removeMonitor(chooser); chooser = null;
            runOnMainSync(dialog::dismiss);

            phase = "configuration retention";
            Object capture = read(activity, "capture");
            ActivityMonitor rotate = addMonitor("com.aqss.bodyguard.prototype.QuietOutputCheckActivity", null, false);
            runOnMainSync(() -> activity.recreate());
            Activity replacement = waitForMonitorWithTimeout(rotate, 5000); removeMonitor(rotate);
            require(replacement != null && replacement != activity, "Activity recreation missing");
            activity = replacement; waitForIdleSync(); focus(activity);
            require(read(activity, "capture") == capture, "Rotation replaced the completed run with new work");
            press("Review check report");
            AlertDialog restored = (AlertDialog) read(activity, "reportDialog");
            TextView restoredPreview = restored.getWindow().getDecorView().findViewWithTag("quiet-output-report-preview");
            require(frozen.equals(restoredPreview.getText().toString()), "Rotation changed the reviewed snapshot");
            shot("quiet-output-rotated"); runOnMainSync(restored::dismiss);

            phase = "back to immediate parent";
            press("Back"); waitForIdleSync(); focus(inventory);
            require(!inventory.isDestroyed(), "Back destroyed the original inventory");
            receipt.putString("quiet_output", "passed: busy input no allocation, real zero-gain framework stream, bounded accounting, native cleanup return, immutable exact share intent (cancelled by observer), no restart on recreation, Back returns to original inventory; physical output unverified");
            receipt.putString("quiet_report_b64", Base64.encodeToString(frozen.getBytes(java.nio.charset.StandardCharsets.UTF_8), Base64.NO_WRAP));
            receipt.putInt("accepted_samples", accepted); receipt.putInt("write_attempts", attempts);
            finish(Activity.RESULT_OK, receipt);
        } catch (Exception | AssertionError error) {
            error.printStackTrace(); receipt.putString("quiet_output_error", phase + ": " + error);
            try { if (activity != null) shot("quiet-output-failure"); } catch (Exception ignored) {}
            finish(Activity.RESULT_CANCELED, receipt);
        } finally {
            if (chooser != null) removeMonitor(chooser);
            if (inputLease != null) try {
                microphone.getClass().getMethod("release", inputLease.getClass(), boolean.class).invoke(microphone, inputLease, true);
            } catch (Exception ignored) {}
            if (activity != null) runOnMainSync(() -> activity.finish());
            Activity closing = inventory; if (closing != null) runOnMainSync(closing::finish);
        }
    }
}
