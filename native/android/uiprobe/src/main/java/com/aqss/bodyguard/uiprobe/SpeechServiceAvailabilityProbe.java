package com.aqss.bodyguard.uiprobe;

import android.app.Activity;
import android.app.Instrumentation;
import android.os.Build;
import android.os.Bundle;
import android.speech.SpeechRecognizer;

/** A test-only, non-capturing OS capability query. No mic, ASR task or words. */
public final class SpeechServiceAvailabilityProbe extends Instrumentation {
    @Override public void onCreate(Bundle arguments) {
        super.onCreate(arguments);
        start();
    }

    @Override public void onStart() {
        Bundle result = new Bundle();
        try {
            final boolean[] available = {false};
            final RuntimeException[] failure = {null};
            // SpeechRecognizer APIs are main-thread owned, including this
            // no-capture availability query in an instrumentation process.
            runOnMainSync(() -> {
                try {
                    available[0] = Build.VERSION.SDK_INT >= 31
                            && SpeechRecognizer.isOnDeviceRecognitionAvailable(getTargetContext());
                } catch (RuntimeException error) {
                    failure[0] = error;
                }
            });
            if (failure[0] != null) throw failure[0];
            result.putString("AQSS_V2_SERVICE_PROBE", "os=Android api=" + Build.VERSION.SDK_INT
                    + " onDeviceService=" + available[0]
                    + " audio=NONE recognitionTask=NONE permissionRequest=NONE");
            finish(Activity.RESULT_OK, result);
        } catch (RuntimeException error) {
            result.putString("AQSS_V2_SERVICE_PROBE", "query-error=" + error.getClass().getSimpleName()
                    + " audio=NONE");
            finish(Activity.RESULT_CANCELED, result);
        }
    }
}
