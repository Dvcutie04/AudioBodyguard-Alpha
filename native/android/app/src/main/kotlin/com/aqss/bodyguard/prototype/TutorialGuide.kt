package com.aqss.bodyguard.prototype

import android.animation.ValueAnimator
import android.app.Activity
import android.app.AlertDialog
import android.graphics.Color
import android.graphics.drawable.Drawable
import android.graphics.drawable.GradientDrawable
import android.os.Bundle
import android.view.View
import android.view.ViewTreeObserver
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
    private val expansion: () -> Pair<Boolean, Boolean>,
    private val setExpansion: (Boolean, Boolean) -> Unit,
) {
    val footer = LinearLayout(activity).apply { orientation = LinearLayout.VERTICAL }
    private val panel = LinearLayout(activity).apply {
        orientation = LinearLayout.VERTICAL
        visibility = View.GONE
        setPadding(dp(12), dp(8), dp(12), 0)
    }
    private val text = TextView(activity).apply {
        textSize = 16f
        accessibilityLiveRegion = View.ACCESSIBILITY_LIVE_REGION_POLITE
    }
    private val explanation = ScrollView(activity).apply { addView(text) }
    private val back = button("Back") { move(-1) }
    private val next = button("Next") { move(1) }
    private var topic: TutorialTopic? = null
    private var index = 0
    private var previous = false to false
    private var highlighted: View? = null
    private var originalForeground: Drawable? = null
    private var pendingLayout: ViewTreeObserver.OnGlobalLayoutListener? = null

    init {
        panel.addView(explanation, LinearLayout.LayoutParams(-1, dp(150)))
        val navigation = LinearLayout(activity)
        for (item in listOf(back, next, button("Close tutorial") { close() })) {
            navigation.addView(item, LinearLayout.LayoutParams(0, -2, 1f))
        }
        panel.addView(navigation)
        footer.addView(panel)
        footer.addView(button("Help & tutorials") { chooseTopic() })
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
        setExpansion(step.area != "home", step.area == "advanced")
        text.text = "Tutorial — ${selected.title}\nStep ${index + 1} of ${selected.steps.size} • Highlighted: ${step.title}\n\n${step.explanation}\n\n${step.example}"
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
        val listener = object : ViewTreeObserver.OnGlobalLayoutListener {
            override fun onGlobalLayout() {
                if (scroll.viewTreeObserver.isAlive) scroll.viewTreeObserver.removeOnGlobalLayoutListener(this)
                pendingLayout = null
                highlighted = target
                originalForeground = target.foreground
                target.foreground = GradientDrawable().apply {
                    setColor(Color.TRANSPARENT)
                    setStroke(dp(3), Color.rgb(0, 96, 180))
                    cornerRadius = dp(6).toFloat()
                }
                var y = target.top
                var parent = target.parent as? View
                while (parent != null && parent !== scroll) { y += parent.top; parent = parent.parent as? View }
                if (ValueAnimator.areAnimatorsEnabled()) scroll.smoothScrollTo(0, y) else scroll.scrollTo(0, y)
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
        if (restore) setExpansion(previous.first, previous.second)
    }

    fun pause() { text.animate().cancel(); clearHighlight() }
    fun resume() { if (topic != null) render() }

    fun save(bundle: Bundle) {
        topic?.let {
            bundle.putString("tutorialTopic", it.id)
            bundle.putInt("tutorialIndex", index)
            bundle.putBoolean("tutorialPreviousOptions", previous.first)
            bundle.putBoolean("tutorialPreviousAdvanced", previous.second)
        }
    }

    fun restore(bundle: Bundle?) {
        val id = bundle?.getString("tutorialTopic") ?: return
        val selected = TutorialContent.topics.firstOrNull { it.id == id } ?: return
        val position = bundle.getInt("tutorialIndex")
        if (position !in selected.steps.indices) return
        topic = selected
        index = position
        previous = bundle.getBoolean("tutorialPreviousOptions") to bundle.getBoolean("tutorialPreviousAdvanced")
        render()
    }
}
