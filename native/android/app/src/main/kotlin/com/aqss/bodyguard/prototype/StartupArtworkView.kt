package com.aqss.bodyguard.prototype

import android.content.Context
import android.graphics.BitmapFactory
import android.graphics.Canvas
import android.graphics.Paint
import android.graphics.RectF
import android.view.View
import kotlin.math.min

/** Fits the owner's complete portrait asset without splitting, cropping,
 * stretching or mutating the title, artwork and Silicon Workforce credit. */
internal class StartupArtworkView(context: Context) : View(context) {
    private val artwork = BitmapFactory.decodeResource(resources, R.drawable.startup_artwork,
        BitmapFactory.Options().apply { inScaled = false })
    private val paint = Paint(Paint.ANTI_ALIAS_FLAG or Paint.FILTER_BITMAP_FLAG)

    init { contentDescription = "Audio Bodyguard. Silicon Workforce." }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        val contentWidth = width - paddingLeft - paddingRight
        val contentHeight = height - paddingTop - paddingBottom
        if (contentWidth <= 0 || contentHeight <= 0) return
        canvas.save()
        canvas.translate(paddingLeft.toFloat(), paddingTop.toFloat())
        val scale = min(contentWidth.toFloat() / artwork.width, contentHeight.toFloat() / artwork.height)
        val drawnWidth = artwork.width * scale
        val drawnHeight = artwork.height * scale
        val left = (contentWidth - drawnWidth) / 2f
        val top = (contentHeight - drawnHeight) / 2f
        canvas.drawBitmap(artwork, null, RectF(left, top, left + drawnWidth, top + drawnHeight), paint)
        canvas.restore()
    }

    override fun onDetachedFromWindow() {
        super.onDetachedFromWindow()
        artwork.recycle()
    }
}
