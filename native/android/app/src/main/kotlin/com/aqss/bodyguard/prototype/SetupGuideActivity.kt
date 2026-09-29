package com.aqss.bodyguard.prototype

import android.app.Activity
import android.app.AlertDialog
import android.content.Intent
import android.graphics.Canvas
import android.graphics.Paint
import android.graphics.Path
import android.graphics.Typeface
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.view.Gravity
import android.view.View
import android.view.WindowInsets
import android.widget.Button
import android.widget.LinearLayout
import android.widget.ProgressBar
import android.widget.ScrollView
import android.widget.TextView
import android.window.OnBackInvokedCallback
import android.window.OnBackInvokedDispatcher
import com.aqss.nativefeedback.SetupContent
import com.aqss.nativefeedback.SetupRoute
import com.aqss.nativefeedback.SetupStep

/** Local illustrated instructions. Finishing a guide changes no connection state. */
class SetupGuideActivity : Activity() {
    private lateinit var skin: InterfaceTheme
    private lateinit var root: LinearLayout
    private lateinit var header: LinearLayout
    private lateinit var content: LinearLayout
    private lateinit var controls: LinearLayout
    private lateinit var scroll: ScrollView
    private var groupId = ""
    private var routeId: String? = null
    private var index = -1
    private var mismatch = false
    private var backCallback: OnBackInvokedCallback? = null
    private val group get() = SetupContent.groups.firstOrNull { it.id == groupId }
    private val route get() = SetupContent.routes.firstOrNull { it.id == routeId }

    override fun onCreate(savedInstanceState: Bundle?) {
        val dark = intent.getBooleanExtra("dark", true)
        setTheme(if (dark) R.style.AQSSMidnightTheme else R.style.AQSSReadOnlyTheme)
        super.onCreate(savedInstanceState)
        skin = InterfaceTheme(this, dark)
        groupId = (savedInstanceState?.getString("group") ?: intent.getStringExtra("group") ?: "")
            .takeIf { id -> SetupContent.groups.any { it.id == id } } ?: ""
        routeId = if (savedInstanceState == null && groupId == "voice") "voice" else savedInstanceState?.getString("route")?.takeIf { group?.routes?.contains(it) == true }
        index = if (savedInstanceState == null && groupId == "voice") 0 else (savedInstanceState?.getInt("index", -1) ?: -1).takeIf { it == -1 || route?.steps?.indices?.contains(it) == true } ?: -1
        mismatch = savedInstanceState?.getBoolean("mismatch", false) ?: false
        root = column().apply { setBackgroundColor(skin.background) }
        header = column().apply { setPadding(dp(16), dp(12), dp(16), dp(12)); setBackgroundColor(skin.surface) }
        content = column().apply { setPadding(dp(20), dp(20), dp(20), dp(20)) }
        controls = column().apply { setPadding(dp(16), dp(12), dp(16), dp(12)); setBackgroundColor(skin.surface) }
        scroll = ScrollView(this).apply { addView(content); clipToPadding = true }
        root.addView(header); root.addView(scroll, LinearLayout.LayoutParams(-1, 0, 1f)); root.addView(controls)
        setContentView(root)
        @Suppress("DEPRECATION")
        window.decorView.systemUiVisibility = if (dark) 0 else View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR or View.SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR
        @Suppress("DEPRECATION")
        window.statusBarColor = skin.background
        @Suppress("DEPRECATION")
        window.navigationBarColor = skin.surface
        if (Build.VERSION.SDK_INT >= 30) {
            window.setDecorFitsSystemWindows(false)
            root.setOnApplyWindowInsetsListener { v, insets ->
                val bars = insets.getInsets(WindowInsets.Type.systemBars() or WindowInsets.Type.displayCutout())
                v.setPadding(bars.left, bars.top, bars.right, bars.bottom); insets
            }
        }
        if (Build.VERSION.SDK_INT >= 33) {
            backCallback = OnBackInvokedCallback { back() }.also { onBackInvokedDispatcher.registerOnBackInvokedCallback(OnBackInvokedDispatcher.PRIORITY_DEFAULT, it) }
        }
        render()
    }
    private fun dp(v: Int) = skin.dp(v)
    private fun column() = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
    private fun words(box: LinearLayout, value: String, size: Float = 16f, color: Int = skin.text, bold: Boolean = false): TextView {
        val view = TextView(this).apply {
            text = value; textSize = size; setTextColor(color); setPadding(0, 0, 0, dp(12))
            if (bold) setTypeface(null, Typeface.BOLD)
        }
        box.addView(view, LinearLayout.LayoutParams(-1, -2)); return view
    }
    private fun button(title: String, action: () -> Unit) = Button(this).apply {
        text = title; skin.style(this); setOnClickListener { action() }
    }
    private fun action(box: LinearLayout, title: String, block: () -> Unit) {
        box.addView(button(title, block).apply { gravity = Gravity.START or Gravity.CENTER_VERTICAL }, LinearLayout.LayoutParams(-1, -2).apply { bottomMargin = dp(10) })
    }
    private fun chooseGroup(id: String) {
        groupId = id; routeId = if (id == "voice") "voice" else null; index = if (id == "voice") 0 else -1; mismatch = false; render()
    }
    private fun render() {
        header.removeAllViews(); content.removeAllViews(); controls.removeAllViews()
        val route = route
        val step = route?.steps?.getOrNull(index)
        val row = LinearLayout(this).apply { gravity = Gravity.CENTER_VERTICAL }
        row.addView(TextView(this).apply {
            text = if (route != null && index >= 0) "Step ${index + 1} of ${route.steps.size}" else "Illustrated setup"
            textSize = 17f; setTextColor(skin.text); setTypeface(null, Typeface.BOLD)
        }, LinearLayout.LayoutParams(0, -2, 1f))
        row.addView(button("Close") { finish() }); header.addView(row)
        if (route != null && index >= 0) header.addView(ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal).apply {
            max = route.steps.size; progress = index + 1; progressTintList = android.content.res.ColorStateList.valueOf(skin.accent); importantForAccessibility = View.IMPORTANT_FOR_ACCESSIBILITY_NO
        }, LinearLayout.LayoutParams(-1, dp(6)).apply { topMargin = dp(10) })
        val heading = words(content, if (mismatch) "My screen looks different" else step?.title ?: route?.title ?: if (group == null) "Choose your TV or app" else "Match your model or menu", 28f, bold = true).apply {
            if (Build.VERSION.SDK_INT >= 28) isAccessibilityHeading = true
            accessibilityLiveRegion = View.ACCESSIBILITY_LIVE_REGION_POLITE
        }
        when {
            mismatch -> mismatchContent(route)
            route != null && step != null -> {
                words(content, when (step.surface) { "tv" -> "On your TV · use the remote"; "both" -> "Your TV + your phone"; else -> "On your phone" }, 15f, skin.accent, true)
                content.addView(illustration(step, index + 1), LinearLayout.LayoutParams(-1, -2).apply { bottomMargin = dp(18) })
                words(content, step.instruction, 20f, bold = true)
                words(content, step.note, color = skin.muted)
                action(content, "My screen looks different") { mismatch = true; render() }
            }
            route != null -> intro(route)
            group != null -> {
                words(content, group!!.title, 20f, skin.accent, true)
                words(content, "Choose the setup screen or operating system you actually see. A brand alone does not confirm compatibility.", color = skin.muted)
                group!!.routes.forEach { id -> SetupContent.routes.firstOrNull { it.id == id }?.let { guide ->
                    action(content, guide.title) { routeId = id; index = -1; render() }
                } }
            }
            else -> {
                words(content, "Follow one picture at a time. The numbered arrow marks the next choice; TV, remote and phone symbols show which device to use.", color = skin.muted)
                SetupContent.groups.filter { it.id !in listOf("both", "neither") }.forEach { choice -> action(content, choice.title) { chooseGroup(choice.id) } }
            }
        }
        val footer = LinearLayout(this)
        if (group != null || route != null) footer.addView(button(if (mismatch) "Return to step" else "Back") { back() }, LinearLayout.LayoutParams(-2, -2).apply { marginEnd = dp(12) })
        if (route != null && !mismatch) footer.addView(button(if (index < 0) "Start guide" else if (index == route.steps.lastIndex) { if (route.id == "voice") "Open Voice check" else "Finish guide" } else "Next") {
            if (index == route.steps.lastIndex) {
                if (route.id == "voice" && !intent.getBooleanExtra("returnToVoice", false)) startActivity(Intent(this, InputAssistanceActivity::class.java).putExtra("mode", "voice").putExtra("dark", skin.dark))
                finish()
            } else { index++; render() }
        }, LinearLayout.LayoutParams(0, -2, 1f))
        controls.addView(footer)
        scroll.post { scroll.scrollTo(0, 0); heading.sendAccessibilityEvent(android.view.accessibility.AccessibilityEvent.TYPE_VIEW_FOCUSED) }
    }
    private fun intro(route: SetupRoute) {
        words(content, "Before you begin", 19f, bold = true)
        words(content, route.appliesTo)
        words(content, if (route.models.isEmpty()) "Menu-family guide. Your exact model is not confirmed by this preview." else "Documented model examples: ${route.models.joinToString()}", color = skin.muted)
        words(content, "${route.steps.size} pictures · one action at a time", 18f, skin.accent, true)
        words(content, "Pictures are simplified illustrations. Labels, layout and services can differ by country, software and language. Compare each picture with your own screen.", color = skin.muted)
        words(content, "Complete account approvals in the official app or on your TV. This guide never asks for a password and does not connect Audio Bodyguard.")
        sources(route)
        action(content, "My screen looks different") { mismatch = true; render() }
    }
    private fun sources(route: SetupRoute) {
        words(content, "Official instructions", 18f, bold = true)
        route.sources.forEach { id -> SetupContent.sources.firstOrNull { it.id == id }?.let { source ->
            action(content, source.title + " ↗") {
                try { startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(source.url))) }
                catch (_: android.content.ActivityNotFoundException) { AlertDialog.Builder(this).setTitle("Open official instructions").setMessage(source.url).setPositiveButton("Close", null).show() }
            }
        } }
    }
    private fun mismatchContent(route: SetupRoute?) {
        words(content, "Pause at this step. Check the full model, TV software and country. Look for the same menu meaning or icon in your language.")
        words(content, "If the option, TV or permission request is absent, use the manufacturer’s instructions below. Do not assume a successful pairing.")
        if (route != null) sources(route)
        action(content, "Choose another model or menu") { routeId = null; index = -1; mismatch = false; render() }
        action(content, "Choose another TV or app") { chooseGroup("") }
        words(content, "You can close this guide at any time. Your current place is preserved while viewing this help.", color = skin.muted)
    }
    private fun illustration(step: SetupStep, number: Int): View {
        val box = column().apply {
            setPadding(dp(14), dp(14), dp(14), dp(14)); background = skin.shape(skin.raised, 22)
            importantForAccessibility = View.IMPORTANT_FOR_ACCESSIBILITY_YES
            contentDescription = "Illustration $number. ${step.surface}: ${step.screen}. Highlighted: ${step.items[step.focus]}. Action: ${step.action}. ${step.instruction}"
        }
        words(box, "ILLUSTRATION", 11f, skin.muted, true).importantForAccessibility = View.IMPORTANT_FOR_ACCESSIBILITY_NO
        if (step.surface == "both") box.addView(SetupActionPicture(this, skin, "both", step.action), LinearLayout.LayoutParams(-1, dp(64)))
        val screen = column().apply { setPadding(dp(12), dp(12), dp(12), dp(12)); background = skin.shape(skin.surface, if (step.surface == "tv") 12 else 26, true); importantForAccessibility = View.IMPORTANT_FOR_ACCESSIBILITY_NO_HIDE_DESCENDANTS }
        box.addView(screen, LinearLayout.LayoutParams(-1, -2).apply { if (step.surface == "phone") { marginStart = dp(10); marginEnd = dp(10) } })
        if (step.surface != "tv") words(screen, "9:41                         ● ▰", 10f, skin.muted)
        words(screen, step.screen, 17f, bold = true)
        step.items.forEachIndexed { i, item ->
            val row = LinearLayout(this).apply {
                gravity = Gravity.CENTER_VERTICAL; setPadding(dp(10), dp(10), dp(10), dp(10)); minimumHeight = dp(48)
                background = skin.shape(if (i == step.focus) skin.control else skin.raised, 9, true)
            }
            val ink = if (i == step.focus) skin.controlText else skin.muted
            row.addView(TextView(this).apply { text = if (i == step.focus) number.toString() else "○"; textSize = 14f; setTypeface(null, Typeface.BOLD); setTextColor(ink); gravity = Gravity.CENTER }, LinearLayout.LayoutParams(dp(30), -2))
            row.addView(TextView(this).apply { text = item; textSize = 15f; setTextColor(ink); if (i == step.focus) setTypeface(null, Typeface.BOLD) }, LinearLayout.LayoutParams(0, -2, 1f))
            row.addView(TextView(this).apply { text = if (i == step.focus) "←" else "›"; textSize = 20f; setTextColor(ink) }, LinearLayout.LayoutParams(dp(22), -2))
            screen.addView(row, LinearLayout.LayoutParams(-1, -2).apply { bottomMargin = dp(8) })
        }
        if (step.surface == "tv") {
            box.addView(View(this).apply { setBackgroundColor(skin.outline) }, LinearLayout.LayoutParams(dp(14), dp(12)).apply { gravity = Gravity.CENTER })
            box.addView(View(this).apply { background = skin.shape(skin.outline, 4) }, LinearLayout.LayoutParams(dp(90), dp(4)).apply { gravity = Gravity.CENTER })
        } else screen.addView(View(this).apply { background = skin.shape(skin.muted, 4) }, LinearLayout.LayoutParams(dp(70), dp(4)).apply { gravity = Gravity.CENTER; topMargin = dp(8) })
        box.addView(SetupActionPicture(this, skin, step.surface, step.action), LinearLayout.LayoutParams(-1, dp(80)).apply { topMargin = dp(8) })
        return box
    }
    private fun back() {
        when {
            mismatch -> mismatch = false
            index >= 0 -> index--
            routeId != null -> routeId = null
            groupId.isNotEmpty() -> groupId = ""
            else -> { finish(); return }
        }
        render()
    }
    @Deprecated("Compatibility for Android 12 and earlier")
    override fun onBackPressed() { back() }
    override fun onSaveInstanceState(outState: Bundle) {
        outState.putString("group", groupId); outState.putString("route", routeId); outState.putInt("index", index); outState.putBoolean("mismatch", mismatch); super.onSaveInstanceState(outState)
    }
    override fun onDestroy() {
        if (Build.VERSION.SDK_INT >= 33) backCallback?.let { onBackInvokedDispatcher.unregisterOnBackInvokedCallback(it) }
        super.onDestroy()
    }
}

/** Pictograms show the physical device and gesture without depending on a language. */
private class SetupActionPicture(activity: Activity, private val skin: InterfaceTheme, private val surface: String, private val action: String) : View(activity) {
    private val paint = Paint(Paint.ANTI_ALIAS_FLAG)
    init { importantForAccessibility = IMPORTANT_FOR_ACCESSIBILITY_NO }
    override fun onDraw(c: Canvas) {
        super.onDraw(c)
        c.save(); val scale = minOf(width / 210f, height / 80f); c.translate((width - 210 * scale) / 2, (height - 80 * scale) / 2); c.scale(scale, scale)
        paint.color = skin.violet; paint.style = Paint.Style.STROKE; paint.strokeWidth = 2.5f; paint.strokeCap = Paint.Cap.ROUND
        if (surface == "both") {
            c.drawRoundRect(10f, 18f, 84f, 62f, 6f, 6f, paint); c.drawLine(47f, 62f, 47f, 70f, paint); c.drawLine(30f, 70f, 64f, 70f, paint)
        } else {
            c.drawRoundRect(29f, 4f, 70f, 76f, 12f, 12f, paint)
            if (surface == "tv") {
                c.drawCircle(49.5f, 47f, 15f, paint); c.drawCircle(49.5f, 47f, 5f, paint)
                c.drawLine(40f, 18f, 49f, 11f, paint); c.drawLine(49f, 11f, 58f, 18f, paint); c.drawLine(42f, 18f, 42f, 25f, paint); c.drawLine(56f, 18f, 56f, 25f, paint); c.drawLine(42f, 25f, 56f, 25f, paint)
            } else { c.drawLine(42f, 11f, 57f, 11f, paint); c.drawLine(43f, 68f, 56f, 68f, paint) }
        }
        c.drawLine(91f, 40f, 115f, 40f, paint); c.drawLine(108f, 33f, 115f, 40f, paint); c.drawLine(108f, 47f, 115f, 40f, paint)
        paint.style = Paint.Style.FILL; paint.color = skin.control; c.drawRoundRect(130f, 10f, 201f, 70f, 14f, 14f, paint)
        paint.style = Paint.Style.STROKE; paint.color = skin.controlText
        when {
            surface == "both" -> { c.drawRoundRect(153f, 17f, 179f, 63f, 5f, 5f, paint); c.drawLine(161f, 57f, 171f, 57f, paint) }
            action == "home" -> { val p = Path(); p.moveTo(148f, 38f); p.lineTo(165f, 23f); p.lineTo(182f, 38f); p.moveTo(152f, 35f); p.lineTo(152f, 56f); p.lineTo(178f, 56f); p.lineTo(178f, 35f); c.drawPath(p, paint) }
            action == "settings" -> { c.drawCircle(165f, 40f, 12f, paint); c.drawCircle(165f, 40f, 4f, paint); for (i in 0..7) { c.save(); c.rotate(i * 45f, 165f, 40f); c.drawLine(165f, 24f, 165f, 28f, paint); c.restore() } }
            action == "type" -> { c.drawRoundRect(144f, 26f, 187f, 54f, 4f, 4f, paint); for (y in listOf(33f, 41f)) for (x in listOf(151f, 160f, 169f, 178f)) c.drawPoint(x, y, paint); c.drawLine(154f, 48f, 177f, 48f, paint) }
            action == "scan" -> { for ((x,y) in listOf(147f to 23f, 184f to 23f, 147f to 57f, 184f to 57f)) { c.drawLine(x, y, x + if (x < 160) 8f else -8f, y, paint); c.drawLine(x,y,x,y + if (y < 40) 8f else -8f, paint) }; c.drawCircle(165f, 40f, 8f, paint) }
            action == "speak" -> { c.drawRoundRect(160f, 23f, 171f, 44f, 5f, 5f, paint); c.drawArc(153f, 26f, 178f, 51f, 0f, 180f, false, paint); c.drawLine(165f, 51f, 165f, 59f, paint) }
            action == "stop" -> { paint.style = Paint.Style.FILL; c.drawRoundRect(153f, 28f, 178f, 53f, 3f, 3f, paint) }
            action == "check" -> { c.drawOval(145f, 29f, 187f, 51f, paint); c.drawCircle(166f, 40f, 6f, paint) }
            else -> { c.drawCircle(165f, 30f, 9f, paint); val p = Path(); p.moveTo(157f, 58f); p.lineTo(154f, 42f); p.lineTo(161f, 46f); p.lineTo(161f, 30f); p.quadTo(165f, 25f, 169f, 30f); p.lineTo(169f, 41f); p.lineTo(178f, 43f); p.lineTo(176f, 58f); c.drawPath(p, paint) }
        }
        c.restore()
    }
}
