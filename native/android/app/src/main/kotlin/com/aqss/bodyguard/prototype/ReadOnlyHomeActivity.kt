package com.aqss.bodyguard.prototype

import android.app.Activity
import android.media.AudioDeviceCallback
import android.media.AudioDeviceInfo
import android.media.AudioManager
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.util.TypedValue
import android.view.View
import android.view.ViewGroup
import android.widget.Button
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import com.aqss.nativefeedback.CapabilityFacts
import com.aqss.nativefeedback.SessionEvidenceView
import com.aqss.nativefeedback.SessionState

/** Read-only prototype: connected-device hints never count as playback evidence. */
class ReadOnlyHomeActivity : Activity() {
    private var optionsExpanded = false
    private var advancedExpanded = false
    private var hintView: TextView? = null
    private var deviceCallback: AudioDeviceCallback? = null
    private var observationEpoch = 0
    private var observing = false

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        optionsExpanded = savedInstanceState?.getBoolean("optionsExpanded") ?: false
        advancedExpanded = optionsExpanded && (savedInstanceState?.getBoolean("advancedExpanded") ?: false)
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

        fun line(target: LinearLayout, text: String, size: Float, heading: Boolean = false): TextView {
            val view = TextView(this).apply {
                this.text = text
                setTextSize(TypedValue.COMPLEX_UNIT_SP, size)
                if (heading) setTypeface(null, android.graphics.Typeface.BOLD)
                setPadding(0, 0, 0, (14 * resources.displayMetrics.density).toInt())
            }
            target.addView(view)
            return view
        }

        fun menuSection(target: LinearLayout, title: Int, detail: Int) {
            line(target, getString(title), 20f, heading = true)
            line(target, getString(detail), 16f)
        }

        line(column, getString(R.string.simulation), 18f, heading = true)
        val optionsContent = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            visibility = if (optionsExpanded) View.VISIBLE else View.GONE
        }
        val optionsButton = Button(this).apply { isAllCaps = false }
        optionsButton.setText(if (optionsExpanded) R.string.options_close else R.string.options_open)
        column.addView(optionsButton)
        column.addView(optionsContent)
        line(optionsContent, getString(R.string.options_scope), 17f)
        menuSection(optionsContent, R.string.option_volume, R.string.option_volume_unavailable)
        menuSection(optionsContent, R.string.option_captions, R.string.option_captions_unavailable)
        menuSection(optionsContent, R.string.option_sound, R.string.option_sound_unavailable)
        menuSection(optionsContent, R.string.option_dialogue, R.string.option_dialogue_unavailable)
        menuSection(optionsContent, R.string.option_night, R.string.option_night_unavailable)
        menuSection(optionsContent, R.string.option_equalizer, R.string.option_equalizer_unavailable)
        menuSection(optionsContent, R.string.option_defaults, R.string.option_defaults_unavailable)

        val advancedContent = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            visibility = if (advancedExpanded) View.VISIBLE else View.GONE
        }
        val advancedButton = Button(this).apply { isAllCaps = false }
        advancedButton.setText(if (advancedExpanded) R.string.advanced_close else R.string.advanced_open)
        optionsContent.addView(advancedButton)
        optionsContent.addView(advancedContent)
        menuSection(advancedContent, R.string.advanced_route, R.string.advanced_route_unknown)
        menuSection(advancedContent, R.string.advanced_physical, R.string.advanced_physical_unknown)
        menuSection(advancedContent, R.string.advanced_background, R.string.advanced_background_unavailable)
        menuSection(advancedContent, R.string.advanced_privacy, R.string.advanced_privacy_detail)
        menuSection(advancedContent, R.string.advanced_handoff, R.string.advanced_handoff_unavailable)
        optionsButton.setOnClickListener {
            optionsExpanded = !optionsExpanded
            if (!optionsExpanded) {
                advancedExpanded = false
                advancedContent.visibility = View.GONE
                advancedButton.setText(R.string.advanced_open)
            }
            optionsContent.visibility = if (optionsExpanded) View.VISIBLE else View.GONE
            optionsButton.setText(if (optionsExpanded) R.string.options_close else R.string.options_open)
        }
        advancedButton.setOnClickListener {
            advancedExpanded = !advancedExpanded
            advancedContent.visibility = if (advancedExpanded) View.VISIBLE else View.GONE
            advancedButton.setText(if (advancedExpanded) R.string.advanced_close else R.string.advanced_open)
        }

        line(column, getString(R.string.coverage_title), 24f, heading = true)
        line(column, getString(R.string.coverage_unknown), 20f, heading = true)
        line(column, getString(R.string.no_observation), 17f)
        line(column, getString(R.string.capability_title), 20f, heading = true)
        line(column, getString(capabilitySummary), 17f)
        line(column, getString(R.string.capability_unknown), 15f)
        line(column, getString(R.string.caption_title), 20f, heading = true)
        line(column, getString(R.string.caption_unknown), 17f)
        line(column, getString(R.string.history_title), 20f, heading = true)
        line(column, getString(R.string.history_unknown), 17f)
        line(column, getString(R.string.hint_title), 20f, heading = true)
        hintView = line(column, getString(R.string.hint_waiting), 17f)
        line(column, getString(R.string.hint_scope), 15f)
        line(column, getString(R.string.handoff_title), 20f, heading = true)
        line(column, getString(R.string.handoff_unavailable), 17f)
        line(column, getString(R.string.next_step_title), 20f, heading = true)
        line(column, getString(R.string.next_step), 17f)
        setContentView(scroll)
    }

    override fun onSaveInstanceState(outState: Bundle) {
        outState.putBoolean("optionsExpanded", optionsExpanded)
        outState.putBoolean("advancedExpanded", advancedExpanded)
        super.onSaveInstanceState(outState)
    }

    override fun onStart() {
        super.onStart()
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
