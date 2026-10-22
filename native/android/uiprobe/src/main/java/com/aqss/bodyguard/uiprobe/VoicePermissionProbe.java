package com.aqss.bodyguard.uiprobe;

import android.Manifest;
import android.app.Activity;
import android.app.Instrumentation;
import android.content.Intent;
import android.os.Bundle;
import android.os.SystemClock;
import java.io.File;

/** Test APK only. Establish real consent without requiring a speech model.
 * The Python observer operates the OS dialog and Settings. No callback,
 * permission result, recognition service, audio or words are injected.
 */
public final class VoicePermissionProbe extends Instrumentation {
    @Override public void onCreate(Bundle arguments) { super.onCreate(arguments); start(); }

    @Override public void onStart() {
        Bundle result = new Bundle();
        File done = new File(getTargetContext().getFilesDir(), "voice-permission-finish");
        try {
            if (done.exists() && !done.delete()) throw new AssertionError("Old fixture signal remains");
            Activity activity = startActivitySync(new Intent()
                    .setClassName(getTargetContext(), "com.aqss.bodyguard.prototype.InputAssistanceActivity")
                    .putExtra("mode", "voice").putExtra("dark", true)
                    .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK));
            waitForIdleSync();
            runOnMainSync(() -> activity.requestPermissions(new String[]{Manifest.permission.RECORD_AUDIO}, 41));
            long until = SystemClock.elapsedRealtime() + 120_000;
            while (!done.exists() && SystemClock.elapsedRealtime() < until) SystemClock.sleep(100);
            if (!done.exists()) throw new AssertionError("Observer did not finish the permission fixture");
            if (!done.delete()) throw new AssertionError("Cannot remove fixture signal");
            result.putString("voice_permission_fixture", "passed: real microphone request/result callback; no recognition service, samples or words injected");
            finish(Activity.RESULT_OK, result);
        } catch (Exception | AssertionError error) {
            result.putString("voice_permission_fixture", "failed: " + error);
            finish(Activity.RESULT_CANCELED, result);
        }
    }
}
