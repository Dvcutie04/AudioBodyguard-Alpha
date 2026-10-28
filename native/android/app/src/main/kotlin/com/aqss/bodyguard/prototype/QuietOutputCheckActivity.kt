package com.aqss.bodyguard.prototype

import android.app.Activity
import android.app.AlertDialog
import android.content.ActivityNotFoundException
import android.content.Intent
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.WindowInsets
import android.widget.*
import com.aqss.nativefeedback.*

/** Explicit, zero-source diagnostic; never controls TV audio or protection. */
class QuietOutputCheckActivity : Activity() {
    private lateinit var skin: InterfaceTheme
    private lateinit var status: TextView
    private lateinit var start: Button
    private lateinit var review: Button
    private val handler = Handler(Looper.getMainLooper())
    private var visible = false
    private var stopping = false
    private var capture: QuietOutputCapture? = null
    private var lastResult: QuietOutputResult? = null
    private var lastReport: QuietOutputReportSnapshot? = null
    private var reportDialog: AlertDialog? = null
    private var watchdog: Runnable? = null
    private data class State(val capture: QuietOutputCapture?, val result: QuietOutputResult?, val report: QuietOutputReportSnapshot?)
    private val liveBuild: Boolean get() = packageName == "com.aqss.bodyguard.prototype.liveinput"

    override fun onCreate(savedInstanceState: Bundle?) {
        val dark = intent.getBooleanExtra("dark", true)
        setTheme(if (dark) R.style.AQSSMidnightTheme else R.style.AQSSReadOnlyTheme)
        super.onCreate(savedInstanceState)
        skin = InterfaceTheme(this, dark)
        (lastNonConfigurationInstance as? State)?.let { capture = it.capture; lastResult = it.result; lastReport = it.report }
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL; setBackgroundColor(skin.background)
            setPadding(skin.dp(16), skin.dp(28), skin.dp(16), skin.dp(16))
        }
        val header = LinearLayout(this)
        header.addView(TextView(this).apply { text = "Quiet output check"; textSize = 23f; setTextColor(skin.text) }, LinearLayout.LayoutParams(0, -2, 1f))
        header.addView(Button(this).apply { text = "Back"; skin.style(this); setOnClickListener { finish() } })
        root.addView(header)
        val column = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        fun words(value: String, size: Float = 17f) = TextView(this).apply {
            text = value; textSize = size; setTextColor(skin.text)
            setPadding(0, skin.dp(12), 0, skin.dp(12)); column.addView(this)
        }
        words("Try this phone's playback connection with a brief quiet check.")
        words("May pause other audio. No microphone is used.", 15f)
        status = words(if (liveBuild) "Ready for a quiet check" else "Available in the Live Test build", 20f)
        column.addView(Button(this).apply {
            text = "[?] About this check"; skin.style(this)
            setOnClickListener {
                stopCheck(QuietStop.USER)
                AlertDialog.Builder(this@QuietOutputCheckActivity).setTitle("About the quiet check")
                    .setMessage("This opens one app-owned playback stream with zero-valued samples and zero app gain. It does not change the phone's volume setting. Android may pause other audio while it runs.\n\nStop, leaving this screen or an interruption closes new work. A delayed Android call may take longer to finish closing. The check never restarts automatically.\n\nThe report shows what Android returned. It does not verify audible output, silence, hearing safety, TV controls or automatic protection. No recording is made or uploaded.")
                    .setPositiveButton("Close", null).show()
            }
        })
        review = Button(this).apply {
            text = "Review check report"; skin.style(this); isEnabled = lastResult != null
            setOnClickListener { showReport() }
        }
        column.addView(review, LinearLayout.LayoutParams(-1, -2))
        words("Sound and automatic protection are not verified.", 15f).setTextColor(skin.warning)
        root.addView(ScrollView(this).apply { addView(column) }, LinearLayout.LayoutParams(-1, 0, 1f))
        start = Button(this).apply {
            text = "Start quiet check"; skin.style(this, primary = true); isEnabled = liveBuild
            setOnClickListener {
                if (capture?.completed?.get() == false) stopCheck(QuietStop.USER) else beginCheck()
            }
        }
        root.addView(start, LinearLayout.LayoutParams(-1, -2))
        setContentView(root)
        root.setOnApplyWindowInsetsListener { view, insets ->
            if (Build.VERSION.SDK_INT >= 30) {
                val bars = insets.getInsets(WindowInsets.Type.systemBars())
                view.setPadding(skin.dp(16) + bars.left, skin.dp(12) + bars.top,
                    skin.dp(16) + bars.right, skin.dp(12) + bars.bottom)
            }; insets
        }
    }

    private fun beginCheck() {
        if (!liveBuild || !visible || !hasWindowFocus() || isFinishing || isDestroyed || capture?.completed?.get() == false) return
        lastResult = null; lastReport = null; stopping = false; review.isEnabled = false
        val current = QuietOutputCapture(this)
        capture = current; status.text = "Starting quiet check…"
        start.text = "Stop quiet check"; start.isEnabled = true
        current.start(); handler.removeCallbacks(tick); handler.post(tick)
        watchdog?.let { handler.removeCallbacks(it) }
        val deadline = Runnable { if (capture === current) stopCheck(QuietStop.TIME_LIMIT) }
        watchdog = deadline; handler.postDelayed(deadline, QuietOutputCheck.BUDGET_MS)
    }

    private fun stopCheck(reason: QuietStop) {
        val current = capture ?: return
        if (current.completed.get()) return
        current.stop(reason); stopping = true
        if (::status.isInitialized) status.text = "Closing quiet check…"
        if (::start.isInitialized) start.isEnabled = false
    }

    private val tick = object : Runnable {
        override fun run() {
            if (!visible) return
            val current = capture ?: return
            if (current.completed.get()) {
                watchdog?.let { handler.removeCallbacks(it) }; watchdog = null
                lastResult = current.result; stopping = false
                val result = lastResult
                status.text = when {
                    result?.quarantined == true || result?.cleanupSucceeded == false || ForegroundAudioExclusion.process.blocked ->
                        "Audio cleanup is unresolved. Force stop this app in Android Settings before trying again."
                    result == null -> "The check could not start. Tap Start to try again."
                    result.reason == QuietStop.COMPLETE -> "Quiet check ended. Review the report for Android's observations."
                    result.reason == QuietStop.BUSY -> "Another audio tool is running or closing. Stop it, then tap Start."
                    result.reason == QuietStop.FOCUS_DENIED -> "Audio focus was not granted. Tap Start to try again."
                    result.reason == QuietStop.UNSUPPORTED -> "This check is unavailable on this configuration."
                    result.reason == QuietStop.ROUTE_CHANGED -> "Check stopped after an output-change notice."
                    result.reason == QuietStop.TIME_LIMIT -> "Check stopped after its time budget expired."
                    result.reason == QuietStop.INACTIVE -> "Check stopped when you left the screen."
                    else -> "Check stopped. Review the report for details."
                }
                start.text = "Start quiet check"
                start.isEnabled = liveBuild && !ForegroundAudioExclusion.process.blocked && result?.cleanupSucceeded != false
                review.isEnabled = result != null
                return
            }
            if (!stopping) status.text = "Quiet check is running…"
            handler.postDelayed(this, 50)
        }
    }

    private fun showReport() {
        val result = lastResult ?: return
        if (!visible || !hasWindowFocus() || isFinishing || isDestroyed || capture?.completed?.get() == false || reportDialog?.isShowing == true) return
        val report = lastReport ?: try {
            QuietOutputReportSnapshot.capture(installedAppBuildDetails(this), result, System.currentTimeMillis()).also { lastReport = it }
        } catch (_: RuntimeException) { status.text = "Report unavailable for this check."; return }
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL; setBackgroundColor(skin.background)
            setPadding(skin.dp(16), skin.dp(12), skin.dp(16), skin.dp(12))
        }
        val header = LinearLayout(this)
        header.addView(TextView(this).apply { text = "Review check report"; textSize = 21f; setTextColor(skin.text) }, LinearLayout.LayoutParams(0, -2, 1f))
        val share = Button(this).apply { text = "Share check report"; skin.style(this, primary = true) }
        val dialog = object : AlertDialog(this) {
            override fun onWindowFocusChanged(hasFocus: Boolean) {
                super.onWindowFocusChanged(hasFocus)
                if (hasFocus && visible && isShowing) share.isEnabled = true
            }
        }
        header.addView(roseButton(this, skin, "Back", compact = true) { dialog.dismiss() })
        root.addView(header)
        val preview = TextView(this).apply {
            text = report.text; textSize = 15f; setTextColor(skin.text); setTextIsSelectable(true)
            tag = "quiet-output-report-preview"; setPadding(0, skin.dp(12), 0, skin.dp(12))
        }
        root.addView(ScrollView(this).apply { addView(preview) }, LinearLayout.LayoutParams(-1, 0, 1f))
        root.addView(TextView(this).apply {
            text = QuietOutputReportSnapshot.NOTICE; textSize = 14f; setTextColor(skin.text)
            setPadding(0, skin.dp(8), 0, skin.dp(8))
        })
        root.addView(share, LinearLayout.LayoutParams(-1, -2))
        dialog.setView(root); dialog.setOnDismissListener { if (reportDialog === dialog) reportDialog = null }
        share.setOnClickListener {
            if (!visible || isFinishing || isDestroyed || !dialog.isShowing ||
                dialog.window?.decorView?.hasWindowFocus() != true || !share.isEnabled) return@setOnClickListener
            share.isEnabled = false
            try {
                startActivity(Intent.createChooser(Intent(Intent.ACTION_SEND).apply {
                    type = "text/plain"; putExtra(Intent.EXTRA_TEXT, report.text)
                }, null))
                handler.post { if (visible && dialog.isShowing && dialog.window?.decorView?.hasWindowFocus() == true) share.isEnabled = true }
            } catch (error: RuntimeException) {
                share.isEnabled = true
                if (error !is ActivityNotFoundException && error !is SecurityException) throw error
                Toast.makeText(this, "Sharing is unavailable. You can read the report shown here.", Toast.LENGTH_LONG).show()
            }
        }
        reportDialog = dialog; dialog.show()
        val display = resources.displayMetrics
        dialog.window?.setLayout(minOf(display.widthPixels - skin.dp(24), skin.dp(680)), (display.heightPixels * .85f).toInt())
    }

    override fun onRetainNonConfigurationInstance(): Any = State(capture, lastResult, lastReport)
    override fun onResume() {
        super.onResume(); visible = true
        capture?.setForeground(hasWindowFocus())
        if (capture != null) handler.post(tick)
    }
    override fun onWindowFocusChanged(hasFocus: Boolean) {
        super.onWindowFocusChanged(hasFocus)
        capture?.setForeground(hasFocus && visible)
        if (!hasFocus) stopCheck(QuietStop.INACTIVE)
    }
    override fun onPause() {
        visible = false; capture?.setForeground(false); stopCheck(QuietStop.INACTIVE)
        handler.removeCallbacks(tick); watchdog?.let { handler.removeCallbacks(it) }; watchdog = null
        super.onPause()
    }
    override fun onDestroy() {
        capture?.setForeground(false); stopCheck(QuietStop.INACTIVE)
        handler.removeCallbacks(tick); watchdog?.let { handler.removeCallbacks(it) }; watchdog = null
        reportDialog?.dismiss(); reportDialog = null
        super.onDestroy()
    }
}
