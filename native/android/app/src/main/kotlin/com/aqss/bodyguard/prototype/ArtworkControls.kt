package com.aqss.bodyguard.prototype

import android.animation.ObjectAnimator
import android.animation.ValueAnimator
import android.app.Activity
import android.graphics.Canvas
import android.graphics.ColorMatrix
import android.graphics.ColorMatrixColorFilter
import android.graphics.ColorFilter
import android.graphics.PixelFormat
import android.graphics.drawable.Drawable
import android.view.View
import android.widget.Button
import android.widget.ImageView

internal fun roseButton(activity: Activity, skin: InterfaceTheme, title: String, compact: Boolean = false, action: () -> Unit): Button = Button(activity).apply {
    text = if (compact || activity.resources.configuration.fontScale >= 1.5f) "" else title
    contentDescription = title
    skin.style(this)
    val art = AspectFitArtwork(activity.resources.getDrawable(R.drawable.tribal_rose, activity.theme))
    art.setBounds(0, 0, skin.dp(26), skin.dp(34))
    setCompoundDrawables(art, null, null, null)
    compoundDrawablePadding = skin.dp(if (compact) 0 else 8)
    setOnClickListener { action() }
}

/** Keep the full transparent rose silhouette inside its button icon bounds. */
private class AspectFitArtwork(private val artwork: Drawable) : Drawable() {
    override fun draw(canvas: Canvas) {
        val scale = minOf(bounds.width().toFloat() / artwork.intrinsicWidth, bounds.height().toFloat() / artwork.intrinsicHeight)
        val checkpoint = canvas.save()
        canvas.clipRect(bounds)
        canvas.translate(bounds.exactCenterX() - artwork.intrinsicWidth * scale / 2, bounds.exactCenterY() - artwork.intrinsicHeight * scale / 2)
        canvas.scale(scale, scale)
        artwork.setBounds(0, 0, artwork.intrinsicWidth, artwork.intrinsicHeight)
        artwork.draw(canvas)
        canvas.restoreToCount(checkpoint)
    }
    override fun setAlpha(alpha: Int) { artwork.alpha = alpha }
    override fun setColorFilter(colorFilter: ColorFilter?) { artwork.colorFilter = colorFilter }
    @Suppress("DEPRECATION") override fun getOpacity(): Int = PixelFormat.TRANSLUCENT
}

/** No tutorial or button can set this view's evidence-backed connection input. */
internal class ConnectionHeadView(activity: Activity, private val connected: Boolean) : ImageView(activity) {
    private var pulse: ObjectAnimator? = null
    init {
        setImageResource(R.drawable.connection_head)
        scaleType = ScaleType.FIT_CENTER
        if (!connected) colorFilter = ColorMatrixColorFilter(ColorMatrix().apply { setSaturation(0f) })
        contentDescription = if (connected) "AI head. Verified connection active." else "AI head. Connection not verified. Black and white."
    }
    override fun onAttachedToWindow() { super.onAttachedToWindow(); updatePulse() }
    override fun onWindowVisibilityChanged(visibility: Int) { super.onWindowVisibilityChanged(visibility); updatePulse() }
    override fun onVisibilityChanged(changedView: View, visibility: Int) { super.onVisibilityChanged(changedView, visibility); updatePulse() }
    override fun onDetachedFromWindow() { pulse?.cancel(); pulse = null; alpha = 1f; super.onDetachedFromWindow() }
    private fun updatePulse() {
        pulse?.cancel(); pulse = null; alpha = 1f
        if (connected && isShown && isAttachedToWindow && windowVisibility == View.VISIBLE && ValueAnimator.areAnimatorsEnabled()) {
            pulse = ObjectAnimator.ofFloat(this, "alpha", 1f, .82f).apply {
                duration = 1800; repeatCount = ValueAnimator.INFINITE; repeatMode = ValueAnimator.REVERSE; start()
            }
        }
    }
}
