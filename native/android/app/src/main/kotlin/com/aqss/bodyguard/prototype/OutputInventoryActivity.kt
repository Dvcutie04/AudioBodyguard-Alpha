package com.aqss.bodyguard.prototype

import android.app.Activity
import android.app.AlertDialog
import android.content.ActivityNotFoundException
import android.content.Intent
import android.media.AudioDeviceCallback
import android.media.AudioDeviceInfo
import android.media.AudioFormat
import android.media.AudioManager
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.WindowInsets
import android.widget.Button
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import android.widget.Toast
import com.aqss.nativefeedback.OutputDeviceAdvertisement
import com.aqss.nativefeedback.OutputDeviceInventory
import com.aqss.nativefeedback.OutputInventoryReportSnapshot
import java.lang.ref.WeakReference

/** Available OS metadata only. Never opens a stream or requests audio focus. */
class OutputInventoryActivity : Activity() {
    private lateinit var skin: InterfaceTheme
    private lateinit var results: TextView
    private lateinit var reviewButton: Button
    private var visible = false
    private var hasSnapshot = false
    private var reportSnapshot: OutputInventoryReportSnapshot? = null
    private var reportDialog: AlertDialog? = null
    private var reportShareButton: Button? = null
    private var reportNotesButton: Button? = null
    private var deviceCallback: AudioDeviceCallback? = null
    private var callbackManager: AudioManager? = null

    private class DeviceChanges(owner: OutputInventoryActivity) : AudioDeviceCallback() {
        private val owner = WeakReference(owner)
        override fun onAudioDevicesAdded(addedDevices: Array<out AudioDeviceInfo>) {
            owner.get()?.invalidateOutputs(this, addedDevices)
        }
        override fun onAudioDevicesRemoved(removedDevices: Array<out AudioDeviceInfo>) {
            owner.get()?.invalidateOutputs(this, removedDevices)
        }
    }

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
        header.addView(TextView(this).apply {
            text = "Output inventory"; textSize = 24f; setTextColor(skin.text)
        }, LinearLayout.LayoutParams(0, -2, 1f))
        header.addView(Button(this).apply {
            text = "Back"; skin.style(this); setOnClickListener { finish() }
        })
        root.addView(header)
        val column = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        fun words(value: String, size: Float = 17f): TextView = TextView(this).apply {
            text = value; textSize = size; setTextColor(skin.text)
            setPadding(0, skin.dp(10), 0, skin.dp(10)); column.addView(this)
        }
        words("Check the audio outputs Android currently lists for this phone.")
        words("${OutputInventoryReportSnapshot.phoneText(Build.MANUFACTURER)} ${OutputInventoryReportSnapshot.phoneText(Build.MODEL)}\nAndroid ${OutputInventoryReportSnapshot.phoneText(Build.VERSION.RELEASE)} · API ${Build.VERSION.SDK_INT}", 15f)
        words("Selected playback route: Unknown\nNegotiated format: Unknown", 18f)
        words("Available outputs can change. Listed capabilities do not identify an active route or prove a working connection.", 15f)
        results = words(IDLE, 16f)
        words("This screen plays no sound and uses no microphone. The live list clears when you leave. You can review a snapshot before sharing it.", 15f)
        root.addView(ScrollView(this).apply { addView(column) }, LinearLayout.LayoutParams(-1, 0, 1f))
        reviewButton = Button(this).apply {
            text = "Review output report"; skin.style(this); isEnabled = false
            setOnClickListener { showReport() }
        }
        root.addView(reviewButton, LinearLayout.LayoutParams(-1, -2))
        root.addView(Button(this).apply {
            text = "Refresh outputs"; skin.style(this, primary = true)
            setOnClickListener { refreshOutputs() }
        }, LinearLayout.LayoutParams(-1, -2))
        if (packageName == "com.aqss.bodyguard.prototype.liveinput") root.addView(Button(this).apply {
            text = "Quiet output check"; skin.style(this)
            setOnClickListener {
                if (visible && hasWindowFocus() && !isFinishing && !isDestroyed)
                    startActivity(Intent(this@OutputInventoryActivity, QuietOutputCheckActivity::class.java).putExtra("dark", skin.dark))
            }
        }, LinearLayout.LayoutParams(-1, -2))
        setContentView(root)
        root.setOnApplyWindowInsetsListener { view, insets ->
            if (Build.VERSION.SDK_INT >= 30) {
                val bars = insets.getInsets(WindowInsets.Type.systemBars())
                view.setPadding(skin.dp(16) + bars.left, skin.dp(12) + bars.top,
                    skin.dp(16) + bars.right, skin.dp(12) + bars.bottom)
            }
            insets
        }
    }

    override fun onResume() {
        super.onResume(); visible = true
        clearSnapshot(IDLE)
        registerNotices()
        if (reportDialog?.isShowing == true) { reportShareButton?.isEnabled = true; reportNotesButton?.isEnabled = true }
    }

    override fun onPause() {
        visible = false; clearSnapshot(IDLE)
        unregisterNotices()
        super.onPause()
    }

    override fun onDestroy() {
        visible = false
        reportDialog?.dismiss()
        unregisterNotices()
        super.onDestroy()
    }

    private fun registerNotices() {
        val manager = try { getSystemService(AUDIO_SERVICE) as? AudioManager }
            catch (_: RuntimeException) { null } ?: return
        val callback = DeviceChanges(this)
        try {
            manager.registerAudioDeviceCallback(callback, Handler(Looper.getMainLooper()))
            callbackManager = manager; deviceCallback = callback
        } catch (_: RuntimeException) {
            // A partially registered observer must never gain UI authority.
            runCatching { manager.unregisterAudioDeviceCallback(callback) }
        }
    }

    private fun unregisterNotices() {
        val callback = deviceCallback
        val manager = callbackManager
        // Retire before cleanup: an already queued notice may still arrive.
        deviceCallback = null; callbackManager = null
        if (callback != null && manager != null) {
            runCatching { manager.unregisterAudioDeviceCallback(callback) }
        }
    }

    private fun invalidateOutputs(source: AudioDeviceCallback, devices: Array<out AudioDeviceInfo>) {
        if (!visible || deviceCallback !== source || !hasSnapshot || isFinishing || isDestroyed) return
        // Oversized notices invalidate conservatively without scanning an
        // unbounded list. No descriptor, name, address or ID is retained.
        if (devices.size <= OutputDeviceInventory.MAX_DEVICES && devices.none { it.isSink }) return
        clearSnapshot("Output list needs a fresh check. Tap Refresh outputs.")
    }

    private fun clearSnapshot(message: String) {
        hasSnapshot = false; reportSnapshot = null; results.text = message
        reviewButton.isEnabled = false
    }

    private fun refreshOutputs() {
        if (!visible || !hasWindowFocus() || isFinishing || isDestroyed) return
        clearSnapshot(IDLE)
        results.text = try {
            val manager = getSystemService(AUDIO_SERVICE) as? AudioManager
                ?: throw IllegalStateException("Audio service unavailable")
            val devices = manager.getDevices(AudioManager.GET_DEVICES_OUTPUTS)
            val rows = devices.take(16).map { device ->
                OutputDeviceAdvertisement(
                    kind = outputKind(device.type),
                    sampleRates = device.sampleRates.asList(),
                    channelCounts = device.channelCounts.asList(),
                    encodings = device.encodings.let { values ->
                        object : AbstractList<String>() {
                            override val size: Int get() = values.size
                            override fun get(index: Int): String = encodingName(values[index])
                        }
                    },
                )
            }
            val inventory = OutputDeviceInventory.from(rows, devices.size)
            reportSnapshot = try {
                OutputInventoryReportSnapshot.capture(installedAppBuildDetails(this),
                    Build.MANUFACTURER, Build.MODEL, Build.VERSION.RELEASE, Build.VERSION.SDK_INT,
                    System.currentTimeMillis(), deviceCallback != null, inventory)
            } catch (_: RuntimeException) { null }
            buildString {
                append(inventory.summaryText)
                inventory.devices.forEachIndexed { index, device ->
                    append("\n\n${index + 1}. ${device.kind}")
                    append("\nAdvertised sample rates: ${device.sampleRatesText}")
                    append("\nAdvertised channel counts: ${device.channelCountsText}")
                    append("\nAdvertised encodings: ${device.encodingsText}")
                }
                if (deviceCallback == null) append("\n\nAutomatic change notices unavailable.")
                if (reportSnapshot == null) append("\n\nReport unavailable for this snapshot.")
                append("\n\nSnapshot only. Tap Refresh outputs to read again.")
            }.also { hasSnapshot = true; reviewButton.isEnabled = reportSnapshot != null }
        } catch (_: RuntimeException) {
            "Output inventory unavailable. Tap Refresh outputs to try again.\nNo output route has been verified."
        }
    }

    /** A historical copy remains immutable through notices and native sharing.
     * It is never substituted for the live list or restored after recreation. */
    private fun showReport() {
        val report = reportSnapshot ?: return
        if (!visible || !hasSnapshot || !hasWindowFocus() || isFinishing || isDestroyed || reportDialog?.isShowing == true) return
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(skin.dp(16), skin.dp(12), skin.dp(16), skin.dp(12))
            setBackgroundColor(skin.background)
        }
        val header = LinearLayout(this).apply { gravity = android.view.Gravity.CENTER_VERTICAL }
        header.addView(TextView(this).apply {
            text = "Review output report"; textSize = 22f; setTextColor(skin.text)
            setTypeface(typeface, android.graphics.Typeface.BOLD)
        }, LinearLayout.LayoutParams(0, -2, 1f))
        val share = Button(this).apply { text = "Share output report"; skin.style(this, primary = true) }
        val addNotes = Button(this).apply { text = "Add setup notes"; skin.style(this) }
        val dialog = object : AlertDialog(this) {
            override fun onWindowFocusChanged(hasFocus: Boolean) {
                super.onWindowFocusChanged(hasFocus)
                if (hasFocus && visible && isShowing) { share.isEnabled = true; addNotes.isEnabled = true }
            }
        }
        header.addView(roseButton(this, skin, "Back", compact = true) { dialog.dismiss() })
        root.addView(header)
        val preview = TextView(this).apply {
            text = report.text; textSize = 16f; setTextColor(skin.text)
            tag = "output-report-preview"; setTextIsSelectable(true)
            setPadding(0, skin.dp(12), 0, skin.dp(12))
        }
        root.addView(ScrollView(this).apply { addView(preview) }, LinearLayout.LayoutParams(-1, 0, 1f))
        root.addView(TextView(this).apply {
            text = "Snapshot only. Outputs may have changed."; textSize = 14f
            setTextColor(skin.text); setPadding(0, skin.dp(8), 0, 0)
        }, LinearLayout.LayoutParams(-1, -2))
        root.addView(addNotes, LinearLayout.LayoutParams(-1, -2).apply { topMargin = skin.dp(8) })
        root.addView(share, LinearLayout.LayoutParams(-1, -2).apply { topMargin = skin.dp(8) })
        dialog.setView(root)
        dialog.setOnDismissListener {
            if (reportDialog === dialog) { reportDialog = null; reportShareButton = null; reportNotesButton = null }
        }
        addNotes.setOnClickListener {
            if (!visible || isFinishing || isDestroyed || !dialog.isShowing ||
                dialog.window?.decorView?.hasWindowFocus() != true || !addNotes.isEnabled) return@setOnClickListener
            addNotes.isEnabled = false
            clearSnapshot(IDLE)
            try { TestSetupActivity.openWithOutput(this, skin.dark, report) }
            catch (error: RuntimeException) {
                addNotes.isEnabled = true
                if (error !is ActivityNotFoundException && error !is SecurityException) throw error
                Toast.makeText(this, "Setup notes are unavailable. You can still share the output report.", Toast.LENGTH_LONG).show()
            }
        }
        share.setOnClickListener {
            if (!visible || isFinishing || isDestroyed || !dialog.isShowing ||
                dialog.window?.decorView?.hasWindowFocus() != true || !share.isEnabled) return@setOnClickListener
            share.isEnabled = false
            // Leaving for a chooser never leaves an apparently current list
            // behind. The separately reviewed text remains the same copy.
            clearSnapshot(IDLE)
            val send = Intent(Intent.ACTION_SEND).apply {
                type = "text/plain"; putExtra(Intent.EXTRA_TEXT, report.text)
            }
            try { startActivity(Intent.createChooser(send, null)) }
            catch (error: RuntimeException) {
                share.isEnabled = true
                if (error !is ActivityNotFoundException && error !is SecurityException) throw error
                Toast.makeText(this, "Sharing is unavailable. You can read the report shown here.", Toast.LENGTH_LONG).show()
            }
        }
        reportDialog = dialog; reportShareButton = share; reportNotesButton = addNotes
        dialog.show()
        val display = resources.displayMetrics
        dialog.window?.setLayout(minOf(display.widthPixels - skin.dp(24), skin.dp(680)),
            (display.heightPixels * .85f).toInt())
    }

    private fun outputKind(type: Int): String = when (type) {
        AudioDeviceInfo.TYPE_BUILTIN_SPEAKER -> "Built-in speaker"
        AudioDeviceInfo.TYPE_BUILTIN_EARPIECE -> "Earpiece"
        AudioDeviceInfo.TYPE_WIRED_HEADSET -> "Wired headset"
        AudioDeviceInfo.TYPE_WIRED_HEADPHONES -> "Wired headphones"
        AudioDeviceInfo.TYPE_BLUETOOTH_A2DP -> "Bluetooth media output"
        AudioDeviceInfo.TYPE_BLUETOOTH_SCO -> "Bluetooth call output"
        AudioDeviceInfo.TYPE_HDMI -> "HDMI"
        AudioDeviceInfo.TYPE_HDMI_ARC -> "HDMI ARC"
        AudioDeviceInfo.TYPE_USB_DEVICE -> "USB audio device"
        AudioDeviceInfo.TYPE_USB_ACCESSORY -> "USB accessory"
        AudioDeviceInfo.TYPE_USB_HEADSET -> "USB headset"
        AudioDeviceInfo.TYPE_LINE_ANALOG -> "Analog line output"
        AudioDeviceInfo.TYPE_LINE_DIGITAL -> "Digital line output"
        AudioDeviceInfo.TYPE_DOCK -> "Dock output"
        AudioDeviceInfo.TYPE_UNKNOWN -> "Unknown output type"
        else -> "Other output type ($type)"
    }

    private fun encodingName(value: Int): String = when (value) {
        AudioFormat.ENCODING_PCM_8BIT -> "PCM 8-bit"
        AudioFormat.ENCODING_PCM_16BIT -> "PCM 16-bit"
        AudioFormat.ENCODING_PCM_FLOAT -> "PCM float"
        else -> "Other encoding ($value)"
    }

    companion object {
        private const val IDLE = "Not read yet. Tap Refresh outputs."
    }
}
