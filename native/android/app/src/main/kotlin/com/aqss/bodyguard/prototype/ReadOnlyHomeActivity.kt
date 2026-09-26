package com.aqss.bodyguard.prototype

import android.app.Activity
import android.os.Bundle
import android.util.TypedValue
import android.view.ViewGroup
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import com.aqss.nativefeedback.SessionEvidenceView
import com.aqss.nativefeedback.SessionState

/** Static prototype with no audio permissions, endpoint or event source. */
class ReadOnlyHomeActivity : Activity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        // The native projector receives no observation. Never synthesize an ACTIVE sample.
        val coverage = SessionEvidenceView.coverage(null, "prototype", "prototype", 0.0)
        require(coverage.state == SessionState.UNKNOWN_PHYSICAL_STATE && coverage.reason == "NO_OBSERVATION")

        val scroll = ScrollView(this)
        val column = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            val padding = (24 * resources.displayMetrics.density).toInt()
            setPadding(padding, padding, padding, padding)
        }
        scroll.addView(column, ViewGroup.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT))

        fun line(text: String, size: Float, heading: Boolean = false) {
            val view = TextView(this).apply {
                this.text = text
                setTextSize(TypedValue.COMPLEX_UNIT_SP, size)
                if (heading) setTypeface(null, android.graphics.Typeface.BOLD)
                setPadding(0, 0, 0, (14 * resources.displayMetrics.density).toInt())
            }
            column.addView(view)
        }

        line(getString(R.string.simulation), 18f, heading = true)
        line(getString(R.string.coverage_title), 24f, heading = true)
        line(getString(R.string.coverage_unknown), 20f, heading = true)
        line(getString(R.string.no_observation), 17f)
        line(getString(R.string.capability_title), 20f, heading = true)
        line(getString(R.string.capability_unknown), 17f)
        line(getString(R.string.caption_title), 20f, heading = true)
        line(getString(R.string.caption_unknown), 17f)
        line(getString(R.string.history_title), 20f, heading = true)
        line(getString(R.string.history_unknown), 17f)
        line(getString(R.string.next_step_title), 20f, heading = true)
        line(getString(R.string.next_step), 17f)
        setContentView(scroll)
    }
}
