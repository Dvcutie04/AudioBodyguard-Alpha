package com.aqss.bodyguard.uiprobe;

import android.app.Activity;
import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import android.os.SystemClock;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.TimeUnit;

/** Test APK only. The app's real clock, worker, decoder, ML Kit and UI remain in use. */
public final class PhotoDeadlineProbe extends CameraCaptureProbe {
    private static final Uri DELAYED = Uri.parse("content://com.aqss.bodyguard.uiprobe.delayedphotos/delayed.png");
    private static final Uri FIXTURE = Uri.parse("content://com.aqss.bodyguard.uiprobe.delayedphotos/fixture.png");
    private Uri selected = DELAYED;

    @Override public void onStart() {
        Bundle result = new Bundle();
        ActivityMonitor monitor = new ActivityMonitor() {
            @Override public ActivityResult onStartActivity(Intent intent) {
                if (!Intent.ACTION_GET_CONTENT.equals(intent.getAction())) return null;
                return new ActivityResult(Activity.RESULT_OK, new Intent().setData(selected));
            }
        };
        addMonitor(monitor);
        try {
            getContext().getContentResolver().call(DELAYED, "prepare", null, null);
            Intent launch = new Intent().setClassName(getTargetContext().getPackageName(),
                    "com.aqss.bodyguard.prototype.InputAssistanceActivity").putExtra("mode", "photo")
                    .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TASK);
            activity = startActivitySync(launch); waitForText("No photo selected");
            long started = SystemClock.elapsedRealtime();
            choose(); waitForText("Reading text on this phone");
            long providerWait = SystemClock.uptimeMillis() + 5000;
            while (!getContext().getContentResolver().call(DELAYED, "state", null, null).getBoolean("opened")) {
                require(SystemClock.uptimeMillis() < providerWait, "App never attempted the delayed provider read");
                SystemClock.sleep(100);
            }
            String expired = "Photo review timed out. Choose the picture again.";
            waitForText(expired); assertUnknown();
            long elapsed = SystemClock.elapsedRealtime() - started;
            require(elapsed >= 15000, "Photo expired before its 15-second result window");
            require(!getContext().getContentResolver().call(DELAYED, "state", null, null).getBoolean("released"),
                    "Delayed photo was released before the timeout observation");
            recordScreen("photo-deadline");

            getContext().getContentResolver().call(DELAYED, "release", null, null);
            // An observer-only barrier waits for the original decoder job to
            // return. No clock, token or OCR result is replaced or injected.
            java.lang.reflect.Field field = activity.getClass().getDeclaredField("worker");
            field.setAccessible(true);
            ((ExecutorService) field.get(activity)).submit(() -> {}).get(10, TimeUnit.SECONDS);
            waitForIdleSync(); waitForText(expired); assertUnknown();

            selected = FIXTURE; choose();
            waitForText("Brand: VIZIO"); waitForText("Model: V505M-K09"); waitForText("TV IP hint: 10.20.30.40");
            waitForText("Nothing is connected."); recordScreen("photo-deadline-retry");
            runOnMainSync(() -> require(click(activity.getWindow().getDecorView(), "Clear photo details"), "Clear missing"));
            waitForText("No photo selected"); assertUnknown();
            result.putString("photo_deadline", "passed: real provider read held through timeout (" + elapsed +
                    "ms); late decoded image rejected; fresh image recognized; Clear unknown");
            finish(Activity.RESULT_OK, result);
        } catch (Exception | AssertionError error) {
            result.putString("photo_deadline_error", error.toString()); finish(Activity.RESULT_CANCELED, result);
        } finally {
            getContext().getContentResolver().call(DELAYED, "release", null, null);
            removeMonitor(monitor);
            if (activity != null) runOnMainSync(() -> activity.finish());
        }
    }
    private void choose() {
        runOnMainSync(() -> require(click(activity.getWindow().getDecorView(), "Choose a photo"), "Photo picker button missing"));
    }
}
