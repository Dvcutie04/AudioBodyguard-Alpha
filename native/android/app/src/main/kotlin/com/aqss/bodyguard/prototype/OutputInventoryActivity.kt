package com.aqss.bodyguard.prototype

import android.app.Activity
import android.media.AudioDeviceInfo
import android.media.AudioFormat
import android.media.AudioManager
import android.os.Build
import android.os.Bundle
import android.view.WindowInsets
import android.widget.Button
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import com.aqss.nativefeedback.OutputDeviceAdvertisement
import com.aqss.nativefeedback.OutputDeviceInventory

/** Available OS metadata only. Never opens a stream or requests audio focus. */
class OutputInventoryActivity : Activity() {
    private lateinit var skin: InterfaceTheme
    private lateinit var results: TextView
    private var visible = false

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
        results = words("Not read yet. Tap Refresh outputs.", 16f)
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
        results.text = "Not read yet. Tap Refresh outputs."
    }

    override fun onPause() {
        visible = false; results.text = "Not read yet. Tap Refresh outputs."
        super.onPause()
    }

    private fun refreshOutputs() {
        if (!visible || !hasWindowFocus() || isFinishing || isDestroyed) return
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
                append("\n\nSnapshot only. Tap Refresh outputs to read again.")
            }
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
}
