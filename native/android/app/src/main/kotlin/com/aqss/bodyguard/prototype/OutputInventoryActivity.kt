package com.aqss.bodyguard.prototype

import android.app.Activity
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
import com.aqss.nativefeedback.OutputDeviceAdvertisement
import com.aqss.nativefeedback.OutputDeviceInventory
import java.lang.ref.WeakReference

/** Available OS metadata only. Never opens a stream or requests audio focus. */
class OutputInventoryActivity : Activity() {
    private lateinit var skin: InterfaceTheme
    private lateinit var results: TextView
    private var visible = false
    private var hasSnapshot = false
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
        words("${Build.MANUFACTURER.take(64)} ${Build.MODEL.take(64)}\nAndroid ${Build.VERSION.RELEASE.take(64)} · API ${Build.VERSION.SDK_INT}", 15f)
        words("Selected playback route: Unknown\nNegotiated format: Unknown", 18f)
        words("Available outputs can change. Listed capabilities do not identify an active route or prove a working connection.", 15f)
        results = words(IDLE, 16f)
        words("This screen plays no sound and uses no microphone. Details stay on this screen and clear when you leave. It cannot verify TV control or audio protection.", 15f)
        root.addView(ScrollView(this).apply { addView(column) }, LinearLayout.LayoutParams(-1, 0, 1f))
        root.addView(Button(this).apply {
            text = "Refresh outputs"; skin.style(this, primary = true)
            setOnClickListener { refreshOutputs() }
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
        hasSnapshot = false; results.text = IDLE
        registerNotices()
    }

    override fun onPause() {
        visible = false; hasSnapshot = false; results.text = IDLE
        unregisterNotices()
        super.onPause()
    }

    override fun onDestroy() {
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
        hasSnapshot = false
        results.text = "Output list needs a fresh check. Tap Refresh outputs."
    }

    private fun refreshOutputs() {
        if (!visible || !hasWindowFocus() || isFinishing || isDestroyed) return
        hasSnapshot = false
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
            buildString {
                append(inventory.summaryText)
                inventory.devices.forEachIndexed { index, device ->
                    append("\n\n${index + 1}. ${device.kind}")
                    append("\nAdvertised sample rates: ${device.sampleRatesText}")
                    append("\nAdvertised channel counts: ${device.channelCountsText}")
                    append("\nAdvertised encodings: ${device.encodingsText}")
                }
                if (deviceCallback == null) append("\n\nAutomatic change notices unavailable.")
                append("\n\nSnapshot only. Tap Refresh outputs to read again.")
            }.also { hasSnapshot = true }
        } catch (_: RuntimeException) {
            "Output inventory unavailable. Tap Refresh outputs to try again.\nNo output route has been verified."
        }
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
