package com.aqss.bodyguard.uiprobe;

import android.app.Activity;
import android.content.ClipData;
import android.content.Intent;
import android.os.Bundle;
import java.io.FileOutputStream;
import java.nio.charset.StandardCharsets;
import org.json.JSONArray;
import org.json.JSONObject;

/** Isolated CI receiver for the actual native Sharesheet handoff. Never in the app APK. */
public final class BuildDetailsShareReceiver extends Activity {
    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        try {
            Intent input = getIntent();
            JSONObject observed = new JSONObject();
            observed.put("action", input.getAction());
            observed.put("type", input.getType());
            observed.put("text", input.getStringExtra(Intent.EXTRA_TEXT));
            observed.put("has_stream", input.hasExtra(Intent.EXTRA_STREAM));
            observed.put("data", input.getData() == null ? JSONObject.NULL : input.getData().toString());
            JSONArray clips = new JSONArray();
            ClipData clip = input.getClipData();
            if (clip != null) {
                for (int index = 0; index < clip.getItemCount(); index++) {
                    ClipData.Item item = clip.getItemAt(index);
                    JSONObject value = new JSONObject();
                    value.put("text", item.getText() == null ? JSONObject.NULL : item.getText().toString());
                    value.put("uri", item.getUri() == null ? JSONObject.NULL : item.getUri().toString());
                    value.put("has_intent", item.getIntent() != null);
                    clips.put(value);
                }
            }
            observed.put("clips", clips);
            try (FileOutputStream output = openFileOutput("shared-build-details.json", MODE_PRIVATE)) {
                output.write(observed.toString().getBytes(StandardCharsets.UTF_8));
            }
        } catch (Exception error) {
            throw new IllegalStateException("Cannot record the native share handoff", error);
        } finally {
            finish();
        }
    }
}
