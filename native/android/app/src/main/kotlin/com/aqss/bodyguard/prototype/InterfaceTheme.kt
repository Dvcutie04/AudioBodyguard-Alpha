package com.aqss.bodyguard.prototype

import android.app.Activity
import android.content.res.ColorStateList
import android.graphics.Canvas
import android.graphics.Paint
import android.graphics.Path
import android.graphics.drawable.GradientDrawable
import android.graphics.drawable.RippleDrawable
import android.view.View
import android.widget.Button
import com.aqss.nativefeedback.InterfaceContent

/** Local presentation tokens. No device, audio or observation dependencies. */
class InterfaceTheme(val activity: Activity, val dark: Boolean) {
    private val palette = InterfaceContent.palettes.getValue(if (dark) "midnight" else "daylight")
    fun color(key: String) = palette.getValue(key)
    val background get() = color("background")
    val surface get() = color("surface")
    val raised get() = color("raised")
    val text get() = color("text")
    val muted get() = color("muted")
    val accent get() = color("accent")
    val violet get() = color("violet")
    val warning get() = color("warning")
    val outline get() = color("outline")
    fun dp(value: Int) = (value * activity.resources.displayMetrics.density).toInt()
    fun shape(fill: Int, radius: Int = 18, border: Boolean = false) = GradientDrawable().apply {
        setColor(fill); cornerRadius = dp(radius).toFloat()
        if (border) setStroke(dp(1), outline)
    }
    fun card() = GradientDrawable(GradientDrawable.Orientation.TL_BR, intArrayOf(raised, surface)).apply {
        cornerRadius = dp(22).toFloat(); setStroke(dp(1), outline)
    }
    fun style(button: Button, primary: Boolean = false) {
        button.isAllCaps = false; button.minHeight = dp(48); button.minimumWidth = 0
        button.setPadding(dp(12), dp(9), dp(12), dp(9)); button.textSize = 15f
        button.setTextColor(ColorStateList(arrayOf(intArrayOf(-android.R.attr.state_enabled), intArrayOf()), intArrayOf(muted, if (primary) background else accent)))
        button.background = RippleDrawable(ColorStateList.valueOf(outline), shape(if (primary) accent else raised, 14), null)
        button.stateListAnimator = null
    }
}

/** Static vector decoration or an explicitly synthetic example; never a live signal. */
class InterfaceGraphic(activity: Activity, private val skin: InterfaceTheme, private val kind: String) : View(activity) {
    private val paint = Paint(Paint.ANTI_ALIAS_FLAG)
    init {
        importantForAccessibility = if (kind == "chart") IMPORTANT_FOR_ACCESSIBILITY_YES else IMPORTANT_FOR_ACCESSIBILITY_NO
        if (kind == "chart") contentDescription = "Example chart. Synthetic relative levels: 18, 24, 21, 64, 40, 30, 45, 25. No measured audio."
    }
    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        val w = width.toFloat(); val h = height.toFloat()
        paint.style = Paint.Style.STROKE; paint.strokeWidth = skin.dp(1).toFloat()
        if (kind == "orbit") {
            for (i in 0..2) {
                paint.color = if (i == 1) skin.violet else skin.accent; paint.alpha = 100
                canvas.drawCircle(w / 2, h / 2, minOf(w, h) * (.45f - i * .10f), paint)
            }
            paint.alpha = 255; paint.color = skin.accent; paint.strokeWidth = skin.dp(2).toFloat()
            val p = Path(); p.moveTo(w * .29f, h * .5f)
            for ((x, y) in listOf(.38f to .5f, .43f to .35f, .50f to .66f, .58f to .41f, .64f to .5f, .72f to .5f)) p.lineTo(w * x, h * y)
            canvas.drawPath(p, paint)
        } else if (kind == "chart") {
            paint.color = skin.outline; paint.alpha = 255
            for (i in 0..2) canvas.drawLine(0f, h * i / 2, w, h * i / 2, paint)
            paint.color = skin.accent; paint.strokeWidth = skin.dp(3).toFloat(); paint.strokeJoin = Paint.Join.ROUND
            val p = Path()
            for ((i, value) in InterfaceContent.exampleValues.withIndex()) {
                val x = w * i / (InterfaceContent.exampleValues.size - 1); val y = h * (1 - value / 100)
                if (i == 0) p.moveTo(x, y) else p.lineTo(x, y)
            }
            canvas.drawPath(p, paint)
        } else {
            paint.color = skin.violet; paint.alpha = 255; paint.strokeWidth = skin.dp(2).toFloat()
            val mid = h / 2
            for ((i, size) in listOf(8, 17, 26, 14, 34, 22, 10).withIndex()) {
                val x = w / 2 + (i - 3) * skin.dp(9)
                canvas.drawLine(x, mid - skin.dp(size) / 2, x, mid + skin.dp(size) / 2, paint)
            }
        }
    }
}
