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
    private volatile Uri selected = DELAYED;
    private volatile int pickerRequests;
    private volatile int cameraRequests;

    @Override public void onStart() {
        Bundle result = new Bundle();
        ActivityMonitor monitor = new ActivityMonitor() {
            @Override public ActivityResult onStartActivity(Intent intent) {
                if (android.provider.MediaStore.ACTION_IMAGE_CAPTURE.equals(intent.getAction())) {
                    cameraRequests++; return new ActivityResult(Activity.RESULT_CANCELED, null);
                }
                if (!Intent.ACTION_GET_CONTENT.equals(intent.getAction())) return null;
                pickerRequests++;
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
            waitForText(expired, 45000); assertUnknown();
            long elapsed = SystemClock.elapsedRealtime() - started;
            require(elapsed >= 30000, "Photo expired before its 30-second result window");
            require(!getContext().getContentResolver().call(DELAYED, "state", null, null).getBoolean("released"),
                    "Delayed photo was released before the timeout observation");
            recordScreen("photo-deadline");

            int reads = getContext().getContentResolver().call(DELAYED, "state", null, null).getInt("reads");
            String busy = "The previous photo is still finishing. Try again shortly.";
            selected = FIXTURE;
            choose(); waitForText(busy); assertUnknown();
            require(pickerRequests == 1, "Retry launched another picker while the original read was blocked");
            runOnMainSync(() -> require(click(activity.getWindow().getDecorView(), "Clear photo details"), "Clear missing"));
            waitForText("No photo selected"); choose(); waitForText(busy); assertUnknown();
            runOnMainSync(() -> require(click(activity.getWindow().getDecorView(), "Take a TV photo"), "Camera missing"));
            require(cameraRequests == 0 && pickerRequests == 1, "Clear or camera request bypassed occupied photo work");

            java.lang.reflect.Field field = activity.getClass().getDeclaredField("worker");
            field.setAccessible(true);
            ExecutorService oldWorker = (ExecutorService) field.get(activity);
            runOnMainSync(() -> activity.finish()); waitForIdleSync();
            activity = startActivitySync(launch); waitForText("No photo selected");
            choose(); waitForText(busy); assertUnknown();
            require(pickerRequests == 1 && getContext().getContentResolver().call(DELAYED, "state", null, null).getInt("reads") == reads,
                    "Reopening photo setup admitted another picker or provider read");
            recordScreen("photo-work-busy");
            getContext().getContentResolver().call(DELAYED, "release", null, null);
            // An observer-only barrier waits for the original decoder job to
            // return. No clock, token or OCR result is replaced or injected.
            require(oldWorker.awaitTermination(10, TimeUnit.SECONDS), "Closed photo worker never returned");
            String ready = "The previous photo has finished. Choose a photo.";
            waitForIdleSync(); waitForText(ready); assertUnknown();
            require(pickerRequests == 1, "Cleanup automatically launched a picker");
            recordScreen("photo-work-ready");

            selected = FIXTURE; choose();
            waitForText("Brand: VIZIO"); waitForText("Model: V505M-K09"); waitForText("TV IP hint: 10.20.30.40");
            waitForText("Nothing is connected."); recordScreen("photo-deadline-retry");
            runOnMainSync(() -> require(click(activity.getWindow().getDecorView(), "Clear photo details"), "Clear missing"));
            waitForText("No photo selected"); assertUnknown();
            ExecutorService currentWorker = (ExecutorService) field.get(activity);
            currentWorker.submit(() -> {}).get(10, TimeUnit.SECONDS);
            getContext().getContentResolver().call(DELAYED, "prepare", null, null);
            selected = DELAYED; choose(); waitForText("Reading text on this phone");
            long secondWait = SystemClock.uptimeMillis() + 5000;
            while (!getContext().getContentResolver().call(DELAYED, "state", null, null).getBoolean("opened")) {
                require(SystemClock.uptimeMillis() < secondWait, "Second provider read never opened");
                SystemClock.sleep(100);
            }
            runOnMainSync(() -> require(click(activity.getWindow().getDecorView(), "Clear photo details"), "Clear missing"));
            choose(); waitForText(busy); assertUnknown();
            Activity overlay = startActivitySync(new Intent().setClassName(getTargetContext().getPackageName(),
                    "com.aqss.bodyguard.prototype.SetupGuideActivity").addFlags(Intent.FLAG_ACTIVITY_NEW_TASK));
            waitForIdleSync();
            java.lang.reflect.Field visible = activity.getClass().getDeclaredField("visible");
            visible.setAccessible(true);
            require(!visible.getBoolean(activity), "Photo setup never paused behind the guide");
            getContext().getContentResolver().call(DELAYED, "release", null, null);
            currentWorker.submit(() -> {}).get(10, TimeUnit.SECONDS);
            runOnMainSync(() -> overlay.finish()); waitForIdleSync();
            waitForText(ready); assertUnknown();
            require(visible.getBoolean(activity), "Photo setup never resumed after the guide");
            require(pickerRequests == 3, "Returning to the screen automatically launched a picker");
            recordScreen("photo-work-ready-resume");
            result.putString("photo_deadline", "passed: real provider read held through timeout (" + elapsed +
                    "ms); retry, Clear, camera and reopened screen admitted no overlapping read; visible cleanup and resume show ready without opening a picker; late decoded image rejected; fresh image recognized; Clear unknown");
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
