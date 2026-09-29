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
    private val finished: (String) -> Unit,
    private val stateChanged: () -> Unit,
) {
    private val sideGuide = activity.resources.configuration.screenWidthDp >= 640 && activity.resources.configuration.screenWidthDp > activity.resources.configuration.screenHeightDp
    val footer = LinearLayout(activity).apply { orientation = LinearLayout.VERTICAL; visibility = View.GONE }
    private val panel = LinearLayout(activity).apply {
        orientation = LinearLayout.VERTICAL; visibility = View.GONE
        setPadding(dp(14), dp(12), dp(14), dp(10)); background = skin.shape(skin.surface, 0, true)
    }
    private val text = TextView(activity).apply {
        textSize = 16f; setTextColor(skin.text); accessibilityLiveRegion = View.ACCESSIBILITY_LIVE_REGION_POLITE
    }
    private val explanation = ScrollView(activity).apply { addView(text) }
    private val progress = LinearLayout(activity).apply { importantForAccessibility = View.IMPORTANT_FOR_ACCESSIBILITY_NO_HIDE_DESCENDANTS }
    private val back = button("Back") { move(-1) }
    private val next = button("Next") { move(1) }
    private var topic: TutorialTopic? = null
    val isActive: Boolean get() = topic != null
    val isBeginner: Boolean get() = topic?.id == "getting_started"
    private var index = 0
    private var previous = Triple(true, true, false)
    private var previousPage = "home"
    private var highlighted: View? = null
    private var originalForeground: Drawable? = null
    private var pendingLayout: ViewTreeObserver.OnGlobalLayoutListener? = null

    init {
        val readingHeight = (activity.resources.configuration.screenHeightDp / 3).coerceIn(80, 160)
        panel.addView(progress)
        panel.addView(explanation, if (sideGuide) LinearLayout.LayoutParams(-1, 0, 1f) else LinearLayout.LayoutParams(-1, dp(readingHeight)))
        panel.addView(TextView(activity).apply { text = "Scroll for details."; textSize = 12f; setTextColor(skin.muted); setPadding(0, dp(6), 0, dp(6)) })
        val controls = LinearLayout(activity)
        val close = button(if (sideGuide) "Close" else "Close tutorial") { close() }.apply { contentDescription = "Close tutorial" }
        for (item in listOf(back, next)) controls.addView(item, LinearLayout.LayoutParams(0, -2, 1f).apply { marginEnd = dp(4) })
        if (activity.resources.configuration.fontScale < 1.5f || sideGuide) controls.addView(close, LinearLayout.LayoutParams(0, -2, 1f))
        panel.addView(controls)
        if (activity.resources.configuration.fontScale >= 1.5f && !sideGuide) panel.addView(close, LinearLayout.LayoutParams(-1, -2).apply { topMargin = dp(6) })
        footer.addView(panel, LinearLayout.LayoutParams(-1, if (sideGuide) -1 else -2))
        if (Build.VERSION.SDK_INT >= 28) panel.accessibilityPaneTitle = "Tutorial"
    }
    private fun dp(value: Int) = skin.dp(value)
    private fun button(label: String, action: () -> Unit) = Button(activity).apply { text = label; skin.style(this); setOnClickListener { action() } }
    fun chooseTopic() {
        AlertDialog.Builder(activity).setTitle("Choose a tutorial").setItems(TutorialContent.topics.map { it.title }.toTypedArray()) { _, i -> start(TutorialContent.topics[i].id) }.setNegativeButton("Cancel", null).show()
    }
    fun chooseSection() {
        val entries = listOf("Start here" to "welcome", "Coverage" to "coverage", "Readiness checklist" to "capability", "Sound options" to "options", "Advanced options" to "advanced", "Captions" to "captions", "Session history" to "history", "Foreground OS hint" to "hint", "Privacy and storage" to "privacy", "Session transfer" to "handoff")
        AlertDialog.Builder(activity).setTitle("Jump to a section").setItems(entries.map { it.first }.toTypedArray()) { _, i -> jump(entries[i].second) }.setNegativeButton("Cancel", null).show()
    }
    fun jump(target: String) {
        close(false); navigate(target, null)
        targets[target]?.let { revealTarget(it, false) }
    }
    fun start(id: String, position: Int = 0) {
        val selected = TutorialContent.topics.firstOrNull { it.id == id } ?: return
        if (position !in selected.steps.indices) return
        if (topic == null) { previous = expansion(); previousPage = currentPage() }
        topic = selected; index = position; render()
    }
    private fun move(delta: Int) {
        val selected = topic ?: return
        val position = index + delta
        if (position >= selected.steps.size) { finished(selected.id); close(); return }
        if (position < 0) return
        index = position; render()
    }
    fun detachTarget() {
        pendingLayout?.let { if (scroll.viewTreeObserver.isAlive) scroll.viewTreeObserver.removeOnGlobalLayoutListener(it) }
        pendingLayout = null; highlighted?.foreground = originalForeground; highlighted = null
    }
    fun refreshHighlight() {
        val step = topic?.steps?.getOrNull(index) ?: return
        // A local card redraw must not scroll away from the example values the
        // user just opened. Only a deliberate tour step change moves the page.
        val target = targets[step.target] ?: return
        detachTarget(); highlightTarget(target)
    }
    private fun highlightTarget(target: View) {
        highlighted = target; originalForeground = target.foreground
        target.foreground = GradientDrawable().apply { setColor(Color.TRANSPARENT); setStroke(dp(3), skin.accent); cornerRadius = dp(22).toFloat() }
    }
    private fun render() {
        val selected = topic ?: return
        val step = selected.steps.getOrNull(index) ?: return
        detachTarget(); navigate(step.target, step.area)
        val target = targets[step.target] ?: run { close(); return }
        progress.removeAllViews()
        progress.visibility = if (selected.id == "getting_started" && activity.resources.configuration.fontScale < 1.5f) View.VISIBLE else View.GONE
        if (progress.visibility == View.VISIBLE) selected.steps.indices.forEach { number ->
            progress.addView(TextView(activity).apply {
                text = "${number + 1}"; textSize = 13f; gravity = android.view.Gravity.CENTER
                setTypeface(null, Typeface.BOLD)
                setTextColor(if (number == index) skin.background else skin.muted)
                background = skin.shape(if (number == index) skin.accent else skin.raised, 13)
            }, LinearLayout.LayoutParams(dp(26), dp(26)).apply { marginEnd = dp(8); bottomMargin = dp(8) })
        }
        val description = "Tutorial — ${selected.title}\nStep ${index + 1} of ${selected.steps.size} • Highlighted: ${step.title}\n\n${step.explanation}\n\n${step.example}"
        text.text = SpannableString(description).apply { setSpan(StyleSpan(Typeface.BOLD), 0, description.indexOf('\n'), Spanned.SPAN_EXCLUSIVE_EXCLUSIVE) }
        explanation.scrollTo(0, 0); back.isEnabled = index > 0
        next.text = if (index == selected.steps.lastIndex) "Done" else "Next"
        footer.visibility = View.VISIBLE; panel.visibility = View.VISIBLE; text.animate().cancel(); text.alpha = 1f
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
                    highlightTarget(target)
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
        detachTarget(); text.animate().cancel(); topic = null; index = 0; panel.visibility = View.GONE; footer.visibility = View.GONE
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
