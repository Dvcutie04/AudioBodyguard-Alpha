package com.aqss.bodyguard.prototype

import android.Manifest
import android.app.Activity
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.*
import android.os.*
import android.provider.MediaStore
import android.speech.*
import android.view.View
import android.widget.*
import com.aqss.nativefeedback.TVPhotoHints
import com.google.mlkit.vision.common.InputImage
import com.google.mlkit.vision.text.TextRecognition
import com.google.mlkit.vision.text.latin.TextRecognizerOptions
import java.util.concurrent.Executors

/** User-initiated foreground input. No output controller, device adapter or socket. */
class InputAssistanceActivity : Activity() {
    private lateinit var skin: InterfaceTheme
    private lateinit var status: TextView
    private lateinit var details: TextView
    private lateinit var levelText: TextView
    private lateinit var startButton: Button
    private lateinit var meter: InputMeter
    private lateinit var column: LinearLayout
    private val handler = Handler(Looper.getMainLooper())
    private var recognizer: SpeechRecognizer? = null
    private var generation = 0
    private var running = false
    private var lastLevelAt = 0L
    private var photoGeneration = 0
    private val worker = Executors.newSingleThreadExecutor()
    private var instructions: TextView? = null
    private val expiry = Runnable { stopVoice("30-second limit reached. Tap Start to try again.") }
    private val isVoice get() = intent.getStringExtra("mode") == "voice"

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        skin = InterfaceTheme(this, intent.getBooleanExtra("dark", true))
        val root = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setPadding(skin.dp(16), skin.dp(28), skin.dp(16), skin.dp(16)); setBackgroundColor(skin.background) }
        val header = LinearLayout(this)
        header.addView(TextView(this).apply { text = if (isVoice) "Voice check" else "TV photo setup"; textSize = 24f; setTextColor(skin.text) }, LinearLayout.LayoutParams(0, -2, 1f))
        header.addView(Button(this).apply { text = "Close"; skin.style(this); setOnClickListener { finish() } })
        root.addView(header)
        column = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setPadding(0, skin.dp(12), 0, 0) }
        root.addView(ScrollView(this).apply { addView(column) }, LinearLayout.LayoutParams(-1, 0, 1f))
        setContentView(root)
        // Use the same insets behavior on Android 15+ as the main shell.
        root.setOnApplyWindowInsetsListener { view, insets ->
            val bars = if (Build.VERSION.SDK_INT >= 30) insets.getInsets(android.view.WindowInsets.Type.systemBars()) else null
            if (bars != null) view.setPadding(skin.dp(16) + bars.left, skin.dp(12) + bars.top, skin.dp(16) + bars.right, skin.dp(12) + bars.bottom)
            insets
        }
        if (isVoice) voicePage() else photoPage()
    }
    private fun label(value: String, large: Boolean = false): TextView = TextView(this).apply {
        text = value; textSize = if (large) 20f else 16f; setTextColor(skin.text); setPadding(0, skin.dp(8), 0, skin.dp(8)); column.addView(this)
    }
    private fun action(value: String, block: () -> Unit): Button = Button(this).apply {
        text = value; skin.style(this); setOnClickListener { block() }; column.addView(this, LinearLayout.LayoutParams(-1, -2).apply { bottomMargin = skin.dp(10) })
    }
    private fun voicePage() {
        label("See what your phone hears", true)
        label("Tap Start, then say: ‘Make the TV quieter.’ The bars show incoming sound. The text shows the words the phone thinks you said. This check does not send a command.")
        status = label("Microphone off", true)
        meter = InputMeter(this, skin.violet)
        column.addView(meter, LinearLayout.LayoutParams(-1, skin.dp(120)))
        levelText = label("No microphone samples yet")
        label("Sound-level history, oldest to newest. Levels come from the speech recognizer; some phones do not supply them. This is not room loudness, a hearing-safety measurement, frequency bands or a syllable count.")
        label("Recognized words · may change", true)
        details = label("No words recognized yet")
        startButton = action("Start voice check") { if (running) stopVoice() else startVoice() }
        action("Clear words") { stopVoice(); details.text = "No words recognized yet" }
        label("On-device recognition only, Android 12 or later with a supported local recognizer. No cloud fallback. No audio file is saved. Closing or leaving the app stops listening and clears words. Noise, accents and overlapping voices can cause errors; a moving meter does not prove every word or sound was understood.")
    }
    private fun startVoice() {
        stopVoice(); details.text = "No words recognized yet"
        if (Build.VERSION.SDK_INT < 31 || !SpeechRecognizer.isOnDeviceRecognitionAvailable(this)) {
            status.text = "On-device speech recognition unavailable. No cloud fallback is used."; return
        }
        if (checkSelfPermission(Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(arrayOf(Manifest.permission.RECORD_AUDIO), 41); return
        }
        val token = ++generation
        try {
            val service = SpeechRecognizer.createOnDeviceSpeechRecognizer(this); recognizer = service; running = true
            startButton.text = "Stop listening"; status.text = "Starting microphone…"
            service.setRecognitionListener(object : RecognitionListener {
                private fun valid() = running && generation == token && !isFinishing
                override fun onReadyForSpeech(params: Bundle?) { if (valid()) status.text = "Listening — on this phone, up to 30 seconds" }
                override fun onBeginningOfSpeech() { if (valid()) status.text = "Speech detected — words are provisional" }
                override fun onRmsChanged(rmsdB: Float) {
                    if (!valid() || !rmsdB.isFinite()) return
                    val now = SystemClock.elapsedRealtime()
                    if (now - lastLevelAt < 100) return
                    lastLevelAt = now
                    meter.add(((rmsdB + 2f) / 12f).coerceIn(0f, 1f))
                    levelText.text = "Recognizer input level: %.1f dB (not dB SPL)".format(rmsdB)
                }
                override fun onBufferReceived(buffer: ByteArray?) { /* No raw audio retained. */ }
                override fun onEndOfSpeech() { if (valid()) { status.text = "Finishing recognition…"; meter.clear(); levelText.text = "No live microphone samples" } }
                override fun onError(error: Int) { if (valid()) stopVoice("Recognition stopped or unavailable (code $error). Words may be incomplete. Tap Start to retry.") }
                private fun words(results: Bundle?) { results?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)?.firstOrNull()?.let { details.text = it.take(500) } }
                override fun onResults(results: Bundle?) { if (valid()) { words(results); stopVoice("Finished — review the words. Nothing was sent to a TV.") } }
                override fun onPartialResults(partialResults: Bundle?) { if (valid()) words(partialResults) }
                override fun onEvent(eventType: Int, params: Bundle?) {}
            })
            service.startListening(Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
                putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
                putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true)
                putExtra(RecognizerIntent.EXTRA_PREFER_OFFLINE, true)
                putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 1)
            })
            handler.postDelayed(expiry, 30_000)
        } catch (_: Exception) { stopVoice("Microphone could not start. Check permission and the installed speech service.") }
    }
    private fun stopVoice(message: String = "Microphone off") {
        generation++; running = false; handler.removeCallbacks(expiry)
        recognizer?.let { service -> recognizer = null; try { service.cancel(); service.destroy() } catch (_: Exception) {} }
        if (::startButton.isInitialized) { startButton.text = "Start voice check"; status.text = message; meter.clear(); levelText.text = "No live microphone samples" }
    }
    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<out String>, grantResults: IntArray) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == 41 && ::status.isInitialized) status.text = if (grantResults.firstOrNull() == PackageManager.PERMISSION_GRANTED) "Permission granted. Tap Start when you are ready." else "Microphone permission denied. You can change it in Android Settings."
    }
    private fun photoPage() {
        label("Find your TV details", true)
        label("Take a clear picture of the model label, or the TV’s Network / IP settings screen. Avoid passwords. Do not move a heavy or wall-mounted TV: use its About screen instead.")
        action("Take a TV photo") {
            try { startActivityForResult(Intent(MediaStore.ACTION_IMAGE_CAPTURE), 52) }
            catch (_: Exception) { status.text = "Camera unavailable. Take a photo in your Camera app, then choose it below." }
        }
        action("Choose a photo") {
            try { startActivityForResult(Intent(Intent.ACTION_GET_CONTENT).apply { type = "image/*"; addCategory(Intent.CATEGORY_OPENABLE) }, 51) }
            catch (_: Exception) { status.text = "No photo picker available. Use the instructions below." }
        }
        status = label("No photo selected", true)
        details = label("Brand: Not identified\nModel: Not identified\nTV IP hint: Not identified")
        label("These are unverified hints. Only a clearly labeled private IPv4 address is shown. We never use a photo as permission to control your TV.")
        action("Show connection instructions") { instructions?.visibility = if (instructions?.visibility == View.VISIBLE) View.GONE else View.VISIBLE }
        instructions = label("1. Open Settings on the TV. Look for About, Support or Device information to find its model. Menu names differ.\n\n2. Look for Network, Connection or Network status, then IP settings. Photograph the IP address row — not Gateway or DNS. The back label usually does not show the current IP.\n\n3. Put the phone and TV on the same home Wi-Fi. Avoid a guest network. IP addresses can change and do not prove TV identity.\n\n4. Supported Samsung models use SmartThings and may ask for approval on the TV. For Alexa or Google Home, add/link a supported TV inside that app and follow its approval steps. Compatibility varies by model.\n\nAQSS pairing is not available yet. This tool reads a photo and helps you prepare; it does not connect or change the TV.").apply { visibility = View.GONE }
        action("Clear photo details") { clearPhoto() }
        label("Text recognition runs on this phone. AQSS does not save or upload the image, serial number or password. Your camera/gallery may keep the original outside AQSS. Details clear on close. Camera previews can be too small for text: choose the original photo if needed.")
    }
    private fun clearPhoto() {
        photoGeneration++; status.text = "No photo selected"; details.text = "Brand: Not identified\nModel: Not identified\nTV IP hint: Not identified"
    }
    @Deprecated("Platform callback retained for API 26 compatibility")
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (resultCode != RESULT_OK || (requestCode != 51 && requestCode != 52)) return
        clearPhoto(); status.text = "Reading text on this phone…"; val token = photoGeneration
        worker.execute {
            try {
                val bitmap: Bitmap = if (requestCode == 52) {
                    @Suppress("DEPRECATION")
                    (data?.extras?.get("data") as? Bitmap) ?: throw IllegalArgumentException("No camera image")
                } else {
                    val uri = data?.data ?: throw IllegalArgumentException("No photo")
                    if (uri.scheme != "content") throw IllegalArgumentException("Unsupported photo source")
                    if (Build.VERSION.SDK_INT >= 28) {
                        ImageDecoder.decodeBitmap(ImageDecoder.createSource(contentResolver, uri)) { decoder, info, _ ->
                            val scale = minOf(1.0, 2048.0 / maxOf(info.size.width, info.size.height))
                            decoder.setTargetSize(maxOf(1, (info.size.width * scale).toInt()), maxOf(1, (info.size.height * scale).toInt()))
                            decoder.allocator = ImageDecoder.ALLOCATOR_SOFTWARE
                        }
                    } else {
                        val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
                        contentResolver.openInputStream(uri).use { BitmapFactory.decodeStream(it, null, bounds) }
                        var sample = 1
                        while (maxOf(bounds.outWidth, bounds.outHeight) / sample > 2048) sample *= 2
                        contentResolver.openInputStream(uri).use { BitmapFactory.decodeStream(it, null, BitmapFactory.Options().apply { inSampleSize = sample }) } ?: throw IllegalArgumentException("Unreadable photo")
                    }
                }
                val scanner = TextRecognition.getClient(TextRecognizerOptions.DEFAULT_OPTIONS)
                scanner.process(InputImage.fromBitmap(bitmap, 0))
                    .addOnSuccessListener { result ->
                        if (!isDestroyed && token == photoGeneration) {
                            val text = result.textBlocks.flatMap { it.lines }.take(100).joinToString("\n") { it.text }
                            val hints = TVPhotoHints(text)
                            details.text = "Brand: ${hints.brand ?: "Not identified"}\nModel: ${hints.model ?: "Not identified"}\nTV IP hint: ${hints.address ?: "Not identified"}"
                            status.text = "Check these details. Text recognition can make mistakes. Nothing is connected."
                        }
                    }
                    .addOnFailureListener { if (!isDestroyed && token == photoGeneration) status.text = "Could not read this picture. Try brighter light and a closer photo." }
                    .addOnCompleteListener { scanner.close(); bitmap.recycle() }
            } catch (_: Exception) {
                runOnUiThread { if (!isDestroyed && token == photoGeneration) status.text = "Photo could not be read. Choose a clear photo of the label or settings screen." }
            }
        }
    }
    override fun onPause() {
        if (isVoice) { stopVoice(); if (::details.isInitialized) details.text = "No words recognized yet" }
        super.onPause()
    }
    override fun onDestroy() { stopVoice(); photoGeneration++; worker.shutdownNow(); super.onDestroy() }
}

private class InputMeter(activity: Activity, color: Int) : View(activity) {
    private val paint = Paint(Paint.ANTI_ALIAS_FLAG).apply { this.color = color }
    private val levels = ArrayDeque<Float>()
    init { importantForAccessibility = IMPORTANT_FOR_ACCESSIBILITY_NO }
    fun add(level: Float) { levels.addLast(level); while (levels.size > 40) levels.removeFirst(); invalidate() }
    fun clear() { levels.clear(); invalidate() }
    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        val values = levels.toList(); val step = width / 40f
        for (i in 0 until 40) {
            val index = i - (40 - values.size); val level = if (index >= 0) values[index] else 0f
            val h = maxOf(2f, height * level)
            canvas.drawRoundRect(i * step, (height - h) / 2, i * step + maxOf(1f, step - 2), (height + h) / 2, 2f, 2f, paint)
        }
    }
}
