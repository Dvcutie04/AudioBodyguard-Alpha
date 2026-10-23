package com.aqss.bodyguard.prototype

import android.Manifest
import android.app.Activity
import android.app.AlertDialog
import android.content.Intent
import android.content.pm.PackageManager
import android.content.res.Configuration
import android.graphics.Canvas
import android.graphics.Paint
import android.net.Uri
import android.os.*
import android.provider.Settings
import android.view.View
import android.view.WindowInsets
import android.widget.*
import com.aqss.nativefeedback.SoundCheckWindow
import com.aqss.nativefeedback.SoundCheckEnd
import com.aqss.nativefeedback.SoundCheckRecaps
import com.aqss.nativefeedback.PrivateSupportReportSnapshot
import java.util.Locale

/** Real microphone input display; no output actuation or protective-state authority. */
class LiveSoundCheckActivity : Activity() {
    private lateinit var skin: InterfaceTheme
    private lateinit var status: TextView
    private lateinit var level: TextView
    private lateinit var details: TextView
    private lateinit var start: Button
    private lateinit var meter: LiveInputMeter
    private lateinit var recent: Button
    private lateinit var permissionSettings: Button
    private val handler = Handler(Looper.getMainLooper())
    private val window = SoundCheckWindow()
    private var capture: MicrophoneCapture? = null
    private var run = 0L
    private var lastSample = 0L
    private var visible = false
    private var stopping = false
    private var permissionGuidance = false
    private val permissionDeniedMessage = "Microphone permission denied. In app settings, choose Permissions, then Microphone."

    override fun onCreate(savedInstanceState: Bundle?) {
        val dark = intent.getBooleanExtra("dark", true)
        setTheme(if (dark) R.style.AQSSMidnightTheme else R.style.AQSSReadOnlyTheme)
        super.onCreate(savedInstanceState)
        skin = InterfaceTheme(this, dark)
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(skin.dp(16), skin.dp(28), skin.dp(16), skin.dp(16))
            setBackgroundColor(skin.background)
        }
        val header = LinearLayout(this)
        header.addView(TextView(this).apply { text = "Live sound check"; textSize = 24f; setTextColor(skin.text) }, LinearLayout.LayoutParams(0, -2, 1f))
        header.addView(Button(this).apply { text = "Back"; skin.style(this); setOnClickListener { finish() } })
        root.addView(header)
        val column = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        fun text(value: String, size: Float = 17f) = TextView(this).apply {
            this.text = value; textSize = size; setTextColor(skin.text)
            setPadding(0, skin.dp(12), 0, skin.dp(12)); column.addView(this)
        }
        text("Try a 30-second microphone check. Speak normally and watch the bars respond.")
        status = text("Microphone off", 21f)
        permissionSettings = Button(this).apply {
            this.text = "Open app settings"; skin.style(this); visibility = View.GONE
            setOnClickListener { openPermissionSettings() }
        }
        column.addView(permissionSettings, LinearLayout.LayoutParams(-1, -2))
        meter = LiveInputMeter(this, skin)
        val meterHeight = if (resources.configuration.orientation == Configuration.ORIENTATION_LANDSCAPE) 84 else 135
        column.addView(meter, LinearLayout.LayoutParams(-1, skin.dp(meterHeight)))
        level = text("No live input", 22f)
        text("Relative microphone input · not calibrated room loudness", 15f).setTextColor(skin.muted)
        column.addView(Button(this).apply {
            this.text = "[?] What does this show?"; skin.style(this)
            setOnClickListener {
                stopCapture(SoundCheckEnd.HELP_OPENED, "Microphone stopped while help is open.")
                AlertDialog.Builder(this@LiveSoundCheckActivity).setTitle("About the sound check")
                    .setMessage("The bars use real microphone samples from this phone. dBFS describes digital input relative to the microphone’s maximum sample value. It is not dBA or a hearing-safety measurement. Phone gain, processing, position and input route change the result.\n\nZero input can mean a quiet signal or blocked input. This check cannot decide whether sound is safe.\n\nListening stops after 30 seconds or when you leave this screen. No audio files are saved or uploaded. Automatic audio protection and TV controls are still unavailable.")
                    .setPositiveButton("Close", null).show()
            }
        })
        details = text("${Build.MANUFACTURER} ${Build.MODEL} · Android ${Build.VERSION.RELEASE}\nInput details appear while the check runs.", 15f).apply { visibility = View.GONE }
        column.addView(Button(this).apply {
            this.text = "Show input details"; skin.style(this)
            setOnClickListener {
                details.visibility = if (details.visibility == View.GONE) View.VISIBLE else View.GONE
                this.text = if (details.visibility == View.VISIBLE) "Hide input details" else "Show input details"
            }
        })
        recent = Button(this).apply {
            this.text = "Recent sound checks"; skin.style(this)
            setOnClickListener { showRecaps() }
        }
        column.addView(recent)
        text("Automatic protection is not active.", 16f).setTextColor(skin.warning)
        root.addView(ScrollView(this).apply { addView(column) }, LinearLayout.LayoutParams(-1, 0, 1f))
        start = Button(this).apply {
            text = "Start sound check"; skin.style(this, primary = true)
            setOnClickListener { if (capture == null) startCapture() else stopCapture(SoundCheckEnd.STOPPED_BY_USER, "Microphone stopped") }
        }
        root.addView(start, LinearLayout.LayoutParams(-1, -2))
        setContentView(root)
        root.setOnApplyWindowInsetsListener { view, insets ->
            if (Build.VERSION.SDK_INT >= 30) {
                val bars = insets.getInsets(WindowInsets.Type.systemBars())
                view.setPadding(skin.dp(16) + bars.left, skin.dp(12) + bars.top, skin.dp(16) + bars.right, skin.dp(12) + bars.bottom)
            }
            insets
        }
    }

    override fun onResume() {
        super.onResume(); visible = true
        if (permissionGuidance) refreshPermissionGuidance()
        if (capture != null) handler.post(tick)
    }

    private fun refreshPermissionGuidance() {
        val granted = checkSelfPermission(Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED
        permissionSettings.visibility = if (permissionGuidance && !granted && capture == null) View.VISIBLE else View.GONE
        if (!permissionGuidance || capture != null) return
        status.text = if (granted) "Permission granted. Tap Start when you are ready." else permissionDeniedMessage
    }

    private fun openPermissionSettings() {
        if (!permissionGuidance || !visible || !hasWindowFocus() || isFinishing || isDestroyed || capture != null) return
        if (checkSelfPermission(Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED) {
            refreshPermissionGuidance(); return
        }
        stopCapture(SoundCheckEnd.LEFT_SCREEN, "Microphone off")
        try {
            startActivity(Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS, Uri.fromParts("package", packageName, null)))
        } catch (_: RuntimeException) {
            status.text = "App settings could not open. In Android Settings, choose Apps, ${getString(R.string.app_name)}, then Permissions."
        }
    }

    private fun startCapture() {
        if (!visible || !hasWindowFocus() || capture != null) return
        if (checkSelfPermission(Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
            permissionGuidance = true
            requestPermissions(arrayOf(Manifest.permission.RECORD_AUDIO), 73); return
        }
        permissionGuidance = false; permissionSettings.visibility = View.GONE
        val now = SystemClock.elapsedRealtime()
        val token = window.start(now) ?: run {
            status.text = "Sound check could not start. Close and reopen the app before trying again."
            return
        }
        run = token; lastSample = now; stopping = false
        recent.isEnabled = false
        meter.clear(); level.text = "Waiting for microphone input"
        status.text = "Starting microphone…"
        capture = MicrophoneCapture(this).also { it.start() }
        start.text = "Stop sound check"; start.isEnabled = true
        handler.removeCallbacks(tick); handler.post(tick)
    }

    private fun stopCapture(reason: SoundCheckEnd, message: String) {
        window.stop(); meter.clear(); level.text = "No live input"
        capture?.let {
            stopping = true; it.stop(reason, message); status.text = "Stopping microphone…"
            start.isEnabled = false
        } ?: run { status.text = message }
    }

    private val tick = object : Runnable {
        override fun run() {
            if (!visible) return
            val source = capture ?: return
            val now = SystemClock.elapsedRealtime()
            if (source.completed.get()) {
                window.stop(); if (!source.cleanupFailed) capture = null; stopping = false
                meter.clear(); level.text = "No live input"; status.text = source.stopReason
                start.text = "Start sound check"; start.isEnabled = !source.cleanupFailed
                recent.isEnabled = true
                return
            }
            if (!stopping) {
                source.takeLatest()?.let { frame ->
                    if (window.offer(run, frame.receivedAtMs, now, frame.level)) {
                        lastSample = frame.receivedAtMs
                        source.noteDisplayedInput()
                        meter.add(frame.level.rmsDbfs?.let { ((it + 60.0) / 60.0).toFloat().coerceIn(0f, 1f) } ?: 0f)
                    }
                }
                val current = window.current(now)
                if (!window.active) {
                    if (window.endReason == SoundCheckWindow.EndReason.timeLimit)
                        stopCapture(SoundCheckEnd.TIME_LIMIT, "30-second check finished. Tap Start for another check.")
                    else stopCapture(SoundCheckEnd.INVALID_INPUT, "Input clock changed. Tap Start for a new sound check.")
                } else {
                    if (current == null) {
                        meter.clear(); show(level, "No current input samples")
                        show(status, "Waiting for microphone input…")
                        if (now - lastSample >= 3000) stopCapture(SoundCheckEnd.NO_SAMPLES, "No current microphone input. Check microphone privacy, then tap Start to retry.")
                    } else {
                        show(status, "Microphone samples received · up to 30 seconds")
                        val value = current.rmsDbfs?.let { String.format(Locale.US, "%.1f dBFS", it) }
                            ?: "No input signal · quiet or blocked"
                        show(level, value + if (current.fullScaleSamples > 0) "\nInput reached digital full scale" else "")
                    }
                    show(details, "${Build.MANUFACTURER} ${Build.MODEL} · Android ${Build.VERSION.RELEASE}\n${source.description}")
                }
            }
            handler.postDelayed(this, 100)
        }
    }

    private fun showRecaps() {
        if (capture?.completed?.get() == false) return
        showRecentSoundChecks(this, skin)
    }

    private fun show(view: TextView, value: String) {
        // Identical input must not generate a stream of accessibility text-change events.
        if (view.text.toString() != value) view.text = value
    }

    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<out String>, grantResults: IntArray) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == 73 && !isFinishing && !isDestroyed && capture == null) {
            permissionGuidance = true; refreshPermissionGuidance()
        }
    }

    override fun onWindowFocusChanged(hasFocus: Boolean) {
        super.onWindowFocusChanged(hasFocus)
        if (!hasFocus && capture != null) stopCapture(SoundCheckEnd.LEFT_SCREEN, "Microphone stopped when you left the sound check.")
    }

    override fun onPause() {
        visible = false; handler.removeCallbacks(tick)
        stopCapture(SoundCheckEnd.LEFT_SCREEN, "Microphone stopped when you left the sound check.")
        super.onPause()
    }

    override fun onDestroy() {
        handler.removeCallbacksAndMessages(null)
        capture?.stop(SoundCheckEnd.CLOSED, "Sound check closed")
        super.onDestroy()
    }
}

/** A bounded history of digital RMS summaries, cleared as soon as samples become stale. */
private class LiveInputMeter(activity: Activity, private val skin: InterfaceTheme) : View(activity) {
    private val values = FloatArray(60)
    private var count = 0
    private var next = 0
    private val paint = Paint(Paint.ANTI_ALIAS_FLAG)
    init { importantForAccessibility = IMPORTANT_FOR_ACCESSIBILITY_NO }
    fun clear() { values.fill(0f); count = 0; next = 0; invalidate() }
    fun add(value: Float) { values[next] = value; next = (next + 1) % values.size; count = minOf(count + 1, values.size); invalidate() }
    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        paint.color = skin.raised; canvas.drawRoundRect(0f, 0f, width.toFloat(), height.toFloat(), 16f, 16f, paint)
        paint.color = skin.accent
        val gap = width.toFloat() / values.size
        for (i in 0 until count) {
            val index = (next - count + i + values.size) % values.size
            val left = (values.size - count + i) * gap
            val barHeight = maxOf(skin.dp(2).toFloat(), values[index] * (height - skin.dp(16)))
            canvas.drawRect(left, height - skin.dp(8) - barHeight, left + gap * .72f, height - skin.dp(8).toFloat(), paint)
        }
    }
}

/** Shared process-only recap presentation; opening it performs no capture work. */
internal fun showRecentSoundChecks(activity: Activity, skin: InterfaceTheme) {
    val store = SoundCheckRecaps.process
    val rows = store.snapshot()
    val content = LinearLayout(activity).apply {
        orientation = LinearLayout.VERTICAL
        setPadding(skin.dp(24), skin.dp(8), skin.dp(24), skin.dp(8))
    }
    fun line(value: String, heading: Boolean = false) {
        content.addView(TextView(activity).apply {
            text = value; textSize = if (heading) 18f else 16f
            setTextColor(skin.text); setPadding(0, skin.dp(8), 0, skin.dp(8))
        })
    }
    line("Up to five completed checks, most recent first. Kept in memory; cleared when this app process ends.")
    if (rows.isEmpty()) line("No completed sound checks in this app session.")
    rows.forEachIndexed { index, row ->
        line("Check ${index + 1} · ${if (row.inputObserved) "Input samples observed" else "No input samples observed"}", true)
        line(row.end.label)
    }
    line("These are meter observations from this phone, not proof of continuous listening, sound safety or TV control. Audio and recognized words are not kept in recaps.")
    content.addView(Button(activity).apply {
        text = "Review support report"; skin.style(this)
        setOnClickListener {
            showPrivateSupportReport(activity, skin, PrivateSupportReportSnapshot(installedAppBuildDetails(activity), rows))
        }
    }, LinearLayout.LayoutParams(-1, -2))
    val dialog = AlertDialog.Builder(activity).setTitle("Recent sound checks")
        .setView(ScrollView(activity).apply { addView(content) })
        .setPositiveButton("Close", null)
    if (rows.isNotEmpty()) dialog.setNeutralButton("Clear recaps") { _, _ ->
        store.clear(); showRecentSoundChecks(activity, skin)
    }
    dialog.show()
}
