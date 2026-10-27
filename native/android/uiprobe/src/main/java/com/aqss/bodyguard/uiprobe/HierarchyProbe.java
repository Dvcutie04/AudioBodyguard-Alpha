package com.aqss.bodyguard.uiprobe;

import android.app.Activity;
import android.app.Instrumentation;
import android.app.UiAutomation;
import android.accessibilityservice.AccessibilityServiceInfo;
import android.graphics.Rect;
import android.os.Bundle;
import android.os.SystemClock;
import android.util.Base64;
import android.util.Xml;
import android.view.accessibility.AccessibilityNodeInfo;
import android.view.accessibility.AccessibilityWindowInfo;
import java.io.StringWriter;
import java.nio.charset.StandardCharsets;
import java.util.Locale;
import org.xmlpull.v1.XmlSerializer;

/** Separate test-only process: observe the current window without waiting for changing input to stop. */
public final class HierarchyProbe extends Instrumentation {
    private String requestedClick;
    @Override public void onCreate(Bundle arguments) {
        super.onCreate(arguments);
        requestedClick = arguments == null ? null : arguments.getString("click");
        start();
    }

    @Override public void onStart() {
        Bundle result = new Bundle();
        try {
            UiAutomation observer = getUiAutomation(UiAutomation.FLAG_DONT_SUPPRESS_ACCESSIBILITY_SERVICES);
            AccessibilityServiceInfo info = observer.getServiceInfo();
            info.flags |= AccessibilityServiceInfo.FLAG_RETRIEVE_INTERACTIVE_WINDOWS;
            observer.setServiceInfo(info);
            AccessibilityNodeInfo root = null;
            // Connection can precede the initial window snapshot. Wait for a real root,
            // not for the live accessibility event stream to become idle.
            long deadline = SystemClock.uptimeMillis() + 3000;
            while (SystemClock.uptimeMillis() < deadline) {
                root = observer.getRootInActiveWindow();
                if (root == null) {
                    for (AccessibilityWindowInfo window : observer.getWindows()) {
                        if (window.isActive()) { root = window.getRoot(); if (root != null) break; }
                    }
                }
                if (root != null && root.refresh() && root.isVisibleToUser()) break;
                root = null;
                SystemClock.sleep(100);
            }
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
            if (requestedClick != null) result.putString("clicked", Boolean.toString(click(root, requestedClick.toLowerCase(Locale.ROOT), 0)));
            finish(Activity.RESULT_OK, result);
        } catch (Exception error) {
            result.putString("probe_error", error.toString());
            finish(Activity.RESULT_CANCELED, result);
        }
    }

    private boolean click(AccessibilityNodeInfo node, String label, int depth) {
        if (depth > 64 || !node.isVisibleToUser()) return false;
        String text = node.getText() == null ? "" : node.getText().toString().toLowerCase(Locale.ROOT);
        String description = node.getContentDescription() == null ? "" : node.getContentDescription().toString().toLowerCase(Locale.ROOT);
        if (label.equals(text) || label.equals(description)) {
            AccessibilityNodeInfo target = node;
            for (int parent = 0; parent < 4 && target != null; parent++, target = target.getParent()) {
                if (target.isClickable()) return target.performAction(AccessibilityNodeInfo.ACTION_CLICK);
            }
        }
        for (int index = 0; index < node.getChildCount(); index++) {
            AccessibilityNodeInfo child = node.getChild(index);
            if (child != null && click(child, label, depth + 1)) return true;
        }
        return false;
    }

    private void write(AccessibilityNodeInfo node, XmlSerializer xml, int depth, int[] count) throws Exception {
        if (depth > 64 || ++count[0] > 2000) throw new IllegalStateException("Hierarchy exceeds node/depth bound");
        if (!node.isVisibleToUser()) return;
        Rect bounds = new Rect(); node.getBoundsInScreen(bounds);
        xml.startTag(null, "node");
        xml.attribute(null, "class", node.getClassName() == null ? "" : node.getClassName().toString());
        xml.attribute(null, "text", node.getText() == null ? "" : node.getText().toString());
        xml.attribute(null, "content-desc", node.getContentDescription() == null ? "" : node.getContentDescription().toString());
        xml.attribute(null, "enabled", Boolean.toString(node.isEnabled()));
        xml.attribute(null, "package", node.getPackageName() == null ? "" : node.getPackageName().toString());
        xml.attribute(null, "bounds", "[" + bounds.left + "," + bounds.top + "][" + bounds.right + "," + bounds.bottom + "]");
        for (int index = 0; index < node.getChildCount(); index++) {
            AccessibilityNodeInfo child = node.getChild(index);
            if (child != null) write(child, xml, depth + 1, count);
        }
        xml.endTag(null, "node");
    }
}
