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

/** Only page navigation, highlighting and temporary guide state. */
class TutorialGuide(
    private val activity: Activity,
    private val scroll: ScrollView,
    private val targets: Map<String, View>,
    private val skin: InterfaceTheme,
    private val expansion: () -> Triple<Boolean, Boolean, Boolean>,
    private val setExpansion: (Boolean, Boolean, Boolean) -> Unit,
    private val currentPage: () -> String,
    private val navigate: (String, String?) -> Unit,
    private val restorePage: (String) -> Unit,
    private val focusHelp: () -> Unit,
    private val stateChanged: () -> Unit,
) {
    val footer = LinearLayout(activity).apply { orientation = LinearLayout.VERTICAL }
    private val panel = LinearLayout(activity).apply {
        orientation = LinearLayout.VERTICAL; visibility = View.GONE
        setPadding(dp(14), dp(12), dp(14), dp(10)); background = skin.shape(skin.surface, 0, true)
    }
    private val text = TextView(activity).apply {
        textSize = 16f; setTextColor(skin.text); accessibilityLiveRegion = View.ACCESSIBILITY_LIVE_REGION_POLITE
    }
    private val explanation = ScrollView(activity).apply { addView(text) }
    private val back = button("Back") { move(-1) }
    private val next = button("Next") { move(1) }
    private var topic: TutorialTopic? = null
    val isActive: Boolean get() = topic != null
    private var index = 0
    private var previous = Triple(true, true, false)
    private var previousPage = "home"
    private var highlighted: View? = null
    private var originalForeground: Drawable? = null
    private var pendingLayout: ViewTreeObserver.OnGlobalLayoutListener? = null

    init {
        val readingHeight = (activity.resources.configuration.screenHeightDp / 3).coerceIn(80, 160)
        panel.addView(explanation, LinearLayout.LayoutParams(-1, dp(readingHeight)))
        panel.addView(TextView(activity).apply { text = "Scroll for details."; textSize = 12f; setTextColor(skin.muted); setPadding(0, dp(6), 0, dp(6)) })
        val controls = LinearLayout(activity)
        val close = button("Close tutorial") { close() }
        for (item in listOf(back, next)) controls.addView(item, LinearLayout.LayoutParams(0, -2, 1f).apply { marginEnd = dp(4) })
        if (activity.resources.configuration.fontScale < 1.5f) controls.addView(close, LinearLayout.LayoutParams(0, -2, 1f))
        panel.addView(controls)
        if (activity.resources.configuration.fontScale >= 1.5f) panel.addView(close, LinearLayout.LayoutParams(-1, -2).apply { topMargin = dp(6) })
        footer.addView(panel)
        if (Build.VERSION.SDK_INT >= 28) panel.accessibilityPaneTitle = "Tutorial"
    }
    private fun dp(value: Int) = skin.dp(value)
    private fun button(label: String, action: () -> Unit) = Button(activity).apply { text = label; skin.style(this); setOnClickListener { action() } }
    fun chooseTopic() {
        AlertDialog.Builder(activity).setTitle("Choose a tutorial").setItems(TutorialContent.topics.map { it.title }.toTypedArray()) { _, i -> start(TutorialContent.topics[i].id) }.setNegativeButton("Cancel", null).show()
    }
    fun chooseSection() {
        val entries = listOf("Coverage" to "coverage", "Readiness checklist" to "capability", "Sound options" to "options", "Advanced options" to "advanced", "Captions" to "captions", "Session history" to "history", "Foreground OS hint" to "hint", "Privacy and storage" to "privacy", "Session transfer" to "handoff")
        AlertDialog.Builder(activity).setTitle("Jump to a section").setItems(entries.map { it.first }.toTypedArray()) { _, i -> jump(entries[i].second) }.setNegativeButton("Cancel", null).show()
    }
    fun jump(target: String) {
        close(false); navigate(target, null)
        targets[target]?.let { revealTarget(it, false) }
    }
    fun start(id: String) {
        val selected = TutorialContent.topics.firstOrNull { it.id == id } ?: return
        if (topic == null) { previous = expansion(); previousPage = currentPage() }
        topic = selected; index = 0; render()
    }
    private fun move(delta: Int) {
        val selected = topic ?: return
        val position = index + delta
        if (position >= selected.steps.size) { close(); return }
        if (position < 0) return
        index = position; render()
    }
    fun detachTarget() {
        pendingLayout?.let { if (scroll.viewTreeObserver.isAlive) scroll.viewTreeObserver.removeOnGlobalLayoutListener(it) }
        pendingLayout = null; highlighted?.foreground = originalForeground; highlighted = null
    }
    private fun render() {
        val selected = topic ?: return
        val step = selected.steps.getOrNull(index) ?: return
        detachTarget(); navigate(step.target, step.area)
        val target = targets[step.target] ?: run { close(); return }
        val description = "Tutorial — ${selected.title}\nStep ${index + 1} of ${selected.steps.size} • Highlighted: ${step.title}\n\n${step.explanation}\n\n${step.example}"
        text.text = SpannableString(description).apply { setSpan(StyleSpan(Typeface.BOLD), 0, description.indexOf('\n'), Spanned.SPAN_EXCLUSIVE_EXCLUSIVE) }
        explanation.scrollTo(0, 0); back.isEnabled = index > 0
        next.text = if (index == selected.steps.lastIndex) "Done" else "Next"
        panel.visibility = View.VISIBLE; text.animate().cancel(); text.alpha = 1f
        if (ValueAnimator.areAnimatorsEnabled()) { text.alpha = .7f; text.animate().alpha(1f).setDuration(180).start() }
        revealTarget(target, true); stateChanged()
    }
    private fun revealTarget(target: View, highlight: Boolean) {
        detachTarget()
        val listener = object : ViewTreeObserver.OnGlobalLayoutListener {
            override fun onGlobalLayout() {
                if (scroll.viewTreeObserver.isAlive) scroll.viewTreeObserver.removeOnGlobalLayoutListener(this)
                pendingLayout = null
                if (!target.isAttachedToWindow || (highlight && !isActive)) return
                if (highlight) {
                    highlighted = target; originalForeground = target.foreground
                    target.foreground = GradientDrawable().apply { setColor(Color.TRANSPARENT); setStroke(dp(3), skin.accent); cornerRadius = dp(22).toFloat() }
                }
                var y = target.top; var parent = target.parent as? View
                while (parent != null && parent !== scroll) { y += parent.top; parent = parent.parent as? View }
                if (highlight && ValueAnimator.areAnimatorsEnabled()) scroll.smoothScrollTo(0, y) else scroll.scrollTo(0, y)
                if (!highlight) target.performAccessibilityAction(AccessibilityNodeInfo.ACTION_ACCESSIBILITY_FOCUS, null)
            }
        }
        pendingLayout = listener; scroll.viewTreeObserver.addOnGlobalLayoutListener(listener); scroll.requestLayout()
    }
    fun close(restore: Boolean = true) {
        if (topic == null) return
        detachTarget(); text.animate().cancel(); topic = null; index = 0; panel.visibility = View.GONE
        if (restore) { setExpansion(previous.first, previous.second, previous.third); restorePage(previousPage); focusHelp() }
        stateChanged()
    }
    fun pause() { text.animate().cancel(); detachTarget() }
    fun resume() { if (topic != null) render() }
    fun save(bundle: Bundle) {
        topic?.let { bundle.putString("tutorialTopic", it.id); bundle.putInt("tutorialIndex", index); bundle.putString("tutorialPreviousPage", previousPage); bundle.putBoolean("tutorialPreviousOptions", previous.first); bundle.putBoolean("tutorialPreviousAdvanced", previous.second); bundle.putBoolean("tutorialPreviousChecklist", previous.third) }
    }
    fun restore(bundle: Bundle?) {
        val id = bundle?.getString("tutorialTopic") ?: return
        val selected = TutorialContent.topics.firstOrNull { it.id == id } ?: return
        val position = bundle.getInt("tutorialIndex")
        if (position !in selected.steps.indices) return
        topic = selected; index = position
        previous = Triple(bundle.getBoolean("tutorialPreviousOptions"), bundle.getBoolean("tutorialPreviousAdvanced"), bundle.getBoolean("tutorialPreviousChecklist"))
        previousPage = bundle.getString("tutorialPreviousPage") ?: "home"; render()
    }
}
