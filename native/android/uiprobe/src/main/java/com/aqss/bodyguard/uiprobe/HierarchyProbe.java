package com.aqss.bodyguard.uiprobe;

import android.app.Activity;
import android.app.Instrumentation;
import android.app.UiAutomation;
import android.graphics.Rect;
import android.os.Bundle;
import android.util.Base64;
import android.util.Xml;
import android.view.accessibility.AccessibilityNodeInfo;
import java.io.StringWriter;
import java.nio.charset.StandardCharsets;
import org.xmlpull.v1.XmlSerializer;

/** Separate test-only process: observe the current window without waiting for changing input to stop. */
public final class HierarchyProbe extends Instrumentation {
    @Override public void onCreate(Bundle arguments) { super.onCreate(arguments); start(); }

    @Override public void onStart() {
        Bundle result = new Bundle();
        try {
            UiAutomation observer = getUiAutomation(UiAutomation.FLAG_DONT_SUPPRESS_ACCESSIBILITY_SERVICES);
            AccessibilityNodeInfo root = observer.getRootInActiveWindow();
            if (root == null) throw new IllegalStateException("No active window root");
            StringWriter text = new StringWriter();
            XmlSerializer xml = Xml.newSerializer();
            xml.setOutput(text);
            xml.startDocument("UTF-8", true);
            xml.startTag(null, "hierarchy");
            write(root, xml, 0, new int[] {0});
            xml.endTag(null, "hierarchy");
            xml.endDocument();
            byte[] bytes = text.toString().getBytes(StandardCharsets.UTF_8);
            if (bytes.length > 524288) throw new IllegalStateException("Hierarchy exceeds bound");
            result.putString("hierarchy", Base64.encodeToString(bytes, Base64.NO_WRAP));
            finish(Activity.RESULT_OK, result);
        } catch (Exception error) {
            result.putString("probe_error", error.toString());
            finish(Activity.RESULT_CANCELED, result);
        }
    }

    private void write(AccessibilityNodeInfo node, XmlSerializer xml, int depth, int[] count) throws Exception {
        if (depth > 64 || ++count[0] > 2000) throw new IllegalStateException("Hierarchy exceeds node/depth bound");
        if (!node.isVisibleToUser()) return;
        Rect bounds = new Rect(); node.getBoundsInScreen(bounds);
        xml.startTag(null, "node");
        xml.attribute(null, "text", node.getText() == null ? "" : node.getText().toString());
        xml.attribute(null, "content-desc", node.getContentDescription() == null ? "" : node.getContentDescription().toString());
        xml.attribute(null, "package", node.getPackageName() == null ? "" : node.getPackageName().toString());
        xml.attribute(null, "bounds", "[" + bounds.left + "," + bounds.top + "][" + bounds.right + "," + bounds.bottom + "]");
        for (int index = 0; index < node.getChildCount(); index++) {
            AccessibilityNodeInfo child = node.getChild(index);
            if (child != null) write(child, xml, depth + 1, count);
        }
        xml.endTag(null, "node");
    }
}
