package com.aqss.bodyguard.prototype

import android.animation.ValueAnimator
import android.app.Activity
import android.app.AlertDialog
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.Drawable
import android.graphics.drawable.GradientDrawable
import android.os.Bundle
import android.os.Build
import android.text.SpannableString
import android.text.Spanned
import android.text.style.StyleSpan
import android.view.View
import android.view.ViewTreeObserver
import android.view.accessibility.AccessibilityNodeInfo
import android.widget.Button
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import com.aqss.nativefeedback.TutorialContent
import com.aqss.nativefeedback.TutorialTopic

/** Presentation only: no audio, evidence, authorization, adapter or profile API. */
class TutorialGuide(
    private val activity: Activity,
    private val scroll: ScrollView,
    private val targets: Map<String, View>,
    private val expansion: () -> Triple<Boolean, Boolean, Boolean>,
    private val setExpansion: (Boolean, Boolean, Boolean) -> Unit,
    private val stateChanged: () -> Unit,
) {
    val footer = LinearLayout(activity).apply { orientation = LinearLayout.VERTICAL }
    private val panel = LinearLayout(activity).apply {
        orientation = LinearLayout.VERTICAL
        visibility = View.GONE
        setPadding(dp(12), dp(8), dp(12), 0)
        background = GradientDrawable().apply {
            setColor(Color.rgb(238, 244, 250))
            setStroke(dp(1), Color.rgb(196, 210, 225))
        }
    }
    private val text = TextView(activity).apply {
        textSize = 16f
        setTextColor(Color.rgb(34, 46, 62))
        accessibilityLiveRegion = View.ACCESSIBILITY_LIVE_REGION_POLITE
    }
    private val explanation = ScrollView(activity).apply { addView(text) }
    private val back = button("Back") { move(-1) }
    private val next = button("Next") { move(1) }
    private val help = button("Help & tutorials") { chooseTopic() }
    private var topic: TutorialTopic? = null
    val isActive: Boolean get() = topic != null
    private var index = 0
    private var previous = Triple(false, false, false)
    private var highlighted: View? = null
    private var originalForeground: Drawable? = null
    private var pendingLayout: ViewTreeObserver.OnGlobalLayoutListener? = null

    init {
        val readingHeight = (activity.resources.configuration.screenHeightDp / 3).coerceIn(100, 220)
        panel.addView(explanation, LinearLayout.LayoutParams(-1, dp(readingHeight)))
        panel.addView(TextView(activity).apply {
            text = "Scroll the explanation to read more."
            textSize = 12f
            setTextColor(Color.rgb(55, 70, 87))
        })
        val navigation = LinearLayout(activity)
        for (item in listOf(back, next, button("Close tutorial") { close() })) {
            navigation.addView(item, LinearLayout.LayoutParams(0, -2, 1f))
        }
        panel.addView(navigation)
        footer.addView(panel)
        val shortcuts = LinearLayout(activity)
        shortcuts.addView(button("Jump to") { chooseSection() }, LinearLayout.LayoutParams(0, -2, 1f))
        shortcuts.addView(help, LinearLayout.LayoutParams(0, -2, 1f))
        footer.addView(shortcuts)
        if (Build.VERSION.SDK_INT >= 28) panel.accessibilityPaneTitle = "Tutorial"
    }

    private fun dp(value: Int) = (value * activity.resources.displayMetrics.density).toInt()

    private fun button(label: String, action: () -> Unit) = Button(activity).apply {
        text = label
        isAllCaps = false
        minHeight = dp(48)
        setOnClickListener { action() }
    }

    fun chooseTopic() {
        AlertDialog.Builder(activity).setTitle("Choose a tutorial")
            .setItems(TutorialContent.topics.map { it.title }.toTypedArray()) { _, which ->
                start(TutorialContent.topics[which].id)
            }.setNegativeButton("Cancel", null).show()
    }

    private fun chooseSection() {
        val entries = listOf(
            Triple("Coverage", "coverage", "home"),
            Triple("Readiness checklist", "capability", "checklist"),
            Triple("Sound options", "options", "options"),
            Triple("Advanced options", "advanced", "advanced"),
            Triple("Captions", "captions", "home"),
            Triple("Session history", "history", "home"),
            Triple("Foreground OS hint", "hint", "home"),
            Triple("Privacy and storage", "privacy", "advanced"),
            Triple("Session transfer", "handoff", "home"),
        )
        AlertDialog.Builder(activity).setTitle("Jump to a section")
            .setItems(entries.map { it.first }.toTypedArray()) { _, which ->
                val entry = entries[which]
                close(restore = false)
                revealArea(entry.third)
                targets[entry.second]?.let { revealTarget(it, highlight = false) }
            }.setNegativeButton("Cancel", null).show()
    }

    private fun revealArea(area: String) {
        setExpansion(area == "options" || area == "advanced", area == "advanced", area == "checklist")
    }

    fun start(id: String) {
        val selected = TutorialContent.topics.firstOrNull { it.id == id } ?: return
        if (topic == null) previous = expansion()
        topic = selected
        index = 0
        render()
    }

    private fun move(delta: Int) {
        val selected = topic ?: return
        val position = index + delta
        if (position >= selected.steps.size) { close(); return }
        if (position < 0) return
        index = position
        render()
    }

    private fun clearHighlight() {
        pendingLayout?.let { if (scroll.viewTreeObserver.isAlive) scroll.viewTreeObserver.removeOnGlobalLayoutListener(it) }
        pendingLayout = null
        highlighted?.foreground = originalForeground
        highlighted = null
    }

    private fun render() {
        val selected = topic ?: return
        val step = selected.steps.getOrNull(index) ?: return
        val target = targets[step.target] ?: run { close(); return }
        clearHighlight()
        revealArea(step.area)
        val description = "Tutorial — ${selected.title}\nStep ${index + 1} of ${selected.steps.size} • Highlighted: ${step.title}\n\n${step.explanation}\n\n${step.example}"
        text.text = SpannableString(description).apply {
            setSpan(StyleSpan(Typeface.BOLD), 0, description.indexOf('\n'), Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
        }
        explanation.scrollTo(0, 0)
        back.isEnabled = index > 0
        next.text = if (index == selected.steps.lastIndex) "Done" else "Next"
        panel.visibility = View.VISIBLE
        text.animate().cancel()
        text.alpha = 1f
        if (ValueAnimator.areAnimatorsEnabled()) {
            text.alpha = 0.7f
            text.animate().alpha(1f).setDuration(180).start()
        }
        revealTarget(target, highlight = true)
        stateChanged()
    }

    private fun revealTarget(target: View, highlight: Boolean) {
        clearHighlight()
        val listener = object : ViewTreeObserver.OnGlobalLayoutListener {
            override fun onGlobalLayout() {
                if (scroll.viewTreeObserver.isAlive) scroll.viewTreeObserver.removeOnGlobalLayoutListener(this)
                pendingLayout = null
                if (highlight) {
                    highlighted = target
                    originalForeground = target.foreground
                    target.foreground = GradientDrawable().apply {
                        setColor(Color.TRANSPARENT)
                        setStroke(dp(3), Color.rgb(0, 96, 180))
                        cornerRadius = dp(6).toFloat()
                    }
                }
                var y = target.top
                var parent = target.parent as? View
                while (parent != null && parent !== scroll) { y += parent.top; parent = parent.parent as? View }
                if (highlight && ValueAnimator.areAnimatorsEnabled()) scroll.smoothScrollTo(0, y) else scroll.scrollTo(0, y)
                if (!highlight) target.performAccessibilityAction(AccessibilityNodeInfo.ACTION_ACCESSIBILITY_FOCUS, null)
            }
        }
        pendingLayout = listener
        scroll.viewTreeObserver.addOnGlobalLayoutListener(listener)
        scroll.requestLayout()
    }

    fun close(restore: Boolean = true) {
        if (topic == null) return
        clearHighlight()
        text.animate().cancel()
        topic = null
        index = 0
        panel.visibility = View.GONE
        if (restore) {
            setExpansion(previous.first, previous.second, previous.third)
            help.performAccessibilityAction(AccessibilityNodeInfo.ACTION_ACCESSIBILITY_FOCUS, null)
        }
        stateChanged()
    }

    fun pause() { text.animate().cancel(); clearHighlight() }
    fun resume() { if (topic != null) render() }

    fun save(bundle: Bundle) {
        topic?.let {
            bundle.putString("tutorialTopic", it.id)
            bundle.putInt("tutorialIndex", index)
            bundle.putBoolean("tutorialPreviousOptions", previous.first)
            bundle.putBoolean("tutorialPreviousAdvanced", previous.second)
            bundle.putBoolean("tutorialPreviousChecklist", previous.third)
        }
    }

    fun restore(bundle: Bundle?) {
        val id = bundle?.getString("tutorialTopic") ?: return
        val selected = TutorialContent.topics.firstOrNull { it.id == id } ?: return
        val position = bundle.getInt("tutorialIndex")
        if (position !in selected.steps.indices) return
        topic = selected
        index = position
        previous = Triple(bundle.getBoolean("tutorialPreviousOptions"), bundle.getBoolean("tutorialPreviousAdvanced"),
            bundle.getBoolean("tutorialPreviousChecklist"))
        render()
    }
}
