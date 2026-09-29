package com.aqss.bodyguard.prototype

import android.app.Activity
import android.app.AlertDialog
import android.widget.LinearLayout
import android.widget.ScrollView
import android.content.res.ColorStateList
import android.graphics.Canvas
import android.graphics.ColorFilter
import android.graphics.Paint
import android.graphics.Path
import android.graphics.PixelFormat
import android.graphics.drawable.Drawable
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
    val control get() = color("control")
    val controlText get() = color("controlText")
    val controlBorder get() = color("controlBorder")
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
        button.setTextColor(ColorStateList(arrayOf(intArrayOf(-android.R.attr.state_enabled), intArrayOf()), intArrayOf(muted, controlText)))
        button.background = RippleDrawable(ColorStateList.valueOf(outline), shape(control, 14).apply { setStroke(dp(1), controlBorder) }, null)
        button.stateListAnimator = null
    }
    fun menu(title: String, items: List<Pair<String, () -> Unit>>) {
        val list = LinearLayout(activity).apply { orientation = LinearLayout.VERTICAL; setPadding(dp(20), dp(10), dp(20), dp(10)) }
        val scroll = ScrollView(activity).apply { addView(list); setBackgroundColor(this@InterfaceTheme.background) }
        val dialog = AlertDialog.Builder(activity).setTitle(title).setView(scroll).create()
        for ((label, action) in items + ("Cancel" to {})) {
            list.addView(Button(activity).apply {
                text = label; style(this); setOnClickListener { dialog.dismiss(); action() }
            }, LinearLayout.LayoutParams(-1, -2).apply { bottomMargin = dp(10) })
        }
        dialog.show()
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

/** Small, scalable navigation glyphs; button text supplies their accessible name. */
class InterfaceSymbol(private val skin: InterfaceTheme, private val kind: String, color: Int) : Drawable() {
    private val paint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        this.color = color; style = Paint.Style.STROKE; strokeWidth = 1.6f
        strokeCap = Paint.Cap.ROUND; strokeJoin = Paint.Join.ROUND
    }
    override fun getIntrinsicWidth() = skin.dp(23)
    override fun getIntrinsicHeight() = skin.dp(23)
    override fun draw(canvas: Canvas) {
        val saved = canvas.save()
        canvas.translate(bounds.left.toFloat(), bounds.top.toFloat())
        canvas.scale(bounds.width() / 24f, bounds.height() / 24f)
        when (kind) {
            "tv" -> {
                canvas.drawRoundRect(2f, 3f, 22f, 17f, 2f, 2f, paint)
                canvas.drawLine(12f, 17f, 12f, 21f, paint); canvas.drawLine(7f, 21f, 17f, 21f, paint)
            }
            "speaker" -> {
                canvas.drawRoundRect(5f, 2f, 19f, 22f, 5f, 5f, paint)
                canvas.drawOval(5f, 2f, 19f, 7f, paint); canvas.drawCircle(12f, 14f, 3f, paint)
            }
            "house" -> {
                val p = Path().apply { moveTo(2f, 11f); lineTo(12f, 2f); lineTo(22f, 11f); moveTo(5f, 9f); lineTo(5f, 21f); lineTo(19f, 21f); lineTo(19f, 9f) }
                canvas.drawPath(p, paint); canvas.drawRect(10f, 14f, 14f, 21f, paint)
            }
            "questionmark.circle" -> {
                canvas.drawCircle(12f, 12f, 10f, paint)
                canvas.drawArc(8f, 5f, 16f, 13f, 180f, 240f, false, paint)
                canvas.drawLine(12f, 12f, 12f, 14f, paint); canvas.drawPoint(12f, 18f, paint)
            }
            "home" -> {
                val p = Path().apply { moveTo(12f, 2f); lineTo(20f, 5f); lineTo(20f, 12f); cubicTo(20f, 17f, 16f, 20f, 12f, 22f); cubicTo(8f, 20f, 4f, 17f, 4f, 12f); lineTo(4f, 5f); close() }
                canvas.drawPath(p, paint); canvas.drawLine(12f, 5f, 12f, 19f, paint)
            }
            "sound" -> for ((x, y) in listOf(5f to 8f, 12f to 16f, 19f to 10f)) {
                canvas.drawLine(x, 3f, x, y - 3, paint); canvas.drawLine(x, y + 3, x, 21f, paint)
                canvas.drawRoundRect(x - 2, y - 3, x + 2, y + 3, 1f, 1f, paint)
            }
            "devices" -> {
                canvas.drawRoundRect(3f, 3f, 11f, 21f, 2f, 2f, paint)
                canvas.drawLine(6f, 18f, 8f, 18f, paint)
                canvas.drawRoundRect(15f, 7f, 22f, 21f, 1.5f, 1.5f, paint)
                canvas.drawCircle(18.5f, 15.5f, 2f, paint); canvas.drawPoint(18.5f, 10f, paint)
            }
            "insights" -> {
                canvas.drawLine(3f, 3f, 3f, 21f, paint); canvas.drawLine(3f, 21f, 22f, 21f, paint)
                val p = Path().apply { moveTo(6f, 15f); lineTo(11f, 10f); lineTo(15f, 13f); lineTo(21f, 5f) }
                canvas.drawPath(p, paint)
            }
            else -> {
                canvas.drawCircle(12f, 12f, 7f, paint); canvas.drawCircle(12f, 12f, 2.5f, paint)
                repeat(8) {
                    val angle = it * Math.PI / 4
                    val x = kotlin.math.cos(angle).toFloat(); val y = kotlin.math.sin(angle).toFloat()
                    canvas.drawLine(12 + x * 7, 12 + y * 7, 12 + x * 10, 12 + y * 10, paint)
                }
            }
        }
        canvas.restoreToCount(saved)
    }
    override fun setAlpha(alpha: Int) { paint.alpha = alpha; invalidateSelf() }
    override fun setColorFilter(colorFilter: ColorFilter?) { paint.colorFilter = colorFilter; invalidateSelf() }
    @Deprecated("Required Drawable compatibility override")
    override fun getOpacity() = PixelFormat.TRANSLUCENT
}
