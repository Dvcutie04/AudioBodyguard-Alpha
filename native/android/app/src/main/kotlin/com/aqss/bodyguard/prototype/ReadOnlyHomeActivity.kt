package com.aqss.bodyguard.prototype

import android.app.Activity
import android.media.AudioDeviceCallback
import android.media.AudioDeviceInfo
import android.media.AudioManager
import android.os.Bundle
import android.os.Build
import android.os.Handler
import android.os.Looper
import android.util.TypedValue
import android.view.View
import android.view.ViewGroup
import android.view.WindowInsets
import android.widget.Button
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import com.aqss.nativefeedback.CapabilityFacts
import com.aqss.nativefeedback.SessionEvidenceView
import com.aqss.nativefeedback.SessionState
import com.aqss.nativefeedback.TutorialContent
import android.window.OnBackInvokedCallback
import android.window.OnBackInvokedDispatcher

/** Read-only prototype: connected-device hints never count as playback evidence. */
class ReadOnlyHomeActivity : Activity() {
    private var optionsExpanded = false
    private var advancedExpanded = false
    private var checklistExpanded = false
    private lateinit var setExpanded: (Boolean, Boolean, Boolean) -> Unit
    private var backCallback: OnBackInvokedCallback? = null
    private lateinit var tutorial: TutorialGuide
    private var hintView: TextView? = null
    private var deviceCallback: AudioDeviceCallback? = null
    private var observationEpoch = 0
    private var observing = false

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        optionsExpanded = savedInstanceState?.getBoolean("optionsExpanded") ?: false
        advancedExpanded = optionsExpanded && (savedInstanceState?.getBoolean("advancedExpanded") ?: false)
        checklistExpanded = savedInstanceState?.getBoolean("checklistExpanded") ?: false
        // The native projector receives no observation. Never synthesize an ACTIVE sample.
        val coverage = SessionEvidenceView.coverage(null, "prototype", "prototype", 0.0)
        require(coverage.state == SessionState.UNKNOWN_PHYSICAL_STATE && coverage.reason == "NO_OBSERVATION")
        val capability = SessionEvidenceView.capability(
            CapabilityFacts(null, null, null, null, null, null, 0.0, 0.0, "prototype"),
            "prototype", 0.0
        )
        val capabilitySummary = if (capability.label == "UNKNOWN" && !capability.canActuate &&
            capability.reasons.size == 6
        ) R.string.six_checks_unknown else R.string.checks_unconfirmed

        val scroll = ScrollView(this)
        val column = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            val padding = (24 * resources.displayMetrics.density).toInt()
            setPadding(padding, padding, padding, padding)
        }
        scroll.addView(column, ViewGroup.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT))
        val tutorialTargets = mutableMapOf<String, View>()

        fun line(target: LinearLayout, text: String, size: Float, heading: Boolean = false): TextView {
            val view = TextView(this).apply {
                this.text = text
                setTextSize(TypedValue.COMPLEX_UNIT_SP, size)
                if (heading) {
                    setTypeface(null, android.graphics.Typeface.BOLD)
                    if (Build.VERSION.SDK_INT >= 28) isAccessibilityHeading = true
                }
                setPadding(0, 0, 0, (14 * resources.displayMetrics.density).toInt())
            }
            target.addView(view)
            return view
        }

        fun menuSection(target: LinearLayout, title: Int, detail: Int, tutorialTarget: String? = null) {
            val heading = line(target, getString(title), 20f, heading = true)
            if (tutorialTarget != null) tutorialTargets[tutorialTarget] = heading
            line(target, getString(detail), 16f)
        }

        line(column, getString(R.string.simulation), 18f, heading = true)
        val optionsContent = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            visibility = if (optionsExpanded) View.VISIBLE else View.GONE
        }
        val optionsButton = Button(this).apply { isAllCaps = false; minHeight = dp(48) }
        optionsButton.setText(if (optionsExpanded) R.string.options_close else R.string.options_open)
        column.addView(optionsButton)
        tutorialTargets["options"] = optionsButton
        column.addView(optionsContent)
        line(optionsContent, getString(R.string.options_scope), 17f)
        optionsContent.addView(Button(this).apply {
            text = "Help with options"; isAllCaps = false; minHeight = dp(48)
            setOnClickListener { tutorial.start("sound") }
        })
        menuSection(optionsContent, R.string.option_volume, R.string.option_volume_unavailable, "volume")
        menuSection(optionsContent, R.string.option_captions, R.string.option_captions_unavailable, "captionOption")
        menuSection(optionsContent, R.string.option_sound, R.string.option_sound_unavailable, "sound")
        menuSection(optionsContent, R.string.option_dialogue, R.string.option_dialogue_unavailable)
        menuSection(optionsContent, R.string.option_night, R.string.option_night_unavailable)
        menuSection(optionsContent, R.string.option_equalizer, R.string.option_equalizer_unavailable, "equalizer")
        menuSection(optionsContent, R.string.option_defaults, R.string.option_defaults_unavailable, "defaults")

        val advancedContent = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            visibility = if (advancedExpanded) View.VISIBLE else View.GONE
        }
        val advancedButton = Button(this).apply { isAllCaps = false; minHeight = dp(48) }
        advancedButton.setText(if (advancedExpanded) R.string.advanced_close else R.string.advanced_open)
        optionsContent.addView(advancedButton)
        tutorialTargets["advanced"] = advancedButton
        optionsContent.addView(advancedContent)
        advancedContent.addView(Button(this).apply {
            text = "Help with advanced options"; isAllCaps = false; minHeight = dp(48)
            setOnClickListener { tutorial.start("advanced") }
        })
        menuSection(advancedContent, R.string.advanced_route, R.string.advanced_route_unknown, "route")
        menuSection(advancedContent, R.string.advanced_physical, R.string.advanced_physical_unknown, "physical")
        menuSection(advancedContent, R.string.advanced_background, R.string.advanced_background_unavailable, "background")
        menuSection(advancedContent, R.string.advanced_privacy, R.string.advanced_privacy_detail, "privacy")
        menuSection(advancedContent, R.string.advanced_handoff, R.string.advanced_handoff_unavailable, "handoffOption")
        optionsButton.setOnClickListener {
            tutorial.close(restore = false)
            setExpanded(!optionsExpanded, false, checklistExpanded)
        }
        advancedButton.setOnClickListener {
            tutorial.close(restore = false)
            setExpanded(true, !advancedExpanded, checklistExpanded)
        }

        tutorialTargets["coverage"] = line(column, getString(R.string.coverage_title), 24f, heading = true)
        line(column, getString(R.string.coverage_unknown), 20f, heading = true)
        line(column, getString(R.string.no_observation), 17f)
        tutorialTargets["capability"] = line(column, getString(R.string.capability_title), 20f, heading = true)
        line(column, getString(capabilitySummary), 17f)
        line(column, getString(R.string.capability_unknown), 15f)
        val checklistButton = Button(this).apply { isAllCaps = false; minHeight = dp(48) }
        val checklistContent = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        column.addView(checklistButton)
        column.addView(checklistContent)
        line(checklistContent, getString(R.string.checklist_scope), 17f)
        checklistContent.addView(Button(this).apply {
            text = "Help with readiness"; isAllCaps = false; minHeight = dp(48)
            setOnClickListener { tutorial.start("readiness") }
        })
        for (step in TutorialContent.topics.single { it.id == "readiness" }.steps) {
            tutorialTargets[step.target] = line(checklistContent, "${step.title} — Unknown", 20f, heading = true)
            line(checklistContent, step.explanation, 16f)
        }
        checklistButton.setOnClickListener {
            tutorial.close(restore = false)
            setExpanded(optionsExpanded, advancedExpanded, !checklistExpanded)
        }
        tutorialTargets["captions"] = line(column, getString(R.string.caption_title), 20f, heading = true)
        line(column, getString(R.string.caption_unknown), 17f)
        tutorialTargets["history"] = line(column, getString(R.string.history_title), 20f, heading = true)
        line(column, getString(R.string.history_unknown), 17f)
        tutorialTargets["hint"] = line(column, getString(R.string.hint_title), 20f, heading = true)
        hintView = line(column, getString(R.string.hint_waiting), 17f)
        line(column, getString(R.string.hint_scope), 15f)
        tutorialTargets["handoff"] = line(column, getString(R.string.handoff_title), 20f, heading = true)
        line(column, getString(R.string.handoff_unavailable), 17f)
        line(column, getString(R.string.next_step_title), 20f, heading = true)
        line(column, getString(R.string.next_step), 17f)
        val root = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        root.addView(scroll, LinearLayout.LayoutParams(-1, 0, 1f))
        setExpanded = { options, advanced, checklist ->
                optionsExpanded = options
                advancedExpanded = options && advanced
                checklistExpanded = checklist
                optionsContent.visibility = if (optionsExpanded) View.VISIBLE else View.GONE
                advancedContent.visibility = if (advancedExpanded) View.VISIBLE else View.GONE
                checklistContent.visibility = if (checklistExpanded) View.VISIBLE else View.GONE
                optionsButton.setText(if (optionsExpanded) R.string.options_close else R.string.options_open)
                advancedButton.setText(if (advancedExpanded) R.string.advanced_close else R.string.advanced_open)
                checklistButton.setText(if (checklistExpanded) R.string.checklist_close else R.string.checklist_open)
                if (Build.VERSION.SDK_INT >= 30) {
                    optionsButton.stateDescription = if (optionsExpanded) "Expanded" else "Collapsed"
                    advancedButton.stateDescription = if (advancedExpanded) "Expanded" else "Collapsed"
                    checklistButton.stateDescription = if (checklistExpanded) "Expanded" else "Collapsed"
                }
                syncBackCallback()
        }
        setExpanded(optionsExpanded, advancedExpanded, checklistExpanded)
        tutorial = TutorialGuide(this, scroll, tutorialTargets,
            expansion = { Triple(optionsExpanded, advancedExpanded, checklistExpanded) },
            setExpansion = setExpanded,
            stateChanged = { syncBackCallback() })
        root.addView(tutorial.footer)
        if (Build.VERSION.SDK_INT >= 30) {
            window.setDecorFitsSystemWindows(false)
            root.setOnApplyWindowInsetsListener { view, insets ->
                val bars = insets.getInsets(WindowInsets.Type.systemBars() or WindowInsets.Type.displayCutout())
                view.setPadding(bars.left, bars.top, bars.right, bars.bottom)
                insets
            }
        }
        setContentView(root)
        tutorial.restore(savedInstanceState)
        syncBackCallback()
    }

    private fun dp(value: Int) = (value * resources.displayMetrics.density).toInt()

    private fun handleLocalBack(): Boolean {
        when {
            tutorial.isActive -> tutorial.close()
            advancedExpanded -> setExpanded(true, false, checklistExpanded)
            optionsExpanded -> setExpanded(false, false, checklistExpanded)
            checklistExpanded -> setExpanded(false, false, false)
            else -> return false
        }
        return true
    }

    private fun syncBackCallback() {
        if (Build.VERSION.SDK_INT < 33 || !::tutorial.isInitialized) return
        val needed = tutorial.isActive || optionsExpanded || checklistExpanded
        if (needed && backCallback == null) {
            val callback = OnBackInvokedCallback { handleLocalBack() }
            onBackInvokedDispatcher.registerOnBackInvokedCallback(OnBackInvokedDispatcher.PRIORITY_DEFAULT, callback)
            backCallback = callback
        } else if (!needed) {
            backCallback?.let { onBackInvokedDispatcher.unregisterOnBackInvokedCallback(it) }
            backCallback = null
        }
    }

    @Deprecated("Legacy Back fallback for Android 8–12")
    override fun onBackPressed() {
        if (handleLocalBack()) return
        super.onBackPressed()
    }

    override fun onDestroy() {
        if (Build.VERSION.SDK_INT >= 33) {
            backCallback?.let { onBackInvokedDispatcher.unregisterOnBackInvokedCallback(it) }
        }
        backCallback = null
        super.onDestroy()
    }

    override fun onSaveInstanceState(outState: Bundle) {
        outState.putBoolean("optionsExpanded", optionsExpanded)
        outState.putBoolean("advancedExpanded", advancedExpanded)
        outState.putBoolean("checklistExpanded", checklistExpanded)
        tutorial.save(outState)
        super.onSaveInstanceState(outState)
    }

    override fun onStart() {
        super.onStart()
        tutorial.resume()
        observationEpoch += 1
        val epoch = observationEpoch
        hintView?.setText(R.string.hint_waiting)
        val callback = object : AudioDeviceCallback() {
            override fun onAudioDevicesAdded(addedDevices: Array<out AudioDeviceInfo>) {
                if (observing && observationEpoch == epoch) hintView?.setText(R.string.hint_added)
            }

            override fun onAudioDevicesRemoved(removedDevices: Array<out AudioDeviceInfo>) {
                if (observing && observationEpoch == epoch) hintView?.setText(R.string.hint_removed)
            }
        }
        try {
            (getSystemService(AUDIO_SERVICE) as AudioManager).registerAudioDeviceCallback(
                callback, Handler(Looper.getMainLooper())
            )
            deviceCallback = callback
            observing = true
        } catch (_: RuntimeException) {
            hintView?.setText(R.string.hint_unavailable)
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
        hintView?.setText(R.string.hint_paused)
        super.onStop()
    }
}
