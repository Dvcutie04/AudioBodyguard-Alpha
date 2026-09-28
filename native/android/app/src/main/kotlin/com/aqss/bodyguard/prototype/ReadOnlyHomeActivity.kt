package com.aqss.bodyguard.prototype

import android.app.Activity
import android.app.AlertDialog
import android.content.res.Configuration
import android.graphics.Color
import android.graphics.Typeface
import android.media.AudioDeviceCallback
import android.media.AudioDeviceInfo
import android.media.AudioManager
import android.os.Bundle
import android.os.Build
import android.os.Handler
import android.os.Looper
import android.view.Gravity
import android.view.View
import android.view.ViewGroup
import android.view.ViewTreeObserver
import android.view.WindowInsets
import android.widget.Button
import android.widget.FrameLayout
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import android.window.OnBackInvokedCallback
import android.window.OnBackInvokedDispatcher
import com.aqss.nativefeedback.CapabilityFacts
import com.aqss.nativefeedback.SessionEvidenceView
import com.aqss.nativefeedback.SessionState
import com.aqss.nativefeedback.TutorialContent
import com.aqss.nativefeedback.InterfaceContent

/** Presentation only: navigation and appearance cannot authorize an audio action. */
class ReadOnlyHomeActivity : Activity() {
    private var page = "home"
    private var optionsExpanded = true
    private var advancedExpanded = true
    private var checklistExpanded = false
    private var showingExample = false
    private var chartValuesVisible = false
    private lateinit var skin: InterfaceTheme
    private lateinit var root: LinearLayout
    private lateinit var column: LinearLayout
    private lateinit var scroll: ScrollView
    private lateinit var nav: LinearLayout
    private lateinit var tutorial: TutorialGuide
    private lateinit var help: Button
    private val targets = mutableMapOf<String, View>()
    private var backCallback: OnBackInvokedCallback? = null
    private var hintView: TextView? = null
    private var hintText = ""
    private var deviceCallback: AudioDeviceCallback? = null
    private var observationEpoch = 0
    private var observing = false
    private val coverage = SessionEvidenceView.coverage(null, "prototype", "prototype", 0.0)
    private val capability = SessionEvidenceView.capability(CapabilityFacts(null, null, null, null, null, null, 0.0, 0.0, "prototype"), "prototype", 0.0)
    private var appearance: String
        get() = getSharedPreferences("aqss-presentation", MODE_PRIVATE).getString("appearance", "midnight") ?: "midnight"
        set(value) { getSharedPreferences("aqss-presentation", MODE_PRIVATE).edit().putString("appearance", value).apply() }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        page = savedInstanceState?.getString("page")?.takeIf { id -> InterfaceContent.pages.any { it.id == id } } ?: "home"
        optionsExpanded = savedInstanceState?.getBoolean("optionsExpanded", true) ?: true
        advancedExpanded = savedInstanceState?.getBoolean("advancedExpanded", true) ?: true
        checklistExpanded = savedInstanceState?.getBoolean("checklistExpanded") ?: false
        require(coverage.state == SessionState.UNKNOWN_PHYSICAL_STATE && coverage.reason == "NO_OBSERVATION")
        build(savedInstanceState)
    }

    private fun build(saved: Bundle?) {
        val dark = when (appearance) { "daylight" -> false; "system" -> resources.configuration.uiMode and Configuration.UI_MODE_NIGHT_MASK == Configuration.UI_MODE_NIGHT_YES; else -> true }
        setTheme(if (dark) R.style.AQSSMidnightTheme else R.style.AQSSReadOnlyTheme)
        skin = InterfaceTheme(this, dark)
        hintText = getString(R.string.hint_waiting)
        root = vertical().apply { setBackgroundColor(skin.background) }
        val header = LinearLayout(this).apply { gravity = Gravity.CENTER_VERTICAL; setPadding(dp(16), dp(4), dp(16), dp(4)) }
        header.addView(TextView(this).apply { text = if (resources.configuration.fontScale >= 1.5f) "AQSS" else "BODYGUARD"; textSize = 12f; setTypeface(null, Typeface.BOLD); setTextColor(skin.accent); letterSpacing = .13f }, LinearLayout.LayoutParams(0, -2, 1f))
        header.addView(button("Jump to") { tutorial.chooseSection() }, LinearLayout.LayoutParams(-2, -2).apply { marginEnd = dp(8) })
        help = button("Help") { tutorial.chooseTopic() }.apply { contentDescription = "Help & tutorials" }
        header.addView(help)
        root.addView(header)
        val sideGuide = resources.configuration.screenWidthDp >= 640 && resources.configuration.screenWidthDp > resources.configuration.screenHeightDp
        val body = LinearLayout(this).apply { orientation = if (sideGuide) LinearLayout.HORIZONTAL else LinearLayout.VERTICAL }
        root.addView(body, LinearLayout.LayoutParams(-1, 0, 1f))
        scroll = ScrollView(this).apply { isFillViewport = false; clipToPadding = true }
        column = vertical().apply { setPadding(dp(20), dp(18), dp(20), dp(20)) }
        scroll.addView(column, ViewGroup.LayoutParams(-1, -2))
        body.addView(scroll, LinearLayout.LayoutParams(if (sideGuide) 0 else -1, if (sideGuide) -1 else 0, 1f))
        tutorial = TutorialGuide(this, scroll, targets, skin,
            expansion = { Triple(optionsExpanded, advancedExpanded, checklistExpanded) },
            setExpansion = { options, advanced, checklist -> optionsExpanded = options; advancedExpanded = advanced; checklistExpanded = checklist },
            currentPage = { page },
            navigate = { target, area ->
                showingExample = false
                page = InterfaceContent.targetPages[target] ?: "home"
                if (page == "sound") optionsExpanded = true
                if (page == "settings") advancedExpanded = true
                if (area == "checklist") checklistExpanded = true
                renderPage()
            },
            restorePage = { previous -> page = previous; renderPage() },
            focusHelp = { help.requestFocus(); help.sendAccessibilityEvent(android.view.accessibility.AccessibilityEvent.TYPE_VIEW_FOCUSED) },
            stateChanged = { syncBackCallback() })
        body.addView(tutorial.footer, LinearLayout.LayoutParams(if (sideGuide) dp((resources.configuration.screenWidthDp * .44f).toInt().coerceIn(300, 440)) else -1, if (sideGuide) -1 else -2))
        nav = LinearLayout(this).apply { setPadding(dp(8), dp(8), dp(8), dp(8)); setBackgroundColor(skin.surface) }
        root.addView(nav)
        if (Build.VERSION.SDK_INT >= 30) {
            window.setDecorFitsSystemWindows(false)
            root.setOnApplyWindowInsetsListener { view, insets ->
                val bars = insets.getInsets(WindowInsets.Type.systemBars() or WindowInsets.Type.displayCutout())
                view.setPadding(bars.left, bars.top, bars.right, bars.bottom)
                insets
            }
        }
        if (saved == null) {
            // The system splash is icon-sized on Android 12+. Show the complete supplied
            // artwork for the first drawn frame, then reveal the already-built page.
            val frame = FrameLayout(this)
            val artwork = StartupArtworkView(this).apply {
                setBackgroundColor(Color.WHITE)
            }
            frame.addView(root, FrameLayout.LayoutParams(-1, -1))
            frame.addView(artwork, FrameLayout.LayoutParams(-1, -1))
            setContentView(frame)
            setSystemBars(false, true)
            var firstFrameDrawn = false
            val listener = object : ViewTreeObserver.OnDrawListener {
                override fun onDraw() {
                    if (firstFrameDrawn) return
                    firstFrameDrawn = true
                    artwork.postOnAnimation {
                        if (artwork.viewTreeObserver.isAlive) artwork.viewTreeObserver.removeOnDrawListener(this)
                        if (isFinishing || isDestroyed) return@postOnAnimation
                        artwork.animate().alpha(0f).setDuration(120L).withEndAction {
                            frame.removeView(artwork)
                            setSystemBars(dark)
                        }.start()
                    }
                }
            }
            artwork.viewTreeObserver.addOnDrawListener(listener)
        } else {
            setContentView(root)
            setSystemBars(dark)
        }
        renderPage(); tutorial.restore(saved); syncBackCallback()
    }

    private fun setSystemBars(dark: Boolean, launching: Boolean = false) {
        @Suppress("DEPRECATION")
        window.decorView.systemUiVisibility = if (launching || !dark) View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR or View.SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR else 0
        @Suppress("DEPRECATION")
        window.statusBarColor = if (launching) Color.WHITE else skin.background
        @Suppress("DEPRECATION")
        window.navigationBarColor = if (launching) Color.WHITE else skin.surface
    }

    private fun dp(value: Int) = skin.dp(value)
    private fun vertical() = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
    private fun button(label: String, primary: Boolean = false, action: () -> Unit) = Button(this).apply { text = label; skin.style(this, primary); setOnClickListener { action() } }
    private fun label(parent: LinearLayout, value: String, size: Float = 16f, color: Int = skin.text, bold: Boolean = false): TextView {
        val view = TextView(this).apply {
            text = value; textSize = size; setTextColor(color); setPadding(0, 0, 0, dp(8))
            if (bold) { setTypeface(null, Typeface.BOLD); if (Build.VERSION.SDK_INT >= 28) isAccessibilityHeading = true }
        }
        parent.addView(view, LinearLayout.LayoutParams(-1, -2)); return view
    }
    private fun card(target: String? = null, content: (LinearLayout) -> Unit): LinearLayout {
        val box = vertical().apply { setPadding(dp(18), dp(18), dp(18), dp(18)); background = skin.card() }
        column.addView(box, LinearLayout.LayoutParams(-1, -2).apply { bottomMargin = dp(18) })
        target?.let { targets[it] = box }
        content(box); return box
    }
    private fun action(parent: LinearLayout, title: String, primary: Boolean = false, expanded: Boolean? = null, onClick: () -> Unit) {
        parent.addView(button(title, primary, onClick).apply {
            expanded?.let { value ->
                val state = if (value) "Expanded" else "Collapsed"
                if (Build.VERSION.SDK_INT >= 30) stateDescription = state else contentDescription = "$title. $state"
            }
        }, LinearLayout.LayoutParams(-1, -2).apply { topMargin = dp(8) })
    }
    private fun section(title: String, detail: String, explanation: String, target: String) = card(target) { c ->
        label(c, title, 20f, bold = true)
        label(c, detail, 16f, if (detail.contains("Unknown") || detail == "Unavailable") skin.warning else skin.text, true)
        label(c, explanation, 15f, skin.muted)
    }
    private fun destination(title: String, subtitle: String, action: () -> Unit) {
        val c = card { c ->
            label(c, "$title  ›", 19f, skin.accent, true)
            label(c, subtitle, 14f, skin.muted)
        }
        c.isClickable = true; c.isFocusable = true; c.contentDescription = "$title. $subtitle"
        c.accessibilityDelegate = object : View.AccessibilityDelegate() {
            override fun onInitializeAccessibilityNodeInfo(host: View, info: android.view.accessibility.AccessibilityNodeInfo) {
                super.onInitializeAccessibilityNodeInfo(host, info)
                info.className = Button::class.java.name
            }
        }
        c.setOnClickListener { action() }
    }

    private fun renderPage(preserveScroll: Boolean = false) {
        val previousScroll = if (preserveScroll) scroll.scrollY else 0
        if (::tutorial.isInitialized) tutorial.detachTarget()
        hintView = null; targets.clear(); column.removeAllViews(); scroll.scrollTo(0, 0)
        val current = InterfaceContent.pages.single { it.id == page }
        label(column, "${current.title.uppercase()}  /  PREVIEW", 12f, skin.accent, true)
        label(column, current.headline, 30f, bold = true)
        label(column, current.subtitle, 16f, skin.muted).setPadding(0, 0, 0, dp(22))
        when (page) {
            "sound" -> soundPage()
            "devices" -> devicesPage()
            "insights" -> insightsPage()
            "settings" -> settingsPage()
            else -> homePage()
        }
        label(column, "SIMULATION · No audio path connected", 12f, skin.muted)
        renderNav(); syncBackCallback()
        if (preserveScroll) scroll.post { scroll.scrollTo(0, previousScroll) }
    }
    private fun renderNav() {
        nav.removeAllViews()
        if (resources.configuration.fontScale >= 1.5f) {
            val title = InterfaceContent.pages.single { it.id == page }.title
            nav.addView(button("Pages · $title") {
                AlertDialog.Builder(this).setTitle("Choose a page").setItems(InterfaceContent.pages.map { it.title }.toTypedArray()) { _, i -> openPage(InterfaceContent.pages[i].id) }.setNegativeButton("Cancel", null).show()
            }, LinearLayout.LayoutParams(-1, -2))
        } else {
            InterfaceContent.pages.forEach { item ->
                nav.addView(button(item.title) { openPage(item.id) }.apply {
                    textSize = 12f; minHeight = dp(58); setPadding(dp(1), dp(4), dp(1), dp(4))
                    setTextColor(if (page == item.id) skin.accent else skin.muted)
                    setCompoundDrawablesWithIntrinsicBounds(null, InterfaceSymbol(skin, item.id, if (page == item.id) skin.accent else skin.muted), null, null)
                    compoundDrawablePadding = dp(4)
                    background = skin.shape(if (page == item.id) skin.raised else skin.surface, 14)
                    contentDescription = item.title; isSelected = page == item.id
                    if (Build.VERSION.SDK_INT >= 30) stateDescription = if (isSelected) "Selected" else "Not selected"
                }, LinearLayout.LayoutParams(0, -2, 1f))
            }
        }
    }
    private fun openPage(id: String) {
        tutorial.close(restore = false); showingExample = false; chartValuesVisible = false; page = id
        if (id == "sound") optionsExpanded = true
        if (id == "settings") advancedExpanded = true
        renderPage()
    }
    private fun jump(target: String) { tutorial.jump(target) }

    private fun homePage() {
        card("coverage") { c ->
            label(c, "COVERAGE", 12f, skin.muted, true)
            val row = LinearLayout(this).apply { gravity = Gravity.CENTER_VERTICAL }
            val words = vertical()
            row.addView(words, LinearLayout.LayoutParams(0, -2, 1f))
            label(words, "Unknown physical state", 23f, skin.warning, true)
            label(words, "No output observation", 15f, skin.text, true)
            if (resources.configuration.fontScale < 1.5f) row.addView(InterfaceGraphic(this, skin, "orbit"), LinearLayout.LayoutParams(dp(90), dp(90)))
            c.addView(row)
            label(c, "This preview does not monitor or protect audio. Start by exploring what a supported path needs.", 16f, skin.muted)
            action(c, "Review readiness", true) { checklistExpanded = true; jump("capability") }
        }
        label(column, "Explore your space", 20f, bold = true)
        destination("Sound controls", "Presets, captions & equalizer") { openPage("sound") }
        destination("Insights", "Trends, evidence & examples") { openPage("insights") }
        card { c ->
            label(c, "START HERE", 12f, skin.violet, true)
            label(c, "A little guidance.\nA clearer picture.", 23f, bold = true)
            label(c, "Short walkthroughs explain each area, one step at a time. Return to Help whenever you need it.", 16f, skin.muted)
            action(c, "Show me around") { tutorial.start("home") }
        }
    }
    private fun soundPage() {
        card("options") { c ->
            label(c, "Sound options", 22f, bold = true)
            label(c, "Explore each control. A qualified device and observed result are needed before audio can change.", 16f, skin.muted)
            action(c, if (optionsExpanded) "Hide options" else "Options", expanded = optionsExpanded) { tutorial.close(false); optionsExpanded = !optionsExpanded; renderPage(true) }
            action(c, "Help with options") { tutorial.start("sound") }
        }
        if (optionsExpanded) {
            section("Volume", "Unavailable", "No qualified device volume control is connected.", "volume")
            card("sound") { c ->
                label(c, "UNAVAILABLE", 12f, skin.warning, true)
                label(c, "Sound presets", 22f, bold = true)
                label(c, "Device support determines which presets can be proposed.", 16f, skin.muted)
                label(c, "Dialogue preset", 20f, skin.violet, true)
                label(c, "A proposed speech-focused setting", 15f, skin.muted)
                label(c, "Night preset", 20f, skin.violet, true)
                label(c, "A proposed quieter listening setting", 15f, skin.muted)
            }
            section("Custom Equalizer", "Unavailable", "Frequency-band adjustments need a qualified device capability. No bands are being changed.", "equalizer")
            section("Captions option", "Unavailable", "No authored caption track or selectable caption mode is connected.", "captionOption")
            section("Defaults and Undo", "Unavailable", "No confirmed device settings or verified change are available to save, restore, or undo.", "defaults")
        }
        section("Captions", "Not observed", "No authored caption track has been discovered or selected.", "captions")
        destination("Advanced options", "Device, privacy & background details") { jump("advanced") }
    }
    private fun devicesPage() {
        card { c ->
            label(c, "PATH NOT QUALIFIED", 12f, skin.warning, true)
            label(c, "This app   ···   Output needed", 21f, skin.accent, true)
            label(c, "No qualified device connected", 18f, bold = true)
            label(c, "Connection, permission and physical observation must all be established. This diagram shows the requirements.", 16f, skin.muted)
        }
        card("capability") { c ->
            label(c, "Readiness checklist", 22f, bold = true)
            label(c, if (capability.label == "UNKNOWN" && !capability.canActuate && capability.reasons.size == 6) "Six setup checks unknown" else "Unavailable — checklist unconfirmed", 17f, skin.warning)
            label(c, "Hardware, qualification, permission, route, runtime and independent observation.", 16f, skin.muted)
            action(c, if (checklistExpanded) "Hide readiness checklist" else "Show readiness checklist", true, checklistExpanded) { tutorial.close(false); checklistExpanded = !checklistExpanded; renderPage(true) }
            action(c, "Help with readiness") { tutorial.start("readiness") }
        }
        if (checklistExpanded) TutorialContent.topics.single { it.id == "readiness" }.steps.forEach { section(it.title, "Unknown", it.explanation, it.target) }
        card("hint") { c ->
            label(c, "Foreground OS hint", 20f, bold = true)
            hintView = label(c, hintText, 16f)
            label(c, "Only this app's callbacks while active. These cannot verify playback, another app's route, or physical output.", 15f, skin.muted)
        }
        section("Move this session", "Unavailable", "No supported endpoint or verified transfer path is connected. Moving between iPhone and Android needs qualification in both directions.", "handoff")
        action(column, "Help with session transfer") { tutorial.start("handoff") }
    }
    private fun insightsPage() {
        card { c ->
            label(c, "Audio trends", 22f, bold = true)
            if (showingExample) {
                label(c, InterfaceContent.exampleLabel, 13f, skin.warning, true)
                label(c, InterfaceContent.exampleTitle, 18f, bold = true)
                label(c, "Invented values for learning this graph. They are not microphone readings, dB measurements or proof of protection.", 15f, skin.muted)
                val graph = LinearLayout(this)
                val axis = vertical()
                for (n in listOf("100", "50", "0")) axis.addView(TextView(this).apply { text = n; textSize = 12f; setTextColor(skin.muted); gravity = if (n == "0") Gravity.BOTTOM else if (n == "50") Gravity.CENTER_VERTICAL else Gravity.TOP }, LinearLayout.LayoutParams(-2, 0, 1f))
                graph.addView(axis, LinearLayout.LayoutParams(dp(34), -1))
                graph.addView(InterfaceGraphic(this, skin, "chart"), LinearLayout.LayoutParams(0, -1, 1f))
                c.addView(graph, LinearLayout.LayoutParams(-1, dp(155)))
                val ends = LinearLayout(this)
                for ((index, name) in listOf("Sample 1", "Sample 8").withIndex()) ends.addView(TextView(this).apply {
                    text = name; textSize = 12f; setTextColor(skin.muted)
                    gravity = if (index == 0) Gravity.START else Gravity.END
                }, LinearLayout.LayoutParams(0, -2, 1f))
                c.addView(ends)
                label(c, InterfaceContent.exampleUnit, 12f, skin.muted)
                action(c, if (chartValuesVisible) "Hide chart values" else "Read chart values") { chartValuesVisible = !chartValuesVisible; renderPage(true) }
                if (chartValuesVisible) InterfaceContent.exampleValues.forEachIndexed { i, v -> label(c, "Sample ${i + 1}: ${v.toInt()} relative units", 15f, skin.muted) }
                action(c, "Close example") { showingExample = false; chartValuesVisible = false; renderPage() }
            } else {
                c.addView(InterfaceGraphic(this, skin, "wave"), LinearLayout.LayoutParams(-1, dp(70)))
                label(c, "No measurements yet", 21f, bold = true)
                label(c, "A qualified observation source is needed before a real trend can appear. Missing measurements cannot establish safe audio.", 16f, skin.muted)
                action(c, "Explore an example", true) { showingExample = true; renderPage() }
            }
        }
        section("Session history", "No observed events", "A missing history cannot establish continuous coverage. Requests and verified results will need distinct records.", "history")
        card { c ->
            label(c, "Read the whole picture", 20f, bold = true)
            label(c, "Future insights need source, time and verification context. Unknown intervals must remain visible.", 16f, skin.muted)
            action(c, "Review requirements") { jump("capability") }
        }
    }
    private fun settingsPage() {
        card { c ->
            label(c, "Appearance", 22f, bold = true)
            label(c, "One visual language, in the light that suits you.", 16f, skin.muted)
            for (value in listOf("midnight", "daylight", "system")) {
                c.addView(button(value.replaceFirstChar { it.uppercase() } + if (appearance == value) "  ✓" else "") {
                    val state = Bundle(); savePresentation(state); tutorial.pause(); appearance = value; build(state)
                }.apply { contentDescription = value.replaceFirstChar { it.uppercase() }; isSelected = appearance == value }, LinearLayout.LayoutParams(-1, -2).apply { topMargin = dp(8) })
            }
        }
        card("advanced") { c ->
            label(c, "Advanced options", 22f, bold = true)
            action(c, if (advancedExpanded) "Hide advanced options" else "Advanced options", expanded = advancedExpanded) { tutorial.close(false); advancedExpanded = !advancedExpanded; renderPage(true) }
            action(c, "Help with advanced options") { tutorial.start("advanced") }
        }
        if (advancedExpanded) {
            section("Device and route", "Unknown", "No qualified output hardware or route has been identified.", "route")
            section("Physical output", "Unknown physical state", "No independent observation is available. Options cannot verify audible output.", "physical")
            section("Background monitoring", "Unavailable", "Only foreground hints are received; changes while away are unknown.", "background")
            section("Privacy and storage", "No audio recorded by this app", "Only your appearance choice is saved locally. Tutorial and example progress are temporary. No tutorial analytics or audio uploads.", "privacy")
            section("Move this session option", "Unavailable", "No authorized endpoint or verified transfer path is connected.", "handoffOption")
        }
        label(column, "On the horizon", 22f, bold = true)
        label(column, "Explore the direction. These features are not active.", 16f, skin.muted)
        InterfaceContent.future.forEach { f ->
            destination(f.title, f.detail) { AlertDialog.Builder(this).setTitle(f.title).setMessage(f.explanation).setPositiveButton("Got it", null).show() }
        }
        action(column, "Browse all tutorials") { tutorial.chooseTopic() }
    }
    private fun handleLocalBack(): Boolean {
        when {
            tutorial.isActive -> tutorial.close()
            showingExample -> { showingExample = false; chartValuesVisible = false; renderPage() }
            page == "settings" && advancedExpanded -> { advancedExpanded = false; renderPage() }
            page == "sound" && optionsExpanded -> { optionsExpanded = false; renderPage() }
            page == "devices" && checklistExpanded -> { checklistExpanded = false; renderPage() }
            page != "home" -> openPage("home")
            else -> return false
        }
        return true
    }
    private fun syncBackCallback() {
        if (Build.VERSION.SDK_INT < 33 || !::tutorial.isInitialized) return
        val needed = tutorial.isActive || page != "home"
        if (needed && backCallback == null) {
            val callback = OnBackInvokedCallback { handleLocalBack() }
            onBackInvokedDispatcher.registerOnBackInvokedCallback(OnBackInvokedDispatcher.PRIORITY_DEFAULT, callback); backCallback = callback
        } else if (!needed) { backCallback?.let { onBackInvokedDispatcher.unregisterOnBackInvokedCallback(it) }; backCallback = null }
    }
    @Deprecated("Legacy Back fallback for Android 8–12")
    override fun onBackPressed() { if (!handleLocalBack()) super.onBackPressed() }
    override fun onDestroy() {
        if (Build.VERSION.SDK_INT >= 33) backCallback?.let { onBackInvokedDispatcher.unregisterOnBackInvokedCallback(it) }
        backCallback = null; super.onDestroy()
    }
    private fun savePresentation(outState: Bundle) {
        outState.putString("page", page)
        outState.putBoolean("optionsExpanded", optionsExpanded); outState.putBoolean("advancedExpanded", advancedExpanded); outState.putBoolean("checklistExpanded", checklistExpanded)
        tutorial.save(outState)
    }
    override fun onSaveInstanceState(outState: Bundle) { savePresentation(outState); super.onSaveInstanceState(outState) }
    private fun updateHint(id: Int) { hintText = getString(id); hintView?.text = hintText }

    override fun onStart() {
        super.onStart()
        tutorial.resume()
        observationEpoch += 1
        val epoch = observationEpoch
        updateHint(R.string.hint_waiting)
        val callback = object : AudioDeviceCallback() {
            override fun onAudioDevicesAdded(addedDevices: Array<out AudioDeviceInfo>) {
                if (observing && observationEpoch == epoch) updateHint(R.string.hint_added)
            }

            override fun onAudioDevicesRemoved(removedDevices: Array<out AudioDeviceInfo>) {
                if (observing && observationEpoch == epoch) updateHint(R.string.hint_removed)
            }
        }
        try {
            (getSystemService(AUDIO_SERVICE) as AudioManager).registerAudioDeviceCallback(
                callback, Handler(Looper.getMainLooper())
            )
            deviceCallback = callback
            observing = true
        } catch (_: RuntimeException) {
            updateHint(R.string.hint_unavailable)
        }
    }

    override fun onStop() {
        tutorial.pause()
        observationEpoch += 1
        observing = false
        deviceCallback?.let { callback ->
            runCatching {
                (getSystemService(AUDIO_SERVICE) as AudioManager).unregisterAudioDeviceCallback(callback)
            }
        }
        deviceCallback = null
        updateHint(R.string.hint_paused)
        super.onStop()
    }
}
