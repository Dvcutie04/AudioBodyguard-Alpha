package com.aqss.bodyguard.uiprobe;

import android.app.Activity;
import android.app.Instrumentation;
import android.content.Intent;
import android.content.pm.ProviderInfo;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.net.Uri;
import android.os.Bundle;
import android.os.SystemClock;
import android.provider.MediaStore;
import android.view.View;
import android.view.ViewGroup;
import android.widget.TextView;
import java.io.FileNotFoundException;
import java.io.InputStream;
import java.io.OutputStream;
import java.util.HashSet;
import java.util.Set;

/** Test APK only. Intercepts the external camera intent, never injects OCR text. */
public final class CameraCaptureProbe extends Instrumentation {
    private Activity activity;
    private final Set<Uri> seen = new HashSet<>();
    private Uri output;
    private String violation;
    private String mode = "photo";
    private int requests;

    @Override public void onCreate(Bundle arguments) { super.onCreate(arguments); start(); }

    @Override public void onStart() {
        Bundle result = new Bundle();
        ActivityMonitor monitor = new ActivityMonitor() {
            @Override public ActivityResult onStartActivity(Intent intent) {
                if (!MediaStore.ACTION_IMAGE_CAPTURE.equals(intent.getAction())) return null;
                requests++;
                try {
                    @SuppressWarnings("deprecation")
                    Uri uri = intent.getParcelableExtra(MediaStore.EXTRA_OUTPUT);
                    require(uri != null, "Camera must supply EXTRA_OUTPUT; a thumbnail is not a full photo");
                    require("content".equals(uri.getScheme()), "Camera output must be a content URI");
                    require((getTargetContext().getPackageName() + ".tvphotos").equals(uri.getAuthority()), "Wrong provider authority");
                    require(seen.add(uri), "A camera output URI was reused");
                    output = uri;
                    int grants = Intent.FLAG_GRANT_READ_URI_PERMISSION | Intent.FLAG_GRANT_WRITE_URI_PERMISSION;
                    require((intent.getFlags() & grants) == grants, "Missing temporary camera read/write grants");
                    require((intent.getFlags() & (Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION | Intent.FLAG_GRANT_PREFIX_URI_PERMISSION)) == 0,
                            "Camera grant must not persist or cover sibling paths");
                    require(intent.getClipData() != null && intent.getClipData().getItemCount() == 1 &&
                            uri.equals(intent.getClipData().getItemAt(0).getUri()), "ClipData must identify only this output");
                    if ("unavailable".equals(mode)) throw new android.content.ActivityNotFoundException("Synthetic camera unavailable");
                    if (!"empty".equals(mode)) {
                        try (InputStream fixture = getContext().getAssets().open("tv-photo-labels.png");
                             OutputStream stream = getTargetContext().getContentResolver().openOutputStream(uri, "w")) {
                            require(stream != null, "Output URI was not writable");
                            byte[] buffer = new byte[8192]; int count;
                            while ((count = fixture.read(buffer)) != -1) stream.write(buffer, 0, count);
                        }
                    }
                    if ("cancel".equals(mode)) return new ActivityResult(Activity.RESULT_CANCELED, null);
                    if ("empty".equals(mode)) {
                        // A valid-looking thumbnail must not substitute for an empty output file.
                        Bitmap thumbnail;
                        try (InputStream fixture = getContext().getAssets().open("tv-photo-labels.png")) {
                            thumbnail = BitmapFactory.decodeStream(fixture);
                        }
                        return new ActivityResult(Activity.RESULT_OK, new Intent().putExtra("data", thumbnail));
                    }
                    return new ActivityResult(Activity.RESULT_OK, null);
                } catch (android.content.ActivityNotFoundException expected) {
                    throw expected;
                } catch (Exception | AssertionError error) {
                    violation = error.toString();
                    return new ActivityResult(Activity.RESULT_CANCELED, null);
                }
            }
        };
        addMonitor(monitor);
        try {
            Intent launch = new Intent().setClassName(getTargetContext(), "com.aqss.bodyguard.prototype.InputAssistanceActivity")
                    .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            activity = startActivitySync(launch);
            waitForText("No photo selected");
            capture("photo");
            require(violation == null, violation);
            waitForText("Brand: VIZIO"); waitForText("Model: V505M-K09"); waitForText("TV IP hint: 10.20.30.40");
            waitForText("Nothing is connected."); assertRemoved(output);

            capture("cancel"); require(violation == null, violation);
            assertEmpty(); assertRemoved(output);

            capture("empty"); require(violation == null, violation);
            waitForText("Photo could not be read."); assertUnknown(); assertRemoved(output);

            capture("unavailable"); require(violation == null, violation);
            waitForText("Camera unavailable."); assertUnknown(); assertRemoved(output);

            // Close on the launch turn, before the posted camera result is delivered.
            mode = "photo";
            runOnMainSync(() -> { click(activity.getWindow().getDecorView(), "Take a TV photo"); activity.finish(); });
            require(violation == null, violation); assertRemoved(output);
            require(requests == 5, "Expected five distinct camera requests, observed " + requests);
            ProviderInfo provider = getTargetContext().getPackageManager().resolveContentProvider(
                    getTargetContext().getPackageName() + ".tvphotos", 0);
            require(provider != null && !provider.exported && provider.grantUriPermissions, "Provider is not privately scoped");
            result.putString("camera_capture", "passed: full image with null result, cancel, empty-output thumbnail rejection, unavailable camera, close; five unique URIs removed");
            finish(Activity.RESULT_OK, result);
        } catch (Exception | AssertionError error) {
            result.putString("camera_capture_error", error.toString());
            finish(Activity.RESULT_CANCELED, result);
        } finally {
            removeMonitor(monitor);
            if (activity != null) runOnMainSync(() -> activity.finish());
        }
    }

    private void capture(String nextMode) {
        mode = nextMode;
        runOnMainSync(() -> require(click(activity.getWindow().getDecorView(), "Take a TV photo"), "Camera button missing"));
    }
    private void assertEmpty() { waitForText("No photo selected"); assertUnknown(); }
    private void assertUnknown() { waitForText("Brand: Not identified"); waitForText("Model: Not identified"); waitForText("TV IP hint: Not identified"); }
    private void assertRemoved(Uri uri) throws Exception {
        require(uri != null, "No output URI captured");
        long deadline = SystemClock.uptimeMillis() + 5000;
        while (SystemClock.uptimeMillis() < deadline) {
            try (InputStream ignored = getTargetContext().getContentResolver().openInputStream(uri)) {
                SystemClock.sleep(100);
            } catch (FileNotFoundException removed) { return; }
        }
        throw new AssertionError("Temporary photo still readable after its request ended");
    }
    private void waitForText(String expected) {
        long deadline = SystemClock.uptimeMillis() + 30000;
        while (SystemClock.uptimeMillis() < deadline) {
            StringBuilder text = new StringBuilder();
            runOnMainSync(() -> read(activity.getWindow().getDecorView(), text));
            if (text.toString().contains(expected)) return;
            SystemClock.sleep(150);
        }
        throw new AssertionError("Missing camera review text: " + expected);
    }
    private static boolean click(View view, String text) {
        if (view instanceof TextView && text.contentEquals(((TextView) view).getText())) return view.performClick();
        if (view instanceof ViewGroup) for (int i = 0; i < ((ViewGroup) view).getChildCount(); i++)
            if (click(((ViewGroup) view).getChildAt(i), text)) return true;
        return false;
    }
    private static void read(View view, StringBuilder text) {
        if (view.getVisibility() != View.VISIBLE) return;
        if (view instanceof TextView) text.append(((TextView) view).getText()).append('\n');
        if (view instanceof ViewGroup) for (int i = 0; i < ((ViewGroup) view).getChildCount(); i++) read(((ViewGroup) view).getChildAt(i), text);
    }
    private static void require(boolean condition, String message) { if (!condition) throw new AssertionError(message); }
}
