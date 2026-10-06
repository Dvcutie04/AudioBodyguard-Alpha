package com.aqss.bodyguard.prototype

import android.app.Activity
import android.app.AlertDialog
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
import com.aqss.nativefeedback.InterfaceContent

/** A dedicated, one-task screen. Choices are explanations, never device commands. */
class TutorialGuide(
    private val activity: Activity,
    private val scroll: ScrollView,
    private val targets: Map<String, View>,
    private val skin: InterfaceTheme,
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
    private var pausedTutorial: Bundle? = null
    val hasPausedTutorial get() = pausedTutorial != null
    val selectedTV get() = guide.selected("chooseTV")?.id ?: ""
    private var moreFeatures = false
    private var helpExpanded = false
    private var renderVersion = 0
    private val choiceButtons = mutableMapOf<String, Button>()
    val isActive get() = guide.topicId != null
    val isBeginner get() = guide.topicId == "getting_started"
    val pictureTarget get() = guide.step?.target?.takeIf { isBeginner && it in listOf("connectionPlan", "connectionCheck") }
    fun completePictures(expectedTarget: String, routeId: String): Boolean {
        if (!guide.completePictures(expectedTarget, routeId)) return false
        render(); return true
    }
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
    private fun button(label: String, primary: Boolean = false, action: () -> Unit) = Button(activity).apply { text = label; skin.style(this, primary); setOnClickListener { action() } }
    fun chooseTopic() = skin.menu("Choose a tutorial", listOf<Pair<String, () -> Unit>>("About this page" to {
        val page = InterfaceContent.pages.single { it.id == currentPage() }
        AlertDialog.Builder(activity).setTitle(page.headline).setMessage(page.subtitle).setPositiveButton("Close", null).show()
    }, "Illustrated setup guides" to { openSetup("") }, "Voice check — step by step" to { openSetup("voice") }) + TutorialContent.topics.map { it.title to { start(it.id); Unit } })
    fun chooseSection() {
        val entries = listOf("Start here" to "welcome", "Coverage" to "coverage", "Readiness checklist" to "capability", "Sound options" to "options", "Advanced Settings" to "advanced", "Captions" to "captions", "Session history" to "history", "Foreground OS hint" to "hint", "Privacy and storage" to "privacy", "Session transfer" to "handoff")
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
        if (guide.start(id)) { pausedTutorial = null; render() }
    }
    private fun render(preserveScroll: Boolean = false) {
        val topic = guide.topic ?: return
        val step = guide.step ?: return
        val oldScroll = if (preserveScroll) reading.scrollY else 0
        val version = ++renderVersion
        if (!preserveScroll) { moreFeatures = false; helpExpanded = false }
        header.removeAllViews(); content.removeAllViews(); controls.removeAllViews()
        val top = LinearLayout(activity).apply { gravity = Gravity.CENTER_VERTICAL }
        top.addView(TextView(activity).apply { text = "Step ${guide.index + 1} of ${topic.steps.size}"; textSize = 15f; setTextColor(skin.muted); setTypeface(null, Typeface.BOLD) }, LinearLayout.LayoutParams(0, -2, 1f))
        top.addView(roseButton(activity, skin, "Exit Home") { exitToHome() }.apply { contentDescription = "Exit tutorial" })
        header.addView(top)
        if (isBeginner) text(header, TutorialContent.previewNotice, 12f, skin.muted).setPadding(0, dp(4), 0, 0)
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
        if (isBeginner && step.target == "welcome") content.addView(connectionOverview(), LinearLayout.LayoutParams(-1, -2).apply { bottomMargin = dp(16) })
        else if (isBeginner && step.target !in listOf("connectionPlan", "connectionCheck")) TutorialContent.connectionStages.firstOrNull { step.target in it.targets }?.let {
            text(content, "Connection ${it.number} of 2", 12f, skin.accent, true)
        }
        choiceButtons.clear()
        guide.choices.forEach { choice ->
            val selected = guide.selected(step.target)?.id == choice.id
            content.addView(button(choice.title + if (selected) "  ✓" else "", primary = selected) { if (guide.selected(step.target)?.id != choice.id) { guide.select(choice.id); refreshChoices(); renderControls() } }.apply {
                choiceButtons[choice.id] = this
                gravity = Gravity.START or Gravity.CENTER_VERTICAL
                minHeight = dp(60); compoundDrawablePadding = dp(14)
                setCompoundDrawablesWithIntrinsicBounds(InterfaceSymbol(skin, choice.icon, if (selected) skin.controlText else skin.text), null, null, null)
                contentDescription = choice.title; isSelected = selected
                if (Build.VERSION.SDK_INT >= 30) stateDescription = if (selected) "Selected" else "Not selected"
            }, LinearLayout.LayoutParams(-1, -2).apply { bottomMargin = dp(10) })
        }
        if (step.target in listOf("connectionPlan", "connectionCheck")) {
            if (step.target == "connectionCheck") content.addView(button("Phone pictures", primary = true) { openSetup("phone") }, LinearLayout.LayoutParams(-1, -2).apply { bottomMargin = dp(12) })
            if (step.target == "connectionPlan") selectedConnectionActions(content, primaryTV = true)
        }
        if (isBeginner && step.target == "welcome") {
            content.addView(featureCatalog())
        } else if (step.example.isNotEmpty()) {
            content.addView(button(if (helpExpanded) "Hide help" else TutorialContent.helpLabel) { helpExpanded = !helpExpanded; render(true) }.apply {
                if (Build.VERSION.SDK_INT >= 30) stateDescription = if (helpExpanded) "Expanded" else "Collapsed"
            }, LinearLayout.LayoutParams(-1, -2))
            if (helpExpanded) {
                val example = column().apply { setPadding(dp(16), dp(16), dp(16), dp(6)); background = skin.shape(skin.surface) }
                text(example, step.example, color = skin.muted)
                if (isBeginner && step.target in listOf("connectionPlan", "connectionCheck")) listOf("chooseTV", "chooseHome").forEach { target ->
                    guide.selected(target)?.let { text(example, it.detail, color = skin.muted) }
                }
                if (step.target == "connectionCheck") selectedConnectionActions(example, primaryTV = false)
                content.addView(example)
            }
        }
        renderControls()
        footer.visibility = View.VISIBLE; stateChanged()
        reading.post { if (version == renderVersion && !activity.isFinishing && !activity.isDestroyed) reading.scrollTo(0, oldScroll) }
    }
    private fun selectedConnectionActions(parent: LinearLayout, primaryTV: Boolean) {
        for (target in listOf("chooseTV", "chooseHome")) guide.selected(target)?.takeIf { it.id !in listOf("both", "neither") }?.let { selected ->
            parent.addView(button("Show ${selected.title} steps", primary = primaryTV && target == "chooseTV") { openSetup(selected.id) }, LinearLayout.LayoutParams(-1, -2).apply { bottomMargin = dp(12) })
        }
        if (guide.selected("chooseHome")?.id == "both") listOf("alexa", "google").forEach { id ->
            TutorialContent.choices["chooseHome"]?.firstOrNull { it.id == id }?.let { choice ->
                parent.addView(button("Show ${choice.title} steps") { openSetup(id) }, LinearLayout.LayoutParams(-1, -2).apply { bottomMargin = dp(12) })
            }
        }
    }
    fun connectionOverview(currentTarget: String? = null): LinearLayout {
        val box = column().apply { setPadding(dp(16), dp(16), dp(16), dp(6)); background = skin.shape(skin.surface) }
        text(box, "Both connections are required", 15f, bold = true)
        TutorialContent.connectionStages.forEach { stage ->
            text(box, "${stage.number}. ${stage.title}", 15f, bold = true)
            if (currentTarget != null && currentTarget in stage.targets) text(box, "Current guide section", 12f, skin.accent)
        }
        return box
    }
    private fun featureCatalog(): LinearLayout {
        val box = column()
        box.addView(button(if (moreFeatures) "Fewer features" else TutorialContent.moreFeaturesLabel) { moreFeatures = !moreFeatures; render(true) }.apply {
            if (Build.VERSION.SDK_INT >= 30) stateDescription = if (moreFeatures) "Expanded" else "Collapsed"
        }, LinearLayout.LayoutParams(-1, -2))
        if (moreFeatures) TutorialContent.features.forEach { feature ->
            val row = column()
            text(row, feature.title, 16f, bold = true)
            text(row, if (feature.availability == "preview") "Preview" else "Planned", 14f, skin.accent, true)
            text(row, feature.detail, color = skin.muted)
            row.setPadding(0, dp(12), 0, 0)
            row.importantForAccessibility = View.IMPORTANT_FOR_ACCESSIBILITY_YES
            row.contentDescription = "${feature.title}. ${if (feature.availability == "preview") "Explore in this preview" else "Planned"}. ${feature.detail}"
            box.addView(row, LinearLayout.LayoutParams(-1, -2))
        }
        return box
    }
    private fun refreshChoices() {
        val step = guide.step ?: return
        guide.choices.forEach { choice ->
            val selected = guide.selected(step.target)?.id == choice.id
            choiceButtons[choice.id]?.let { button ->
                button.text = choice.title + if (selected) "  ✓" else ""
                skin.style(button, selected); button.gravity = Gravity.START or Gravity.CENTER_VERTICAL; button.minHeight = dp(60)
                button.compoundDrawablePadding = dp(14)
                button.setCompoundDrawablesWithIntrinsicBounds(InterfaceSymbol(skin, choice.icon, if (selected) skin.controlText else skin.text), null, null, null)
                button.isSelected = selected
                if (Build.VERSION.SDK_INT >= 30) button.stateDescription = if (selected) "Selected" else "Not selected"
            }
        }
    }
    private fun renderControls() {
        val topic = guide.topic ?: return
        val step = guide.step ?: return
        controls.removeAllViews()
        if (!guide.canContinue) text(controls, "Choose one option above to continue.", 15f, skin.muted)
        guide.selected(step.target)?.let { text(controls, "Selected: ${it.title}", 15f, skin.muted) }
        val row = LinearLayout(activity)
        if (guide.index > 0) row.addView(button("Back") { guide.back(); render() }, LinearLayout.LayoutParams(-2, -2).apply { marginEnd = dp(12) })
        if (guide.canContinue) {
            val label = if (guide.isLast) { if (isBeginner) "Open full app" else "Done" } else if (guide.index == 0) { if (isBeginner) TutorialContent.startLabel else "Begin" } else "Next"
            row.addView(button(label, primary = step.target !in listOf("connectionPlan", "connectionCheck")) {
                if (guide.isLast) { finished(topic.id); close() } else { guide.next(); render() }
            }, LinearLayout.LayoutParams(0, -2, 1f))
        }
        controls.addView(row)
    }
    fun detachTarget() { /* Guide never overlays a page. */ }
    fun refreshHighlight() { /* Full app and guide have separate view trees. */ }
    fun close(restore: Boolean = true) {
        if (!isActive) return
        guide.close(); footer.visibility = View.GONE
        stateChanged()
        if (restore) { restorePage(previousPage); focusHelp() }
    }
    private fun exitToHome() {
        val saved = Bundle()
        pausedTutorial = null; save(saved); pausedTutorial = saved
        close(restore = false); restorePage("home"); focusHelp()
    }
    fun returnToTutorial() {
        val saved = pausedTutorial
        if (saved == null) { start("getting_started"); return }
        pausedTutorial = null
        saved.putString("tutorialPreviousPage", currentPage())
        restore(saved)
    }
    fun back() {
        if (guide.index > 0) { guide.back(); render() } else close()
    }
    fun pause() { /* No animation or timer to stop. */ }
    fun resume() { if (isActive) { footer.visibility = View.VISIBLE; stateChanged() } }
    fun save(bundle: Bundle) {
        pausedTutorial?.let { bundle.putBundle("pausedTutorial", it) }
        guide.topicId?.let { id ->
            bundle.putString("tutorialTopic", id); bundle.putInt("tutorialIndex", guide.index)
            bundle.putString("tutorialPreviousPage", previousPage)
            guide.snapshot().forEach { (key, value) -> bundle.putString("guide-$key", value) }
        }
    }
    fun restore(bundle: Bundle?) {
        pausedTutorial = bundle?.getBundle("pausedTutorial")
        val id = bundle?.getString("tutorialTopic") ?: return
        val saved = TutorialContent.choices.keys.mapNotNull { key -> bundle.getString("guide-$key")?.let { key to it } }.toMap()
        guide.restore(id, bundle.getInt("tutorialIndex"), saved)
        previousPage = bundle.getString("tutorialPreviousPage") ?: "home"
        if (isActive) render()
    }
}
