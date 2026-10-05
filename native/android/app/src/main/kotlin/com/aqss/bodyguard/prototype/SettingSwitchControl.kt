package com.aqss.bodyguard.prototype

import android.animation.ValueAnimator
import android.app.Activity
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.view.View
import android.widget.CompoundButton

/** Accessible iOS-style pill, with the owner's cyan active color. */
internal class SettingSwitchControl(activity: Activity, private val skin: InterfaceTheme) : CompoundButton(activity) {
    private val paint = Paint(Paint.ANTI_ALIAS_FLAG)
    private var position = 0f
    private var motion: ValueAnimator? = null
    init {
        buttonDrawable = null
        minimumWidth = skin.dp(64); minimumHeight = skin.dp(48)
        setPadding(0, 0, 0, 0)
        isFocusable = true
    }
    override fun getAccessibilityClassName(): CharSequence = "android.widget.Switch"
    override fun setChecked(checked: Boolean) {
        val previous = isChecked
        super.setChecked(checked)
        if (previous == isChecked) return
        motion?.cancel()
        val end = if (isChecked) 1f else 0f
        if (isAttachedToWindow && ValueAnimator.areAnimatorsEnabled()) {
            motion = ValueAnimator.ofFloat(position, end).apply {
                duration = 180
                addUpdateListener { position = it.animatedValue as Float; invalidate() }
                start()
            }
        } else { position = end; invalidate() }
    }
    override fun onDraw(canvas: Canvas) {
        val w = skin.dp(56).toFloat(); val h = skin.dp(34).toFloat()
        val left = (width - w) / 2f; val top = (height - h) / 2f
        paint.style = Paint.Style.FILL
        paint.color = if (isChecked) skin.control else Color.rgb(199, 199, 201)
        canvas.drawRoundRect(left, top, left + w, top + h, h / 2, h / 2, paint)
        // Thin neutral boundary remains visible against the white row.
        paint.style = Paint.Style.STROKE; paint.strokeWidth = .7f * resources.displayMetrics.density
        paint.color = if (isChecked) skin.controlBorder else Color.rgb(128, 128, 132)
        canvas.drawRoundRect(left, top, left + w, top + h, h / 2, h / 2, paint)
        paint.style = Paint.Style.FILL; paint.color = Color.WHITE
        val radius = h / 2 - skin.dp(3)
        canvas.drawCircle(left + h / 2 + (w - h) * position, top + h / 2, radius, paint)
    }
    override fun onDetachedFromWindow() { motion?.cancel(); motion = null; super.onDetachedFromWindow() }
    override fun onVisibilityChanged(changedView: View, visibility: Int) {
        super.onVisibilityChanged(changedView, visibility)
        if (visibility != View.VISIBLE) { motion?.cancel(); position = if (isChecked) 1f else 0f }
    }
}
