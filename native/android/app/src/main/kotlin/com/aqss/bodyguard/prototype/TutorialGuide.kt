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
import com.aqss.nativefeedback.TutorialChoice
import com.aqss.nativefeedback.TutorialStep
import com.aqss.nativefeedback.InterfaceContent

/** A dedicated, one-task screen. Choices are explanations, never device commands. */
class TutorialGuide(
    private val activity: Activity,
    private val scroll: ScrollView,
    private val targets: Map<String, View>,
    private val skin: InterfaceTheme,
    private val currentPage: () -> String,
    private val openSetup: (String) -> Unit,
    private val openPhoto: () -> Unit,
    private val openTool: (String) -> Unit,
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
    private var moreTVBrands = false
    private var helpExpanded = false
    private var renderVersion = 0
    private val choiceButtons = mutableMapOf<String, Button>()
    val isActive get() = guide.topicId != null
    val isBeginner get() = guide.topicId == "getting_started"
    val pictureTarget get() = guide.step?.target?.takeIf { isBeginner && it in listOf("connectionPlan", "connectionCheck") }
    fun useSuggestedTV(brand: String?): Boolean {
        if (!guide.acceptPhotoBrand(brand)) return false
        render(); return true
    }
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
    private fun text(parent: LinearLayout, value: String, size: Float = 19f, color: Int = skin.text, bold: Boolean = false): TextView {
        val view = TextView(activity).apply {
            text = value; textSize = size; setTextColor(color); setPadding(0, 0, 0, dp(18))
            if (bold) setTypeface(null, Typeface.BOLD)
        }
        parent.addView(view, LinearLayout.LayoutParams(-1, -2)); return view
    }
    private fun button(label: String, primary: Boolean = false, action: () -> Unit) = Button(activity).apply { text = label; skin.style(this, primary); textSize = 20f; gravity = Gravity.START or Gravity.CENTER_VERTICAL; minHeight = dp(56); setOnClickListener { action() } }
    fun chooseTopic() = skin.menu("? Help & jump to", listOf(
        "Jump to setup guide" to { start("getting_started"); Unit },
        "Jump to TV photo" to { openPhoto() },
        "Jump to sound check" to { openTool("sound") },
        "Jump to voice check" to { openTool("voice") },
        "Features" to { skin.menu("Features", emptyList(), TutorialContent.features.joinToString("\n\n") { "${it.title} · ${if (it.availability == "preview") "Preview" else "Planned"}\n${it.detail}" }) },
        "More tutorials" to { skin.menu("Tutorials", TutorialContent.topics.map { it.title to { start(it.id); Unit } }) }
    ))
    fun chooseSection() {
        val entries = when (currentPage()) {
            "sound" -> listOf("Sound options" to "options", "Captions" to "captions", "Advanced Settings" to "advanced")
            "devices" -> listOf("Readiness checklist" to "capability", "Connection status" to "coverage", "Privacy and storage" to "privacy")
            "insights" -> listOf("Session history" to "history", "Connection status" to "coverage")
            "settings" -> listOf("Appearance" to "appearance", "Advanced Settings" to "advanced", "Privacy and storage" to "privacy")
            else -> listOf("Connection status" to "coverage", "Readiness checklist" to "capability")
        }
        skin.menu("Jump to", listOf(
            "Setup guide" to { start("getting_started"); Unit },
            "Sound check" to { openTool("sound") },
            "Voice check" to { openTool("voice") }
        ) + entries.map { it.first to { jump(it.second) } })
    }
    private fun setupHelp() {
        val step = guide.step ?: return
        val items = mutableListOf<Pair<String, () -> Unit>>()
        if (step.target in listOf("welcome", "chooseTV")) items += "Jump to TV photo" to { openPhoto() }
        if (step.target == "connectionPlan") {
            items += "Choose home app (optional)" to {
                skin.menu("Optional home app", TutorialContent.choices["chooseHome"].orEmpty().map { choice ->
                    (if (choice.id == "neither") "Use TV maker’s app (default)" else choice.title) to {
                        guide.selectHomeApp(choice.id); render(true)
                    }
                }, "Use your TV maker’s app unless you already use Google Home or Alexa.")
            }
            for (id in listOf("google", "alexa")) if (guide.selected("chooseHome")?.id in listOf(id, "both")) {
                val title = TutorialContent.choices["chooseHome"]!!.first { it.id == id }.title
                items += "Jump to $title pictures" to { openSetup(id) }
            }
        }
        if (step.target in listOf("connectionPlan", "connectionCheck")) items += "Jump to phone Wi-Fi pictures" to { openSetup("phone_wifi") }
        items += "Jump to sound check" to { openTool("sound") }
        items += "Jump to voice check" to { openTool("voice") }
        items += "More tutorials" to { chooseTopic() }
        skin.menu("? Setup help", items, step.example.removePrefix("Example: ").ifEmpty {
            "Follow the TV pictures, then the phone pictures. You can return at any time. Setup guidance does not verify a TV connection."
        })
    }
    private fun chooseBrand() = skin.menu("Choose TV brand", guide.choices.map { choice ->
        choice.title to { if (guide.select(choice.id)) { guide.next(); render() } }
    }, searchable = true)
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
        if (!preserveScroll) { moreFeatures = false; moreTVBrands = false; helpExpanded = false }
        header.removeAllViews(); content.removeAllViews(); controls.removeAllViews()
        val top = LinearLayout(activity).apply { gravity = Gravity.CENTER_VERTICAL }
        top.addView(TextView(activity).apply { text = "Step ${guide.stepNumber} of ${guide.stepCount}"; textSize = 17f; setTextColor(skin.muted); setTypeface(null, Typeface.BOLD) }, LinearLayout.LayoutParams(0, -2, 1f))
        top.addView(roseButton(activity, skin, "Exit Home") { exitToHome() }.apply { contentDescription = "Exit tutorial" })
        header.addView(top)
        if (isBeginner) text(header, TutorialContent.previewNotice, 15f, skin.muted).setPadding(0, dp(4), 0, 0)
        val symbols = when (step.target) {
            "welcome" -> listOf("tv", "arrow.right", "phone")
            "chooseTV" -> listOf("phone", "tv")
            "connectionCheck" -> listOf("phone")
            "chooseHome" -> listOf("house")
            else -> listOf("tv")
        }
        val iconRow = LinearLayout(activity).apply { setPadding(0, dp(12), 0, dp(16)) }
        symbols.forEach { symbol ->
            iconRow.addView(TextView(activity).apply {
                setCompoundDrawablesWithIntrinsicBounds(InterfaceSymbol(skin, symbol, skin.violet, 36), null, null, null)
                importantForAccessibility = View.IMPORTANT_FOR_ACCESSIBILITY_NO
            }, LinearLayout.LayoutParams(dp(64), dp(40)))
        }
        skin.guideCue(iconRow)
        content.addView(iconRow)
        text(content, step.title, 36f, bold = true).apply {
            if (Build.VERSION.SDK_INT >= 28) isAccessibilityHeading = true
            accessibilityLiveRegion = View.ACCESSIBILITY_LIVE_REGION_POLITE
        }
        text(content, step.explanation)
        if (isBeginner) {
            when (step.target) {
                "welcome" -> text(content, "1. Your TV  →  2. Your phone", 18f, skin.accent, true)
                "chooseTV" -> {
                    content.addView(button("Identify TV from a photo", primary = true) { openPhoto() }.apply {
                        setCompoundDrawablesWithIntrinsicBounds(null, null, InterfaceSymbol(skin, "camera", skin.controlText), null)
                    }, LinearLayout.LayoutParams(-1, -2).apply { bottomMargin = dp(16) })
                    content.addView(button("Choose TV brand") { chooseBrand() }, LinearLayout.LayoutParams(-1, -2))
                }
                "connectionPlan" -> guide.selected("chooseTV")?.let { selected ->
                    content.addView(button(if (selected.id == "unsure") "Help identify my TV" else "Show ${selected.title} steps", primary = true) { openSetup(selected.id) }, LinearLayout.LayoutParams(-1, -2))
                }
                "connectionCheck" -> content.addView(button("Phone pictures", primary = true) { openSetup("phone") }, LinearLayout.LayoutParams(-1, -2))
            }
            content.addView(button("? Setup help") { setupHelp() }, LinearLayout.LayoutParams(-2, -2).apply { topMargin = dp(20) })
        } else {
            appendHelp(step)
        }
        renderControls()
        footer.visibility = View.VISIBLE; stateChanged()
        reading.post { if (version == renderVersion && !activity.isFinishing && !activity.isDestroyed) reading.scrollTo(0, oldScroll) }
    }
    private fun appendHelp(step: TutorialStep) {
        if (step.example.isEmpty()) return
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
        text(box, "Both connections are required", 18f, bold = true)
        TutorialContent.connectionStages.forEach { stage ->
            text(box, "${stage.number}. ${stage.title}", 18f, bold = true)
            if (currentTarget != null && currentTarget in stage.targets) text(box, "Current guide section", 12f, skin.accent)
        }
        return box
    }
    private fun featureCatalog(): LinearLayout {
        val box = column()
        box.addView(button(if (moreFeatures) "Fewer features" else TutorialContent.moreFeaturesLabel) { moreFeatures = !moreFeatures; render(true) }.apply {
            if (Build.VERSION.SDK_INT >= 30) stateDescription = if (moreFeatures) "Expanded" else "Collapsed"
        }, LinearLayout.LayoutParams(-2, -2))
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
                skin.style(button, selected); button.textSize = 20f; button.gravity = Gravity.START or Gravity.CENTER_VERTICAL; button.minHeight = dp(64)
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
        guide.selected(step.target)?.let { text(controls, "Selected: ${it.title}", 15f, skin.muted) }
        val row = LinearLayout(activity)
        if (guide.index > 0) row.addView(button("Back") { guide.back(); render() }, LinearLayout.LayoutParams(-2, -2).apply { marginEnd = dp(12) })
        if (guide.canContinue) {
            val label = if (guide.isLast) { if (isBeginner) "Go to Home" else "Done" } else if (guide.index == 0) { if (isBeginner) TutorialContent.startLabel else "Begin" } else "Next"
            row.addView(button(label, primary = step.target !in listOf("connectionPlan", "connectionCheck")) {
                if (guide.isLast) { finished(topic.id); close() } else { guide.next(); render() }
            }.apply {
                compoundDrawablePadding = dp(12)
                setCompoundDrawablesWithIntrinsicBounds(null, null, InterfaceSymbol(skin, "arrow.right", if (step.target !in listOf("connectionPlan", "connectionCheck")) skin.controlText else skin.text), null)
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
