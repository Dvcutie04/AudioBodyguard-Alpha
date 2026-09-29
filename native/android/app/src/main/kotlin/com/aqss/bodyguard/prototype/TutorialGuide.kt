package com.aqss.bodyguard.prototype

import android.app.Activity
import android.graphics.Typeface
import android.os.Build
import android.os.Bundle
import android.view.Gravity
import android.view.View
import android.widget.Button
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import com.aqss.nativefeedback.GuideProgress
import com.aqss.nativefeedback.TutorialContent

/** A dedicated, one-task screen. Choices are explanations, never device commands. */
class TutorialGuide(
    private val activity: Activity,
    private val scroll: ScrollView,
    private val targets: Map<String, View>,
    private val skin: InterfaceTheme,
    private val setExpansion: (Boolean, Boolean, Boolean) -> Unit,
    private val currentPage: () -> String,
    private val openSetup: (String) -> Unit,
    private val navigate: (String, String?) -> Unit,
    private val restorePage: (String) -> Unit,
    private val focusHelp: () -> Unit,
    private val finished: (String) -> Unit,
    private val stateChanged: () -> Unit,
) {
    private val guide = GuideProgress()
    val footer = LinearLayout(activity).apply { orientation = LinearLayout.VERTICAL; visibility = View.GONE }
    private val header = column()
    private val reading = ScrollView(activity)
    private val content = column()
    private val controls = column()
    private var previousPage = "home"
    val isActive get() = guide.topicId != null
    val isBeginner get() = guide.topicId == "getting_started"
    init {
        for (box in listOf(header, content, controls)) box.setPadding(dp(20), dp(12), dp(20), dp(12))
        controls.setBackgroundColor(skin.surface)
        footer.addView(header)
        reading.addView(content)
        footer.addView(reading, LinearLayout.LayoutParams(-1, 0, 1f))
        footer.addView(controls)
        if (Build.VERSION.SDK_INT >= 28) footer.accessibilityPaneTitle = "Tutorial"
    }
    private fun dp(n: Int) = skin.dp(n)
    private fun column() = LinearLayout(activity).apply { orientation = LinearLayout.VERTICAL }
    private fun text(parent: LinearLayout, value: String, size: Float = 16f, color: Int = skin.text, bold: Boolean = false): TextView {
        val view = TextView(activity).apply {
            text = value; textSize = size; setTextColor(color); setPadding(0, 0, 0, dp(14))
            if (bold) setTypeface(null, Typeface.BOLD)
        }
        parent.addView(view, LinearLayout.LayoutParams(-1, -2)); return view
    }
    private fun button(label: String, action: () -> Unit) = Button(activity).apply { text = label; skin.style(this); setOnClickListener { action() } }
    fun chooseTopic() = skin.menu("Choose a tutorial", listOf("Illustrated setup guides" to { openSetup("") }, "Voice check — step by step" to { openSetup("voice") }) + TutorialContent.topics.map { it.title to { start(it.id) } })
    fun chooseSection() {
        val entries = listOf("Start here" to "welcome", "Coverage" to "coverage", "Readiness checklist" to "capability", "Sound options" to "options", "Advanced options" to "advanced", "Captions" to "captions", "Session history" to "history", "Foreground OS hint" to "hint", "Privacy and storage" to "privacy", "Session transfer" to "handoff")
        skin.menu("Jump to a section", entries.map { it.first to { jump(it.second) } })
    }
    fun jump(target: String) {
        close(false); navigate(target, null)
        scroll.post {
            targets[target]?.let { view ->
                var y = view.top; var parent = view.parent as? View
                while (parent != null && parent !== scroll) { y += parent.top; parent = parent.parent as? View }
                scroll.scrollTo(0, y)
            }
        }
    }
    fun start(id: String) {
        if (!isActive) previousPage = currentPage()
        if (guide.start(id)) render()
    }
    private fun render(preserveScroll: Boolean = false) {
        val topic = guide.topic ?: return
        val step = guide.step ?: return
        val oldScroll = if (preserveScroll) reading.scrollY else 0
        header.removeAllViews(); content.removeAllViews(); controls.removeAllViews()
        text(header, "Step ${guide.index + 1} of ${topic.steps.size}", 15f, skin.muted, true)
        header.addView(button("Exit tutorial") { close() }, LinearLayout.LayoutParams(-1, -2))
        content.addView(TextView(activity).apply {
            setCompoundDrawablesWithIntrinsicBounds(InterfaceSymbol(skin, if (step.target == "chooseHome") "house" else "tv", skin.violet), null, null, null)
            importantForAccessibility = View.IMPORTANT_FOR_ACCESSIBILITY_NO
            setPadding(0, dp(6), 0, dp(12))
        }, LinearLayout.LayoutParams(-1, dp(52)))
        text(content, step.title, 30f, bold = true).apply {
            if (Build.VERSION.SDK_INT >= 28) isAccessibilityHeading = true
            accessibilityLiveRegion = View.ACCESSIBILITY_LIVE_REGION_POLITE
        }
        text(content, step.explanation)
        guide.choices.forEach { choice ->
            val selected = guide.selected(step.target)?.id == choice.id
            content.addView(button(choice.title + if (selected) "  ✓" else "") { guide.select(choice.id); render(true) }.apply {
                gravity = Gravity.START or Gravity.CENTER_VERTICAL
                minHeight = dp(60); compoundDrawablePadding = dp(14)
                setCompoundDrawablesWithIntrinsicBounds(InterfaceSymbol(skin, choice.icon, skin.controlText), null, null, null)
                contentDescription = choice.title; isSelected = selected
                if (Build.VERSION.SDK_INT >= 30) stateDescription = if (selected) "Selected" else "Not selected"
            }, LinearLayout.LayoutParams(-1, -2).apply { bottomMargin = dp(10) })
        }
        if (step.target == "connectionPlan") for (target in listOf("chooseTV", "chooseHome")) {
            guide.selected(target)?.let { selected ->
                val box = column().apply { setPadding(dp(16), dp(16), dp(16), dp(6)); background = skin.shape(skin.surface) }
                text(box, selected.title, 20f, bold = true); text(box, selected.detail, color = skin.muted)
                box.addView(button("Show ${selected.title} steps") { openSetup(selected.id) }, LinearLayout.LayoutParams(-1, -2).apply { bottomMargin = dp(12) })
                content.addView(box, LinearLayout.LayoutParams(-1, -2).apply { bottomMargin = dp(16) })
            }
        }
        val example = column().apply { setPadding(dp(16), dp(16), dp(16), dp(6)); background = skin.shape(skin.surface) }
        text(example, step.example, color = skin.muted); content.addView(example)
        if (step.target == "connectionCheck") text(content, "Not connected · Audio protection is not active", 18f, skin.warning, true)
        if (!guide.canContinue) text(controls, "Choose one option above to continue.", 15f, skin.muted)
        guide.selected(step.target)?.let { text(controls, "Selected: ${it.title}", 15f, skin.muted) }
        val row = LinearLayout(activity)
        if (guide.index > 0) row.addView(button("Back") { guide.back(); render() }, LinearLayout.LayoutParams(-2, -2).apply { marginEnd = dp(12) })
        if (guide.canContinue) {
            val label = if (guide.isLast) { if (isBeginner) "Open full app" else "Done" } else if (guide.index == 0) "Begin" else "Next"
            row.addView(button(label) {
                if (guide.isLast) { finished(topic.id); close() } else { guide.next(); render() }
            }, LinearLayout.LayoutParams(0, -2, 1f))
        }
        controls.addView(row)
        footer.visibility = View.VISIBLE; stateChanged()
        reading.post { reading.scrollTo(0, oldScroll) }
    }
    fun detachTarget() { /* Guide never overlays a page. */ }
    fun refreshHighlight() { /* Full app and guide have separate view trees. */ }
    fun close(restore: Boolean = true) {
        if (!isActive) return
        guide.close(); footer.visibility = View.GONE
        setExpansion(true, true, true)
        stateChanged()
        if (restore) { restorePage(previousPage); focusHelp() }
    }
    fun pause() { /* No animation or timer to stop. */ }
    fun resume() { if (isActive) render(true) }
    fun save(bundle: Bundle) {
        guide.topicId?.let { id ->
            bundle.putString("tutorialTopic", id); bundle.putInt("tutorialIndex", guide.index)
            bundle.putString("tutorialPreviousPage", previousPage)
            guide.snapshot().forEach { (key, value) -> bundle.putString("guide-$key", value) }
        }
    }
    fun restore(bundle: Bundle?) {
        val id = bundle?.getString("tutorialTopic") ?: return
        val saved = TutorialContent.choices.keys.mapNotNull { key -> bundle.getString("guide-$key")?.let { key to it } }.toMap()
        guide.restore(id, bundle.getInt("tutorialIndex"), saved)
        previousPage = bundle.getString("tutorialPreviousPage") ?: "home"
        if (isActive) render()
    }
}
