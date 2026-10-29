package com.aqss.bodyguard.uiprobe;

import android.Manifest;
import android.app.Activity;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.graphics.Bitmap;
import android.os.Bundle;
import android.os.SystemClock;
import android.util.Base64;
import android.view.View;
import android.view.accessibility.AccessibilityNodeInfo;
import android.widget.Button;
import android.widget.TextView;
import java.io.File;
import java.io.FileOutputStream;
import java.lang.reflect.Field;
import java.util.List;
import java.util.concurrent.atomic.AtomicBoolean;

/** Test APK only. Synthetic ownership/quarantine; never an actual delayed recorder or cleanup failure. */
public final class SoundAvailabilityProbe extends CameraCaptureProbe {
    private static final String BUSY = "Another audio tool is running or closing. Stop it and wait for it to close before tapping Start.";
    private static final String BLOCKED = "Audio tools are blocked by unresolved cleanup. Review or share any reports you want to keep, then force stop this app in Android Settings before starting a new check.";
    private String phase = "synthetic output reservation";
    private static Object read(Object target, String name) throws Exception {
        Field field = target.getClass().getDeclaredField(name); field.setAccessible(true); return field.get(target);
    }
    private static Object get(Object target, String name) throws Exception { return target.getClass().getMethod(name).invoke(target); }
    private void focus() {
        long end = SystemClock.uptimeMillis() + 5000; boolean[] ready = {false};
        while (SystemClock.uptimeMillis() < end) {
            runOnMainSync(() -> ready[0] = activity.hasWindowFocus());
            if (ready[0]) return;
            SystemClock.sleep(25);
        }
        throw new AssertionError("Sound-check window did not regain focus");
    }
    private void press(String label) {
        focus(); runOnMainSync(() -> require(click(activity.getWindow().getDecorView(), label), "Missing button: " + label));
        waitForIdleSync();
    }
    private String status() throws Exception { return ((TextView) read(activity, "status")).getText().toString(); }
    private void noCapture() throws Exception {
        require(read(activity, "capture") == null, "Presentation or retry created a microphone capture");
        require(!((Boolean) read(activity, "permissionGuidance")), "Unavailable audio requested microphone permission");
    }
    private void recreate() {
        Activity original = activity; waitForIdleSync(); focus();
        ActivityMonitor monitor = addMonitor(original.getClass().getName(), null, false);
        Activity replacement = null; long end = SystemClock.uptimeMillis() + 10000;
        try {
            runOnMainSync(original::recreate);
            while (SystemClock.uptimeMillis() < end) {
                Activity candidate = waitForMonitorWithTimeout(monitor, Math.max(1, end - SystemClock.uptimeMillis()));
                if (candidate != null && candidate != original) { replacement = candidate; break; }
            }
        } finally { removeMonitor(monitor); }
        require(replacement != null, "Distinct sound-check recreation missing");
        activity = replacement; waitForIdleSync(); focus();
    }
    private void shot(String name) throws Exception {
        waitForIdleSync(); SystemClock.sleep(150);
        Bitmap image = getUiAutomation().takeScreenshot(); require(image != null, "Screenshot unavailable");
        try (FileOutputStream out = new FileOutputStream(new File(getTargetContext().getFilesDir(), name + ".png"))) {
            require(image.compress(Bitmap.CompressFormat.PNG, 100, out), "Screenshot could not be retained");
        } finally { image.recycle(); }
    }
    private AccessibilityNodeInfo node(AccessibilityNodeInfo root, String text, boolean prefix) {
        if (root == null) return null;
        CharSequence value = root.getText();
        if (value != null && (prefix ? value.toString().startsWith(text) : text.equalsIgnoreCase(value.toString()))) return root;
        CharSequence description = root.getContentDescription();
        if (!prefix && description != null && text.equalsIgnoreCase(description.toString())) return root;
        for (int i = 0; i < root.getChildCount(); i++) {
            AccessibilityNodeInfo found = node(root.getChild(i), text, prefix); if (found != null) return found;
        }
        return null;
    }
    private AccessibilityNodeInfo waitNode(String text, boolean prefix) {
        long end = SystemClock.uptimeMillis() + 5000;
        while (SystemClock.uptimeMillis() < end) {
            AccessibilityNodeInfo found = node(getUiAutomation().getRootInActiveWindow(), text, prefix);
            if (found != null) return found;
            SystemClock.sleep(50);
        }
        throw new AssertionError("Missing active-window text: " + text);
    }
    private boolean scroll(AccessibilityNodeInfo root, boolean backward) {
        if (root == null) return false;
        for (int i = 0; i < root.getChildCount(); i++) if (scroll(root.getChild(i), backward)) return true;
        return root.isScrollable() && root.performAction(backward ? AccessibilityNodeInfo.ACTION_SCROLL_BACKWARD : AccessibilityNodeInfo.ACTION_SCROLL_FORWARD);
    }
    private void pressWindow(String text) {
        pressWindow(text, false);
    }
    private void pressWindow(String text, boolean backward) {
        for (int attempt = 0; attempt < 12; attempt++) {
            AccessibilityNodeInfo root = getUiAutomation().getRootInActiveWindow();
            AccessibilityNodeInfo control = node(root, text, false);
            if (control != null && control.isVisibleToUser() && control.isEnabled() && control.performAction(AccessibilityNodeInfo.ACTION_CLICK)) {
                waitForIdleSync(); return;
            }
            scroll(root, backward); SystemClock.sleep(100);
        }
        throw new AssertionError("Active-window button unavailable: " + text);
    }
    @Override public void onStart() {
        Bundle receipt = new Bundle(); Object gate = null; Object lease = null; boolean quarantined = false;
        ActivityMonitor share = null;
        try {
            ClassLoader loader = getTargetContext().getClassLoader();
            Class<?> gateType = loader.loadClass("com.aqss.nativefeedback.ForegroundAudioExclusion");
            Class<?> toolType = loader.loadClass("com.aqss.nativefeedback.ForegroundAudioExclusion$Tool");
            gate = get(gateType.getField("Companion").get(null), "getProcess");
            Object output = toolType.getField("OUTPUT").get(null);
            lease = gateType.getMethod("acquire", toolType, Object.class).invoke(gate, output, new Object());
            require(lease != null, "Synthetic output lease unavailable in fresh process");
            Class<?> recapsType = loader.loadClass("com.aqss.nativefeedback.SoundCheckRecaps");
            Object recaps = get(recapsType.getField("Companion").get(null), "getProcess");
            Object token = get(recaps, "begin");
            Class<?> reasonType = loader.loadClass("com.aqss.nativefeedback.SoundCheckEnd");
            require((Boolean) recapsType.getMethod("finish", token.getClass(), reasonType).invoke(recaps, token, reasonType.getField("STOPPED_BY_USER").get(null)), "Could not seed synthetic historical recap");
            List<?> rows = (List<?>) get(recaps, "snapshot");
            require(rows.size() == 1, "Synthetic recap count differs");

            phase = "busy entry before microphone permission";
            activity = startActivitySync(new Intent().setClassName(getTargetContext(), "com.aqss.bodyguard.prototype.LiveSoundCheckActivity").addFlags(Intent.FLAG_ACTIVITY_NEW_TASK));
            waitForIdleSync(); focus();
            require(BUSY.equals(status()), "Busy entry did not explain waiting for cleanup: " + status());
            noCapture(); require(((Button) read(activity, "start")).isEnabled(), "Busy entry prevents an explicit later retry");
            press("Start sound check"); focus(); noCapture();
            require(BUSY.equals(status()), "Busy retry changed cleanup guidance");
            require(rows.equals(get(recaps, "snapshot")), "Denied UI start invented a completed microphone check");
            shot("sound-availability-busy");
            recreate(); noCapture(); require(BUSY.equals(status()), "Recreation lost busy guidance");

            phase = "actual worker admission still rejects an occupied owner";
            Class<?> captureType = loader.loadClass("com.aqss.bodyguard.prototype.MicrophoneCapture");
            Object denied = captureType.getConstructor(android.content.Context.class).newInstance(getTargetContext());
            captureType.getMethod("start").invoke(denied);
            require(((AtomicBoolean) get(denied, "getCompleted")).get(), "Denied capture did not finish");
            require(read(denied, "recorder") == null && read(denied, "lease") == null, "Denied capture allocated or reserved an input owner");
            require(BUSY.equals(get(denied, "getStopReason")), "Worker denial did not ask to wait for cleanup");
            require(rows.equals(get(recaps, "snapshot")), "Denied worker invented a completed recap");

            phase = "release and foreground return require manual Start";
            require((Boolean) gateType.getMethod("release", lease.getClass(), boolean.class).invoke(gate, lease, true), "Synthetic output did not release");
            lease = null; recreate(); noCapture();
            require(((Button) read(activity, "start")).isEnabled(), "Completed cleanup did not leave manual Start available");
            require(!status().contains("running or closing") && !status().contains("blocked"), "Fresh available entry retained stale guidance");
            shot("sound-availability-released");

            phase = "sticky synthetic cleanup failure";
            lease = gateType.getMethod("acquire", toolType, Object.class).invoke(gate, output, new Object());
            require(lease != null, "Opening the available screen acquired audio without Start");
            require(!((Boolean) gateType.getMethod("release", lease.getClass(), boolean.class).invoke(gate, lease, false)), "Synthetic failed cleanup released its owner");
            quarantined = true; recreate();
            require(BLOCKED.equals(status()), "Blocked entry did not put report review before force stop: " + status());
            noCapture(); require(!((Button) read(activity, "start")).isEnabled(), "Blocked entry offered microphone Start");
            require(((Button) read(activity, "permissionSettings")).getVisibility() == View.GONE, "Cleanup failure offered a permission repair");
            // An old permission response must not replace the current cleanup state.
            runOnMainSync(() -> activity.onRequestPermissionsResult(73, new String[]{Manifest.permission.RECORD_AUDIO}, new int[]{PackageManager.PERMISSION_DENIED}));
            require(BLOCKED.equals(status()), "Permission callback overrode unresolved cleanup");
            require(!((Button) read(activity, "start")).isEnabled(), "Permission callback reenabled a blocked microphone");
            require(rows.equals(get(recaps, "snapshot")), "Recovery presentation changed existing recaps");
            require(((Button) read(activity, "recent")).isEnabled(), "Cleanup block hid recent reports");
            shot("sound-availability-blocked");

            phase = "historical support report during quarantine";
            press("Recent sound checks"); waitNode("Review support report", false); pressWindow("Review support report");
            String frozen = waitNode("Audio Bodyguard\nPlatform: Android\n", true).getText().toString();
            require(frozen.contains("Check 1: No input samples observed\nStopped by you"), "Synthetic historical recap absent from preview");
            require(frozen.contains("not proof of sound safety, protection or TV control"), "Historical report lost uncertainty");
            final int[] sent = {0};
            share = new ActivityMonitor() {
                @Override public ActivityResult onStartActivity(Intent intent) {
                    if (!Intent.ACTION_CHOOSER.equals(intent.getAction())) return null;
                    Intent send = intent.getParcelableExtra(Intent.EXTRA_INTENT);
                    require(send != null && Intent.ACTION_SEND.equals(send.getAction()) && "text/plain".equals(send.getType()), "Missing plain-text report intent");
                    require(frozen.equals(send.getStringExtra(Intent.EXTRA_TEXT)), "Quarantined support Share differs from reviewed text");
                    sent[0]++; return new ActivityResult(Activity.RESULT_CANCELED, null);
                }
            };
            addMonitor(share); pressWindow("Share support report");
            require(sent[0] == 1, "Expected one cancelled exact support share");
            removeMonitor(share); share = null;
            require(frozen.equals(waitNode("Audio Bodyguard\nPlatform: Android\n", true).getText().toString()), "Cancelled sharing changed historical report");
            shot("sound-availability-report");
            pressWindow("Back", true); pressWindow("Clear recaps"); pressWindow("Close"); focus();
            require(((List<?>) get(recaps, "snapshot")).isEmpty(), "Clear recaps did not clear presentation rows");
            require((Boolean) get(gate, "getBlocked"), "Review, Share or Clear released quarantine");
            require(!((Button) read(activity, "start")).isEnabled() && read(activity, "capture") == null, "Report action restarted microphone work");
            receipt.putString("sound_availability_report_b64", Base64.encodeToString(frozen.getBytes(java.nio.charset.StandardCharsets.UTF_8), Base64.NO_WRAP));
            receipt.putString("sound_availability", "passed: synthetic occupied/blocked entry before permission; denied UI and worker allocate no recorder; explicit retry only after release; recreation and stale permission response preserve cleanup state; exact historical report Share and Clear do not release quarantine");
            finish(Activity.RESULT_OK, receipt);
        } catch (Exception | AssertionError error) {
            error.printStackTrace(); receipt.putString("sound_availability_error", phase + ": " + error);
            try { if (activity != null) shot("sound-availability-failure"); } catch (Exception ignored) {}
            finish(Activity.RESULT_CANCELED, receipt);
        } finally {
            if (share != null) removeMonitor(share);
            if (!quarantined && gate != null && lease != null) try { gate.getClass().getMethod("release", lease.getClass(), boolean.class).invoke(gate, lease, true); } catch (Exception ignored) {}
            if (activity != null) runOnMainSync(() -> activity.finish());
        }
    }
}
