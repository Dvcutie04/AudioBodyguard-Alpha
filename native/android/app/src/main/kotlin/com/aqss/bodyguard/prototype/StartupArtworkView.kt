package com.aqss.bodyguard.prototype

import android.content.Context
import android.graphics.BitmapFactory
import android.graphics.Canvas
import android.graphics.Paint
import android.graphics.Rect
import android.graphics.RectF
import android.view.View
import kotlin.math.min

/** Draws three uncropped-width slices of the owner's exact portrait asset.
 * The title stays at the top, the rose is centered, and the credit stays at
 * the bottom without stretching or mutating the supplied image. */
internal class StartupArtworkView(context: Context) : View(context) {
    private val artwork = BitmapFactory.decodeResource(resources, R.drawable.startup_artwork,
        BitmapFactory.Options().apply { inScaled = false })
    private val paint = Paint(Paint.ANTI_ALIAS_FLAG or Paint.FILTER_BITMAP_FLAG)

    init { contentDescription = "Audio Bodyguard. Silicon Workforce." }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        if (width <= 0 || height <= 0) return
        val scale = min(width.toFloat() / artwork.width, height.toFloat() / artwork.height)
        val drawnWidth = artwork.width * scale
        val left = (width - drawnWidth) / 2f
        val titleEnd = (artwork.height * (290f / 1733f)).toInt()
        val creditStart = (artwork.height * (1535f / 1733f)).toInt()
        fun section(from: Int, to: Int, top: Float) {
            canvas.drawBitmap(artwork, Rect(0, from, artwork.width, to),
                RectF(left, top, left + drawnWidth, top + (to - from) * scale), paint)
        }
        section(0, titleEnd, 0f)
        section(titleEnd, creditStart, (height - (creditStart - titleEnd) * scale) / 2f)
        section(creditStart, artwork.height, height - (artwork.height - creditStart) * scale)
    }

    override fun onDetachedFromWindow() {
        super.onDetachedFromWindow()
        artwork.recycle()
    }
}
