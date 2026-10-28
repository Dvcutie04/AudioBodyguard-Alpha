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
import android.widget.EditText;
import android.widget.TextView;
import android.view.View;
import android.view.ViewGroup;
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
    private boolean requireSetupNotes;
    @Override public void onCreate(Bundle arguments) {
        requireSetupNotes = arguments != null && "1".equals(arguments.getString("quiet_setup"));
        super.onCreate(arguments);
    }
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
    private void focus(AlertDialog target) {
        long end = SystemClock.uptimeMillis() + 5000; boolean[] ready = new boolean[1];
        while (SystemClock.uptimeMillis() < end) {
            runOnMainSync(() -> ready[0] = target.isShowing() && target.getWindow() != null &&
                    target.getWindow().getDecorView().hasWindowFocus());
            if (ready[0]) return;
            SystemClock.sleep(25);
        }
        throw new AssertionError("Expected focused report window before sharing");
    }
    private void press(String label) {
        focus(activity);
        boolean[] clicked = {false};
        runOnMainSync(() -> clicked[0] = clickControl(activity.getWindow().getDecorView(), label));
        require(clicked[0], "Missing control: " + label);
        waitForIdleSync();
    }
    private boolean clickControl(View view, String label) {
        boolean named = view instanceof TextView && label.contentEquals(((TextView) view).getText());
        named |= view.getContentDescription() != null && label.contentEquals(view.getContentDescription());
        if (named && view.isShown() && view.isEnabled() && view.isClickable()) return view.performClick();
        if (view instanceof ViewGroup) {
            ViewGroup group = (ViewGroup) view;
            for (int i = 0; i < group.getChildCount(); i++) if (clickControl(group.getChildAt(i), label)) return true;
        }
        return false;
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
    private EditText entry(View view, String title) {
        if (view instanceof EditText && view.getContentDescription() != null && title.contentEquals(view.getContentDescription())) return (EditText) view;
        if (view instanceof ViewGroup) {
            ViewGroup group = (ViewGroup) view;
            for (int i = 0; i < group.getChildCount(); i++) {
                EditText found = entry(group.getChildAt(i), title); if (found != null) return found;
            }
        }
        return null;
    }
    private void note(String title, String text) {
        EditText[] field = {null};
        runOnMainSync(() -> field[0] = entry(activity.getWindow().getDecorView(), title));
        require(field[0] != null, "Missing setup field: " + title);
        runOnMainSync(() -> field[0].setText(text)); waitForIdleSync();
    }
    private String setupPreview() {
        TextView[] preview = {null};
        runOnMainSync(() -> preview[0] = activity.getWindow().getDecorView().findViewWithTag("test-setup-report-preview"));
        require(preview[0] != null, "Missing actual setup preview"); return preview[0].getText().toString();
    }
    private void recreateQuiet() {
        Activity original = activity;
        ActivityMonitor monitor = addMonitor("com.aqss.bodyguard.prototype.QuietOutputCheckActivity", null, false);
        runOnMainSync(original::recreate);
        Activity replacement = waitForMonitorWithTimeout(monitor, 5000); removeMonitor(monitor);
        require(replacement != null && replacement != original, "Quiet screen recreation missing");
        activity = replacement; waitForIdleSync(); focus(replacement);
    }
    private void guidanceLifecycle(Activity inventory, Object capture, String frozen, Bundle receipt) throws Exception {
        phase = "synthetic pending-completion presentation";
        String previous = ((TextView) read(activity, "status")).getText().toString();
        AtomicBoolean completedFlag = (AtomicBoolean) get(capture, "getCompleted");
        // The real stream has already returned and released. Only the observer
        // toggles this completion flag to inspect a retained closing screen.
        completedFlag.set(false);
        try {
            recreateQuiet(); waitForText("Closing quiet check…");
            require(read(activity, "capture") == capture, "Closing recreation created another worker");
            require(!((Button) read(activity, "start")).isEnabled(), "Closing screen offered another Start");
            require(!((Button) read(activity, "review")).isEnabled(), "Closing screen offered a completed report");
            shot("quiet-output-pending-close");
        } finally { completedFlag.set(true); }
        waitForText(previous);
        require(((Button) read(activity, "start")).isEnabled(), "Completed reference check did not restore manual Start");

        phase = "synthetic process cleanup quarantine";
        ClassLoader loader = getTargetContext().getClassLoader();
        Class<?> gateType = loader.loadClass("com.aqss.nativefeedback.ForegroundAudioExclusion");
        Class<?> toolType = loader.loadClass("com.aqss.nativefeedback.ForegroundAudioExclusion$Tool");
        Object gate = get(gateType.getField("Companion").get(null), "getProcess");
        Object outputTool = toolType.getField("OUTPUT").get(null);
        Object lease = gateType.getMethod("acquire", toolType, Object.class).invoke(gate, outputTool, new Object());
        require(lease != null, "Reference native run retained the exclusion lease");
        require(!((Boolean) gateType.getMethod("release", lease.getClass(), boolean.class).invoke(gate, lease, false)),
                "Synthetic failed cleanup unexpectedly released its lease");
        require((Boolean) get(gate, "getBlocked"), "Synthetic cleanup did not retain process quarantine");
        recreateQuiet();
        String retained = ((TextView) read(activity, "status")).getText().toString();
        require(retained.contains("unresolved cleanup") && retained.indexOf("Review") >= 0 && retained.indexOf("Review") < retained.indexOf("force stop"),
                "Cleanup recovery did not preserve the report before force stop");
        require(!((Button) read(activity, "start")).isEnabled(), "Quarantine offered another Start");
        require(((Button) read(activity, "review")).isEnabled(), "Quarantine hid the retained report");
        shot("quiet-output-blocked-report");
        press("Review check report"); AlertDialog dialog = (AlertDialog) read(activity, "reportDialog");
        focus(dialog);
        TextView preview = dialog.getWindow().getDecorView().findViewWithTag("quiet-output-report-preview");
        require(preview != null && frozen.equals(preview.getText().toString()), "Quarantine rewrote the historical report");
        final int[] sent = {0};
        ActivityMonitor share = new ActivityMonitor() {
            @Override public ActivityResult onStartActivity(Intent intent) {
                if (!Intent.ACTION_CHOOSER.equals(intent.getAction())) return null;
                Intent send = intent.getParcelableExtra(Intent.EXTRA_INTENT);
                require(send != null && Intent.ACTION_SEND.equals(send.getAction()) && "text/plain".equals(send.getType()),
                        "Blocked report did not offer plain-text sharing");
                require(frozen.equals(send.getStringExtra(Intent.EXTRA_TEXT)), "Blocked share changed the historical report");
                sent[0]++; return new ActivityResult(Activity.RESULT_CANCELED, null);
            }
        };
        addMonitor(share);
        try {
            runOnMainSync(() -> require(click(dialog.getWindow().getDecorView(), "Share check report"), "Blocked report lost Share"));
            waitForIdleSync(); require(sent[0] == 1, "Blocked report did not send one exact share intent");
            require(frozen.equals(preview.getText().toString()), "Cancelled blocked share changed the report");
        } finally { removeMonitor(share); }
        runOnMainSync(dialog::dismiss);
        receipt.putString("quiet_guidance_report_status_b64", Base64.encodeToString(retained.getBytes(java.nio.charset.StandardCharsets.UTF_8), Base64.NO_WRAP));

        phase = "new screen during process quarantine";
        press("Back"); activity = inventory; waitForIdleSync(); focus(inventory);
        ActivityMonitor open = addMonitor("com.aqss.bodyguard.prototype.QuietOutputCheckActivity", null, false);
        press("Quiet output check"); Activity fresh = waitForMonitorWithTimeout(open, 5000); removeMonitor(open);
        require(fresh != null, "Quarantined screen could not be inspected"); activity = fresh; waitForIdleSync(); focus(fresh);
        String empty = ((TextView) read(fresh, "status")).getText().toString();
        require(read(fresh, "capture") == null, "Entering a quarantined screen started another worker");
        require(empty.contains("unresolved cleanup") && empty.contains("Force stop") && !empty.contains("Review"),
                "Empty quarantined screen offered a nonexistent report or a ready state");
        require(!((Button) read(fresh, "start")).isEnabled() && !((Button) read(fresh, "review")).isEnabled(),
                "Empty quarantined screen enabled Start or Review");
        require((Boolean) get(gate, "getBlocked"), "Presentation cleared sticky process quarantine");
        shot("quiet-output-blocked-entry");
        receipt.putString("quiet_guidance_entry_status_b64", Base64.encodeToString(empty.getBytes(java.nio.charset.StandardCharsets.UTF_8), Base64.NO_WRAP));
        receipt.putString("quiet_guidance", "passed: actual busy admission; synthetic pending-completion retention and sticky cleanup quarantine; original report/share retained; fresh entry starts no worker");
    }
    private void combinedSetup(AlertDialog dialog, String frozen, Bundle receipt) throws Exception {
        Activity parent = activity; Object source = read(parent, "lastReport"), capture = read(parent, "capture");
        ActivityMonitor open = addMonitor("com.aqss.bodyguard.prototype.TestSetupActivity", null, false);
        boolean[] clicked = {false};
        runOnMainSync(() -> clicked[0] = click(dialog.getWindow().getDecorView(), "Add setup notes"));
        require(clicked[0], "Quiet report has no Add setup notes control");
        Activity child = waitForMonitorWithTimeout(open, 5000); removeMonitor(open);
        require(child != null, "Quiet report did not open setup notes"); activity = child; waitForIdleSync(); focus(child);
        require(read(child, "quietReport") == source, "Handoff did not preserve the exact typed quiet snapshot");
        require(!child.getIntent().hasExtra(Intent.EXTRA_TEXT), "Report text was serialized in an Intent");
        note("Intended output", "Phone speaker"); note("Setup constraints", "No calibration");
        press("Review setup report"); String joined = setupPreview();
        require(joined.startsWith("Audio Bodyguard test setup (v2)"), "Missing combined quiet envelope");
        require(joined.endsWith(frozen), "Original quiet report changed during handoff");
        require(joined.contains("Intended output: \"Phone speaker\""), "Notes missing from actual preview");
        require(joined.contains("Physical output and protection: Not verified"), "Physical uncertainty missing");
        shot("quiet-setup-report");
        final int[] sent = {0};
        ActivityMonitor share = new ActivityMonitor() {
            @Override public ActivityResult onStartActivity(Intent intent) {
                if (!Intent.ACTION_CHOOSER.equals(intent.getAction())) return null;
                Intent send = intent.getParcelableExtra(Intent.EXTRA_INTENT);
                require(send != null && Intent.ACTION_SEND.equals(send.getAction()) && "text/plain".equals(send.getType()), "Combined share is not plain text");
                require(joined.equals(send.getStringExtra(Intent.EXTRA_TEXT)), "Combined share differs from actual preview");
                sent[0]++; return new ActivityResult(Activity.RESULT_CANCELED, null);
            }
        };
        addMonitor(share);
        try { press("Share setup report"); require(sent[0] == 1, "Expected one cancelled combined share"); }
        finally { removeMonitor(share); }
        require(setupPreview().equals(joined), "Cancelled share changed the frozen combination");
        ActivityMonitor rotate = addMonitor("com.aqss.bodyguard.prototype.TestSetupActivity", null, false);
        runOnMainSync(child::recreate); Activity replacement = waitForMonitorWithTimeout(rotate, 5000); removeMonitor(rotate);
        require(replacement != null && replacement != child, "Setup recreation missing");
        activity = replacement; waitForIdleSync(); focus(replacement);
        require(read(replacement, "quietReport") == source && setupPreview().equals(joined), "Recreation lost the included quiet report");
        shot("quiet-setup-rotated");
        press("Back"); press("Clear notes"); press("Review setup report");
        String cleared = setupPreview();
        require(cleared.endsWith(frozen) && cleared.contains("Intended output: Unknown"), "Clear notes discarded quiet data or retained old notes");
        press("Back"); note("Intended output", "Phone speaker"); press("Remove output details"); press("Review setup report");
        String removed = setupPreview();
        require(removed.contains("Intended output: \"Phone speaker\"") && !removed.contains("Attached quiet check report"), "Remove output details discarded notes or retained quiet data");
        shot("quiet-setup-removed"); press("Back"); press("Back"); activity = parent; waitForIdleSync();
        require(read(parent, "capture") == capture, "Notes launched another quiet worker");
        require(dialog.isShowing() && frozen.equals(((TextView) dialog.getWindow().getDecorView().findViewWithTag("quiet-output-report-preview")).getText().toString()), "Back did not return to the original quiet report");
        receipt.putString("quiet_setup", "passed: typed single-use handoff, exact combined preview/intent, recreation, independent Clear/remove and Back; no new output work");
        receipt.putString("quiet_setup_b64", Base64.encodeToString(joined.getBytes(java.nio.charset.StandardCharsets.UTF_8), Base64.NO_WRAP));
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
            waitForText("Another audio tool is running or closing. Stop it and wait for it to close before tapping Start.");
            require(((TextView) read(activity, "status")).getText().toString().contains("wait for it to close"),
                    "Busy guidance did not distinguish stopping from completed cleanup");
            shot("quiet-output-busy");
            phase = "denied-admission report";
            press("Review check report");
            AlertDialog busyDialog = (AlertDialog) read(activity, "reportDialog");
            require(busyDialog != null && busyDialog.isShowing(), "Missing denied-admission report");
            TextView busyPreview = busyDialog.getWindow().getDecorView().findViewWithTag("quiet-output-report-preview");
            require(busyPreview != null, "Missing denied-admission report text");
            String busyText = busyPreview.getText().toString();
            require(busyText.contains("Resource cleanup calls: Not entered") && !busyText.contains("Resource cleanup calls: Returned"),
                    "Denied-admission report invented returned cleanup calls");
            require(busyText.contains("Known accepted samples: 0\nWrite attempts: 0"), "Denied admission reported output work");
            receipt.putString("quiet_busy_report_b64", Base64.encodeToString(busyText.getBytes(java.nio.charset.StandardCharsets.UTF_8), Base64.NO_WRAP));
            shot("quiet-output-busy-report"); runOnMainSync(busyDialog::dismiss);
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
            if (requireSetupNotes) { phase = "quiet report and setup notes"; combinedSetup(dialog, frozen, receipt); }
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

            guidanceLifecycle(inventory, capture, frozen, receipt);

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
