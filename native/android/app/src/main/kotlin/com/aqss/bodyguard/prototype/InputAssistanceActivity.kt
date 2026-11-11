package com.aqss.bodyguard.prototype

import android.Manifest
import android.app.Activity
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.*
import android.net.Uri
import android.os.*
import android.provider.Settings
import android.speech.*
import android.view.View
import android.widget.*
import com.aqss.nativefeedback.LocalTVTarget
import com.aqss.nativefeedback.TVPhotoHints
import com.aqss.nativefeedback.PhotoReviewRun
import com.aqss.nativefeedback.PhotoWorkSlot
import com.aqss.nativefeedback.boundedTVPhotoText
import com.aqss.nativefeedback.TutorialContent
import com.aqss.nativefeedback.ForegroundMicrophoneGate
import com.aqss.nativefeedback.ForegroundAudioExclusion
import com.aqss.nativefeedback.OwnedSkipAction
import com.aqss.nativefeedback.OwnedSkipDecision
import com.aqss.nativefeedback.OwnedSkipSnapshot
import com.aqss.nativefeedback.OwnedVoiceSkipGate
import com.aqss.nativefeedback.VoiceInputRun
import com.aqss.nativefeedback.boundedRecognizedWords
import com.google.mlkit.vision.common.InputImage
import com.google.mlkit.vision.text.TextRecognition
import com.google.mlkit.vision.text.TextRecognizer
import com.google.mlkit.vision.text.latin.TextRecognizerOptions
import com.google.android.gms.tasks.Task
import com.google.android.gms.tasks.Tasks
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
    private lateinit var footer: LinearLayout
    private val handler = Handler(Looper.getMainLooper())
    private var recognizer: SpeechRecognizer? = null
    private var generation = 0L
    private val voiceRun = VoiceInputRun()
    private val voiceSkipGate = OwnedVoiceSkipGate()
    private var voiceSkipRunId: String? = null
    // Emulator-only supplied FINAL TEXT, deliberately not microphone/OS recognition.
    private val finalTextFixtureGate = OwnedVoiceSkipGate()
    private var finalTextFixtureRunId: String? = null
    private var finalTextFixtureSequence = 0
    private val finalTextFixtureEnabled: Boolean
        get() = (applicationInfo.flags and android.content.pm.ApplicationInfo.FLAG_DEBUGGABLE) != 0 &&
            (Build.HARDWARE == "ranchu" || Build.FINGERPRINT.startsWith("generic"))
    private var demoGeneration = 1
    private var demoIntroAvailable = true
    private var demoRecapAvailable = true
    private var demoIntroButton: Button? = null
    private var demoRecapButton: Button? = null
    private var demoResetButton: Button? = null
    private var demoStatus: TextView? = null
    // Silent, bundled local video only. This is NOT an external media adapter.
    private var localVideo: VideoView? = null
    private var localMedia: android.media.MediaPlayer? = null
    private var localVideoStatus: TextView? = null
    private var localVideoActive = false
    private var localVideoBusy = false
    private var localVideoEpoch = 0
    private var localStage: OwnedSkipAction? = null
    // Persist only whether an abandoned owned-video trial requires explicit Reset.
    // Do not persist a media control, recognized words, or an authorization.
    private val localVideoNeedsResetKey = "needs_reset_v1"
    private val localVideoPrefs get() = getSharedPreferences("aqss_owned_local_video", MODE_PRIVATE)

    private fun updateLocalStatus(message: String) { localVideoStatus?.text = message }

    private fun retireFinalTextFixture() {
        finalTextFixtureGate.stop()
        finalTextFixtureRunId = null
    }
    private fun readyFinalTextFixture() {
        if (!finalTextFixtureEnabled) return
        retireFinalTextFixture()
        finalTextFixtureSequence++
        val id = "fixture-${finalTextFixtureSequence}"
        if (finalTextFixtureGate.start(id, demoSnapshot())) finalTextFixtureRunId = id
    }
    private fun requestFinalTextFixture(action: OwnedSkipAction) {
        if (!finalTextFixtureEnabled || running || recognizer != null) return
        val id = finalTextFixtureRunId ?: return
        // Explicit synthetic final text: no OS recognizer, permission or audio was exercised.
        val words = if (action == OwnedSkipAction.SKIP_INTRO)
            "Audio Bodyguard, skip intro" else "Audio Bodyguard, skip recap"
        val decision = finalTextFixtureGate.requestFinal(
            words, id, demoSnapshot(), permitted = true,
            foreground = visible && hasWindowFocus() && !isFinishing && !isDestroyed,
            pressOwnedButton = ::pressDemo)
        if (decision != OwnedSkipDecision.REQUESTED) {
            demoStatus?.text = "Fixture final text refused; no additional player action"
        }
    }

    // A competing user seek on the same actual local decoder, for emulator-only tests.
    // It is NOT voice recognition and never contacts a remote player.
    private fun moveFinalTextFixturePlayhead() {
        if (!finalTextFixtureEnabled || running || recognizer != null ||
            !localVideoActive || localVideoBusy) return
        val player = localMedia ?: return
        val stage = localStage ?: return
        val target = if (stage == OwnedSkipAction.SKIP_INTRO) 1000 else 5000
        val epoch = ++localVideoEpoch
        localVideoBusy = true
        player.setOnSeekCompleteListener { observedPlayer ->
            if (localVideoEpoch != epoch) return@setOnSeekCompleteListener
            localVideoBusy = false
            val actual = observedPlayer.currentPosition
            if (kotlin.math.abs(actual - target) > 300) {
                updateLocalStatus("Local video: fixture playhead move NOT observed")
            } else {
                updateLocalStatus(if (stage == OwnedSkipAction.SKIP_INTRO)
                    "Local video moved: intro playhead now 1s"
                    else "Local video moved: recap playhead now 5s")
            }
        }
        try {
            player.seekTo(target.toLong(), android.media.MediaPlayer.SEEK_CLOSEST)
        } catch (_: RuntimeException) {
            localVideoBusy = false
            updateLocalStatus("Local video: fixture playhead move refused")
        }
    }

    private fun closeLocalVideo() {
        retireFinalTextFixture()
        localVideoEpoch++; localStage = null; localVideoBusy = false
        localVideoActive = false
        localMedia = null
        localVideo?.stopPlayback()
        updateLocalStatus("Local video not prepared")
    }

    /** Backgrounded local video cannot leave its stale Skip control enabled. */
    private fun suspendLocalVideo() {
        if (!localVideoActive) return
        closeLocalVideo()
        demoIntroAvailable = false; demoRecapAvailable = false; demoGeneration++
        demoIntroButton?.isEnabled = false; demoRecapButton?.isEnabled = false
        demoStatus?.text = "Test player paused — reset to prepare video again"
    }

    private fun prepareLocalVideo(action: OwnedSkipAction) {
        if (running || localVideoBusy || recognizer != null) return
        val video = localVideo ?: return
        // Fail closed if the local-only retirement marker cannot be saved.
        if (!localVideoPrefs.edit().putBoolean(localVideoNeedsResetKey, true).commit()) {
            updateLocalStatus("Local video unavailable: trial state could not be saved")
            return
        }
        localVideoEpoch++; val epoch = localVideoEpoch
        localVideoActive = true; localStage = null; localVideoBusy = true
        demoIntroAvailable = false; demoRecapAvailable = false; demoGeneration++
        demoIntroButton?.isEnabled = false; demoRecapButton?.isEnabled = false
        updateLocalStatus("Local video: preparing segment")
        val entry = if (action == OwnedSkipAction.SKIP_INTRO) 0 else 4000
        video.setOnErrorListener { _, _, _ ->
            if (localVideoEpoch == epoch) {
                localVideoBusy = false
                updateLocalStatus("Local video unavailable: media decoder failed")
            }
            true
        }
        video.setOnPreparedListener { mp ->
            // Only a retired prepare may be ignored. The matching epoch is the active video.
            if (localVideoEpoch != epoch) return@setOnPreparedListener
            localMedia = mp
            mp.setVolume(0f, 0f)
            if (mp.duration !in 7500..8500) {
                localVideoBusy = false
                updateLocalStatus("Local video unavailable: wrong clip duration")
                return@setOnPreparedListener
            }
            fun completeStage() {
                if (localVideoEpoch != epoch) return
                val observed = mp.currentPosition
                localVideoBusy = false
                if (kotlin.math.abs(observed - entry) > 300) {
                    updateLocalStatus("Local video unavailable: entry not observed")
                    return
                }
                localStage = action
                demoIntroAvailable = action == OwnedSkipAction.SKIP_INTRO
                demoRecapAvailable = action == OwnedSkipAction.SKIP_RECAP
                demoGeneration++
                demoIntroButton?.isEnabled = demoIntroAvailable
                demoRecapButton?.isEnabled = demoRecapAvailable
                updateLocalStatus(if (action == OwnedSkipAction.SKIP_INTRO)
                    "Local video: intro ready at 0s" else "Local video: recap ready at 4s")
                readyFinalTextFixture()
            }
            if (entry == 0 && mp.currentPosition <= 300) {
                completeStage()
            } else {
                mp.setOnSeekCompleteListener { if (localVideoEpoch == epoch) completeStage() }
                mp.seekTo(entry.toLong(), android.media.MediaPlayer.SEEK_CLOSEST)
            }
        }
        video.setVideoURI(Uri.parse("android.resource://$packageName/${R.raw.voice_skip_sample}"))
    }

    private fun requestLocalVideoSkip(action: OwnedSkipAction): Boolean {
        val mp = localMedia ?: return false
        if (!localVideoActive || localVideoBusy || localStage != action) return false
        // Re-read the actual player position before dispatch, not a cached UI
        // label or control generation. A changed section revokes the affordance.
        val entry = if (action == OwnedSkipAction.SKIP_INTRO) 0 else 4000
        if (kotlin.math.abs(mp.currentPosition - entry) > 300) {
            localStage = null
            demoIntroAvailable = false; demoRecapAvailable = false; demoGeneration++
            demoIntroButton?.isEnabled = false; demoRecapButton?.isEnabled = false
            updateLocalStatus("Local video unavailable: selected section changed")
            return false
        }
        localVideoEpoch++; val epoch = localVideoEpoch
        localStage = null; localVideoBusy = true
        demoIntroAvailable = false; demoRecapAvailable = false; demoGeneration++
        demoIntroButton?.isEnabled = false; demoRecapButton?.isEnabled = false
        demoStatus?.text = if (action == OwnedSkipAction.SKIP_INTRO)
            "Test player: Skip Intro button activated" else "Test player: Skip Recap button activated"
        updateLocalStatus("Local video: transition requested, awaiting player readback")
        val target = if (action == OwnedSkipAction.SKIP_INTRO) 2000 else 6000
        mp.setOnSeekCompleteListener { player ->
            if (localVideoEpoch != epoch) return@setOnSeekCompleteListener
            localVideoBusy = false
            val actual = player.currentPosition
            if (kotlin.math.abs(actual - target) > 300) {
                updateLocalStatus("Local video: requested but position NOT verified")
            } else {
                // Direct native MediaPlayer position readback, not button-label proof.
                updateLocalStatus(if (action == OwnedSkipAction.SKIP_INTRO)
                    "Local video observed: intro ends at 2s"
                    else "Local video observed: recap ends at 6s")
            }
        }
        return try {
            mp.seekTo(target.toLong(), android.media.MediaPlayer.SEEK_CLOSEST)
            true // REQUESTED. Readback arrives asynchronously.
        } catch (_: RuntimeException) {
            localVideoBusy = false
            updateLocalStatus("Local video: player seek was refused")
            false
        }
    }

    private fun demoSnapshot() = OwnedSkipSnapshot(
        "owned-test-player", "voice-demo", "test-episode", demoGeneration,
        demoIntroAvailable, demoIntroAvailable, demoRecapAvailable, demoRecapAvailable
    )
    /** Both displayed demo buttons and final admitted speech call this same handler. */
    private fun pressDemo(action: OwnedSkipAction): Boolean {
        if (localVideoActive) return requestLocalVideoSkip(action)
        when (action) {
            OwnedSkipAction.SKIP_INTRO -> if (demoIntroAvailable) {
                demoIntroAvailable = false; demoGeneration++
                demoStatus?.text = "Test player: Skip Intro button activated"
            } else return false
            OwnedSkipAction.SKIP_RECAP -> if (demoRecapAvailable) {
                demoRecapAvailable = false; demoGeneration++
                demoStatus?.text = "Test player: Skip Recap button activated"
            } else return false
        }
        demoIntroButton?.isEnabled = demoIntroAvailable
        demoRecapButton?.isEnabled = demoRecapAvailable
        return true
    }
    private fun resetDemo() {
        if (running) return
        if (!localVideoPrefs.edit().remove(localVideoNeedsResetKey).commit()) {
            demoStatus?.text = "Test player reset unavailable"
            return
        }
        demoIntroAvailable = true; demoRecapAvailable = true; demoGeneration++
        demoIntroButton?.isEnabled = true; demoRecapButton?.isEnabled = true
        demoStatus?.text = "Test player ready — nothing connected"
        closeLocalVideo()
    }
    private fun handleFinalDemoCommand(text: String?): String {
        val id = voiceSkipRunId ?: return "Finished — no supported test-player command. Nothing sent to a TV."
        // The Android final onResults event uses the same gate exercised in Kotlin tests.
        return when (voiceSkipGate.requestFinal(
            text, id, demoSnapshot(),
            checkSelfPermission(Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED,
            visible && hasWindowFocus() && !isFinishing, ::pressDemo
        )) {
            OwnedSkipDecision.REQUESTED -> "Test-player Skip button requested. No TV command sent."
            OwnedSkipDecision.CALL_FAILED -> "Test-player button unavailable. No TV command sent."
            OwnedSkipDecision.UNAVAILABLE -> "Skip target changed or was unavailable. No TV command sent."
        }
    }
    private val microphone = ForegroundMicrophoneGate.process
    private var microphoneLease: ForegroundMicrophoneGate.Lease? = null
    private var visible = false
    private var running = false
    private var permissionGuidance = false
    private var availabilityGuidance = false
    private var permissionSettingsButton: Button? = null
    private var recent: Button? = null
    private val microphoneDeniedMessage = "Microphone permission denied. In app settings, choose Permissions, then Microphone."
    private var lastLevelAt = 0L
    private val photoRun = PhotoReviewRun(SystemClock::elapsedRealtime)
    private val photoWork = PhotoWorkSlot.process
    private var photoObservation: PhotoWorkSlot.Observation? = null
    private var waitingForPhotoWork = false
    private data class PhotoRequest(val code: Int, val token: PhotoReviewRun.Token, val capture: TVPhotoCapture?)
    private var cameraPhoto: TVPhotoCapture? = null
    private var readingPhoto: PhotoReviewRun.Token? = null
    private var photoWatchdog: Runnable? = null
    private var pendingPhoto: PhotoRequest? = null
    private var nextPhotoRequestCode = 100
    private val worker = Executors.newSingleThreadExecutor()
    private var instructions: TextView? = null
    private var photoBrand: String? = null
    private var useBrand: Button? = null
    private var photoExtra: TextView? = null
    private var photoTarget: LocalTVTarget? = null
    private var photoAddressReview: TextView? = null
    private var usePhotoAddress: Button? = null
    private val voiceWatchdog = object : Runnable {
        override fun run() {
            if (!validVoice(generation)) return
            val now = SystemClock.elapsedRealtime()
            if (lastLevelAt != 0L && now - lastLevelAt >= 750) {
                lastLevelAt = 0; meter.clear(); levelText.text = "No current recognizer level"
            }
            handler.postDelayed(this, 100)
        }
    }
    private val isVoice get() = intent.getStringExtra("mode") == "voice"

    override fun onCreate(savedInstanceState: Bundle?) {
        val dark = intent.getBooleanExtra("dark", true)
        setTheme(if (dark) R.style.AQSSMidnightTheme else R.style.AQSSReadOnlyTheme)
        super.onCreate(savedInstanceState)
        if (isVoice && localVideoPrefs.getBoolean(localVideoNeedsResetKey, false)) {
            demoIntroAvailable = false
            demoRecapAvailable = false
        }
        skin = InterfaceTheme(this, dark)
        val root = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setPadding(skin.dp(16), skin.dp(28), skin.dp(16), skin.dp(16)); setBackgroundColor(skin.background) }
        val header = LinearLayout(this)
        header.addView(TextView(this).apply { text = if (isVoice) "Voice check" else "TV photo setup"; textSize = 24f; setTextColor(skin.text) }, LinearLayout.LayoutParams(0, -2, 1f))
        header.addView(roseButton(this, skin, "Close") { finish() })
        root.addView(header)
        column = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setPadding(0, skin.dp(12), 0, 0) }
        root.addView(ScrollView(this).apply { addView(column) }, LinearLayout.LayoutParams(-1, 0, 1f))
        footer = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        root.addView(footer)
        setContentView(root)
        // Use the same insets behavior on Android 15+ as the main shell.
        root.setOnApplyWindowInsetsListener { view, insets ->
            if (Build.VERSION.SDK_INT >= 30) {
                val bars = insets.getInsets(android.view.WindowInsets.Type.systemBars())
                view.setPadding(skin.dp(16) + bars.left, skin.dp(12) + bars.top, skin.dp(16) + bars.right, skin.dp(12) + bars.bottom)
            }
            insets
        }
        if (isVoice) voicePage() else photoPage()
    }
    private fun label(value: String, large: Boolean = false): TextView = TextView(this).apply {
        text = value; textSize = if (large) 20f else 16f; setTextColor(skin.text); setPadding(0, skin.dp(8), 0, skin.dp(8)); column.addView(this)
    }
    private fun action(value: String, primary: Boolean = false, block: () -> Unit): Button = Button(this).apply {
        text = value; skin.style(this, primary); setOnClickListener { block() }; column.addView(this, LinearLayout.LayoutParams(-1, -2).apply { bottomMargin = skin.dp(10) })
    }
    private fun openSetup(group: String = "") {
        if (isVoice) { stopVoice(); details.text = "No words recognized yet" }
        startActivity(Intent(this, SetupGuideActivity::class.java).putExtra("group", group).putExtra("dark", skin.dark).putExtra("returnToVoice", isVoice))
    }
    private fun voicePage() {
        label("See what your phone hears", true)

        label("Tap Start, then say “Audio Bodyguard, skip intro” or “Audio Bodyguard, skip recap.”")
        status = label("Microphone off", true)
        permissionSettingsButton = action("Open app settings") { openVoicePermissionSettings() }.apply { visibility = View.GONE }
        meter = InputMeter(this, skin.violet)
        column.addView(meter, LinearLayout.LayoutParams(-1, skin.dp(120)))
        levelText = label("No microphone samples yet")

        label("Recent recognized words · may change", true)
        details = label("No words recognized yet")
        label("Test player — this app only", true)
        label("These are test-player buttons in Audio Bodyguard only. No TV or streaming app is controlled.")
        demoStatus = label(if (!demoIntroAvailable && !demoRecapAvailable)
            "Test player paused — reset to prepare video again"
            else "Test player ready — nothing connected")
        demoIntroButton = action("Skip Intro") { pressDemo(OwnedSkipAction.SKIP_INTRO) }
            .apply { isEnabled = demoIntroAvailable }
        demoRecapButton = action("Skip Recap") { pressDemo(OwnedSkipAction.SKIP_RECAP) }
            .apply { isEnabled = demoRecapAvailable }
        val localPanel = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            visibility = View.GONE
        }
        action("? Local video trial") {
            localPanel.visibility = if (localPanel.visibility == View.VISIBLE) View.GONE else View.VISIBLE
        }
        column.addView(localPanel)
        localPanel.addView(TextView(this).apply {
            text = "An eight-second silent test clip with separate intro and recap sections. No external player is controlled."
            setTextColor(skin.text); textSize = 14f
        })
        fun localAction(title: String, action: OwnedSkipAction) {
            val button = Button(this)
            button.text = title; skin.style(button, false)
            button.setOnClickListener { prepareLocalVideo(action) }
            localPanel.addView(button)
        }
        localAction("Prepare intro video", OwnedSkipAction.SKIP_INTRO)
        localAction("Prepare recap video", OwnedSkipAction.SKIP_RECAP)
        if (finalTextFixtureEnabled) {
            // Debug/emulator-only controls; absent on production/physical phone runs.
            for ((title, selection) in listOf(
                "Fixture final Intro text (no audio)" to OwnedSkipAction.SKIP_INTRO,
                "Fixture final Recap text (no audio)" to OwnedSkipAction.SKIP_RECAP
            )) {
                localPanel.addView(Button(this).apply {
                    text = title; skin.style(this, false)
                    setOnClickListener { requestFinalTextFixture(selection) }
                })
            }
            localPanel.addView(Button(this).apply {
                text = "Fixture move playhead (no audio)"; skin.style(this, false)
                setOnClickListener { moveFinalTextFixturePlayhead() }
            })
        }
        localVideoStatus = TextView(this).apply {
            text = "Local video not prepared"; textSize = 16f; setTextColor(skin.text)
            setPadding(0, skin.dp(8), 0, skin.dp(8))
        }
        localPanel.addView(localVideoStatus)
        localVideo = VideoView(this).apply {
            setBackgroundColor(android.graphics.Color.BLACK)
        }
        localPanel.addView(localVideo, LinearLayout.LayoutParams(-1, skin.dp(112)))
        demoResetButton = action("Reset test player") { resetDemo() }
        recent = action("Recent sound checks") {
            if (visible && hasWindowFocus() && !isFinishing && !isDestroyed &&
                !running && recognizer == null && microphone.blocked) showRecentSoundChecks(this, skin)
        }.apply { visibility = View.GONE }
        startButton = action("Start voice check", primary = true) { if (running) stopVoice() else startVoice() }
        column.removeView(startButton)
        footer.addView(startButton, LinearLayout.LayoutParams(-1, -2))
        action("? Voice help") { skin.menu("Voice help", listOf(
            "Jump to voice steps" to { openSetup("voice") },
            "Clear words" to { stopVoice(); details.text = "No words recognized yet" }
        ), "Digital recognizer levels are not room loudness. A final recognized command can activate an available test-player button once. Check the result; no TV command is sent. Listening stops when you leave.") }
    }
    private fun startVoice() {
        if (!visible || !hasWindowFocus() || isFinishing) return
        stopVoice(); details.text = "No words recognized yet"
        if (showVoiceAudioUnavailable()) return
        if (checkSelfPermission(Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED) {
            permissionGuidance = false; permissionSettingsButton?.visibility = View.GONE
        }
        if (Build.VERSION.SDK_INT < 31) {
            status.text = "On-device speech recognition unavailable. No cloud fallback is used."; return
        }
        val supported = try { SpeechRecognizer.isOnDeviceRecognitionAvailable(this) } catch (_: Exception) { false }
        if (!supported) {
            status.text = "On-device speech recognition unavailable. No cloud fallback is used."; return
        }
        if (checkSelfPermission(Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
            permissionGuidance = true
            requestPermissions(arrayOf(Manifest.permission.RECORD_AUDIO), 41); return
        }
        val reservation = microphone.acquire()
        if (reservation == null) {
            if (!showVoiceAudioUnavailable()) status.text = MicrophoneAvailabilityGuidance.BUSY
            return
        }
        microphoneLease = reservation
        val token = voiceRun.start(SystemClock.elapsedRealtime())
        if (token == null) { stopVoice("The input clock is unavailable. Close and reopen this screen."); return }
        generation = token; lastLevelAt = 0
        val skipId = "voice-$token"
        if (!voiceSkipGate.start(skipId, demoSnapshot())) {
            stopVoice("Test-player session could not start. Tap Start to retry."); return
        }
        voiceSkipRunId = skipId
        demoResetButton?.isEnabled = false
        try {
            val service = SpeechRecognizer.createOnDeviceSpeechRecognizer(this); recognizer = service; running = true
            startButton.text = "Stop listening"; status.text = "Starting microphone…"
            service.setRecognitionListener(object : RecognitionListener {
                private fun valid() = validVoice(token)
                override fun onReadyForSpeech(params: Bundle?) { if (valid()) status.text = "Listening — on this phone, up to 30 seconds" }
                override fun onBeginningOfSpeech() { if (valid()) status.text = "Speech detected — words are provisional" }
                override fun onRmsChanged(rmsdB: Float) {
                    if (!valid()) return
                    if (!rmsdB.isFinite()) { stopVoice("Recognizer input level was invalid. Tap Start to retry."); return }
                    val now = SystemClock.elapsedRealtime()
                    if (now - lastLevelAt < 100) return
                    lastLevelAt = now
                    meter.add(((rmsdB + 2f) / 12f).coerceIn(0f, 1f))
                    levelText.text = "Recognizer input level: %.1f dB (not dB SPL)".format(rmsdB)
                }
                override fun onBufferReceived(buffer: ByteArray?) { /* No raw audio retained. */ }
                override fun onEndOfSpeech() { if (valid()) { status.text = "Finishing recognition…"; meter.clear(); levelText.text = "No live microphone samples" } }
                override fun onError(error: Int) { if (valid()) stopVoice(voiceErrorMessage(error)) }
                private fun words(results: Bundle?) { results?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)?.firstOrNull()?.let { details.text = boundedRecognizedWords(it) } }
                override fun onResults(results: Bundle?) {
                    if (valid()) {
                        val finalWords = results?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)?.firstOrNull()
                        words(results)
                        stopVoice(handleFinalDemoCommand(finalWords))
                    }
                }
                override fun onPartialResults(partialResults: Bundle?) { if (valid()) words(partialResults) }
                override fun onEvent(eventType: Int, params: Bundle?) {}
            })
            service.startListening(Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
                putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
                putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true)
                putExtra(RecognizerIntent.EXTRA_PREFER_OFFLINE, true)
                putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 1)
            })
            if (running) handler.post(voiceWatchdog)
        } catch (_: Exception) { stopVoice("Microphone could not start. Check permission and the installed speech service.") }
    }
    private fun voiceErrorMessage(error: Int): String {
        // Describe the service's reported result; never infer room silence,
        // change permission state, download a model or restart recognition.
        val guidance = when (error) {
            SpeechRecognizer.ERROR_AUDIO ->
                "Microphone input could not be read. Check microphone access, then tap Start."
            SpeechRecognizer.ERROR_SPEECH_TIMEOUT ->
                "No speech was detected. Tap Start and speak normally."
            SpeechRecognizer.ERROR_NO_MATCH ->
                "No words matched. Tap Start and try again."
            SpeechRecognizer.ERROR_RECOGNIZER_BUSY ->
                "The speech service is busy. Wait a moment, then tap Start."
            SpeechRecognizer.ERROR_INSUFFICIENT_PERMISSIONS ->
                "Speech access was denied. Check app permissions, then tap Start."
            SpeechRecognizer.ERROR_TOO_MANY_REQUESTS ->
                "Too many voice checks were requested. Wait a moment, then tap Start."
            SpeechRecognizer.ERROR_LANGUAGE_NOT_SUPPORTED ->
                "This language is not supported here. Try Live sound check for microphone levels."
            SpeechRecognizer.ERROR_LANGUAGE_UNAVAILABLE ->
                "Speech for this language is unavailable. Try Live sound check for microphone levels."
            else -> "Voice recognition stopped. Tap Start to try again."
        }
        return "$guidance Words may be incomplete."
    }
    private fun validVoice(token: Long): Boolean {
        if (!running || generation != token) return false
        if (voiceRun.accepts(token, SystemClock.elapsedRealtime(), visible && hasWindowFocus() && !isFinishing,
                checkSelfPermission(Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED)) return true
        val message = when (voiceRun.endReason) {
            VoiceInputRun.EndReason.timeLimit -> "30-second limit reached. Tap Start to try again."
            VoiceInputRun.EndReason.permission -> "Microphone permission was removed. Tap Start to check permission."
            VoiceInputRun.EndReason.clockInvalid -> "The input clock changed. Tap Start to try again."
            else -> "Microphone stopped when you left the voice check."
        }
        stopVoice(message)
        return false
    }
    /** Presentation only. A later explicit Start must still acquire native ownership. */
    private fun showVoiceAudioUnavailable(): Boolean {
        if (!isVoice || !::startButton.isInitialized || running || recognizer != null) return false
        val state = ForegroundAudioExclusion.process.state
        if (state == ForegroundAudioExclusion.State.AVAILABLE) {
            recent?.visibility = View.GONE
            if (availabilityGuidance) {
                availabilityGuidance = false
                status.text = "Microphone off"
            }
            return false
        }
        availabilityGuidance = true
        permissionGuidance = false
        permissionSettingsButton?.visibility = View.GONE
        status.text = if (state == ForegroundAudioExclusion.State.BLOCKED)
            MicrophoneAvailabilityGuidance.BLOCKED else MicrophoneAvailabilityGuidance.BUSY
        startButton.text = "Start voice check"
        startButton.isEnabled = state != ForegroundAudioExclusion.State.BLOCKED
        recent?.apply { visibility = if (state == ForegroundAudioExclusion.State.BLOCKED) View.VISIBLE else View.GONE; isEnabled = true }
        meter.clear(); lastLevelAt = 0; levelText.text = "No live microphone samples"
        return true
    }
    private fun refreshVoicePermissionGuidance() {
        if (!isVoice || !::status.isInitialized || isDestroyed || isFinishing) return
        if (showVoiceAudioUnavailable() || !permissionGuidance) return
        if (running || recognizer != null || microphone.blocked) {
            permissionSettingsButton?.visibility = View.GONE; return
        }
        val denied = checkSelfPermission(Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED
        meter.clear(); lastLevelAt = 0; levelText.text = "No live microphone samples"
        permissionSettingsButton?.visibility = if (denied) View.VISIBLE else View.GONE
        status.text = if (denied) microphoneDeniedMessage else "Permission granted. Tap Start when you are ready."
    }
    private fun openVoicePermissionSettings() {
        if (!visible || !hasWindowFocus() || !isVoice || running || recognizer != null ||
            isDestroyed || isFinishing) return
        if (showVoiceAudioUnavailable()) return
        if (checkSelfPermission(Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED) {
            refreshVoicePermissionGuidance(); return
        }
        stopVoice(); details.text = "No words recognized yet"
        if (microphone.blocked) return
        try {
            startActivity(Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS, Uri.fromParts("package", packageName, null)))
        } catch (_: RuntimeException) {
            status.text = "App settings could not open. In Android Settings, choose Apps, Audio Bodyguard Live Test, then Permissions and Microphone."
        }
    }
    private fun stopVoice(message: String = "Microphone off") {
        running = false; voiceRun.stop(); handler.removeCallbacks(voiceWatchdog)
        voiceSkipGate.stop(); voiceSkipRunId = null
        demoResetButton?.isEnabled = true
        var clean = true
        recognizer?.let { service ->
            recognizer = null
            // Destroy is still attempted if cancel throws; neither callback restarts input.
            try { service.cancel() } catch (_: Exception) { clean = false }
            try { service.destroy() } catch (_: Exception) { clean = false }
        }
        microphone.release(microphoneLease, cleanupSucceeded = clean); microphoneLease = null
        if (::startButton.isInitialized) {
            startButton.text = "Start voice check"; startButton.isEnabled = !microphone.blocked
            status.text = message
            meter.clear(); lastLevelAt = 0; levelText.text = "No live microphone samples"
            showVoiceAudioUnavailable()
        }
    }
    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<out String>, grantResults: IntArray) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == 41 && isVoice && ::status.isInitialized && !isDestroyed && !isFinishing && !running && recognizer == null) {
            permissionGuidance = true; refreshVoicePermissionGuidance()
        }
    }
    private fun photoPage() {
        val fromTutorial = intent.getBooleanExtra("fromTutorial", false)
        label("Find your TV details", true)
        label("Photograph your TV’s model label, About screen, or IP address row. Keep passwords out of the picture.")
        action("Take a TV photo", primary = true) { selectPhoto(camera = true) }
        action("Choose a photo") { selectPhoto(camera = false) }
        status = label("No photo selected", true)
        details = label("Brand: Not identified").apply { visibility = View.GONE }
        if (fromTutorial) {
            useBrand = action("Use brand and continue", primary = true) {
                photoBrand?.lowercase()?.let { id ->
                    setResult(RESULT_OK, Intent().putExtra("suggestedBrand", id)); finish()
                }
            }.apply { visibility = View.GONE }
        } else {
            photoAddressReview = label("").apply { visibility = View.GONE }
            usePhotoAddress = action("Use address in VIZIO check", primary = true) {
                val target = photoTarget ?: return@action
                if (!visible) return@action
                usePhotoAddress?.isEnabled = false
                if (!TVNetworkCheckActivity.openPhotoDraft(this, target, skin.dark)) {
                    usePhotoAddress?.isEnabled = true
                }
            }.apply { visibility = View.GONE }
        }
        photoExtra = label("Model: Not identified\nTV IP hint: Not identified").apply {
            visibility = View.GONE
        }
        label("Check the suggested details on your TV. A photo does not connect it. Choosing another picture clears these details.")
        action("? Photo help") {
            val options = buildList<Pair<String, () -> Unit>> {
                if (!fromTutorial) add("VIZIO V505M-K09 address pictures" to {
                    TVNetworkCheckActivity.showAddressPictures(this@InputAssistanceActivity, skin.dark)
                })
                add("Show photo details" to { photoExtra?.visibility = View.VISIBLE })
                add("Jump to illustrated setup guides" to { openSetup(photoBrand?.lowercase() ?: "") })
                add("Clear photo details" to { clearPhoto() })
            }
            skin.menu("Photo help", options, "Use About in your TV’s Settings; do not move a heavy TV. For an IP hint, photograph the Network screen’s IP address row, not Gateway or DNS. Keep TV and phone on the same home Wi-Fi. Text recognition stays on this phone; details clear on close.")
        }
    }

    private fun showPhotoTarget(target: LocalTVTarget?) {
        photoTarget = target
        val reviewVisibility = if (target == null) View.GONE else View.VISIBLE
        photoAddressReview?.apply {
            text = target?.let {
                "Address read from photo: ${it.address}\nCompare this address with your VIZIO TV’s network screen."
            }.orEmpty()
            visibility = reviewVisibility
        }
        usePhotoAddress?.visibility = reviewVisibility
    }

    private fun clearPhoto() {
        waitingForPhotoWork = false
        stopPhotoWatchdog()
        pendingPhoto = null; photoRun.clear(); cameraPhoto?.close(); cameraPhoto = null; photoBrand = null
        status.text = "No photo selected"; details.text = "Brand: Not identified"; details.visibility = View.GONE
        photoExtra?.text = "Model: Not identified\nTV IP hint: Not identified"; useBrand?.visibility = View.GONE
        showPhotoTarget(null)
    }
    private fun stopPhotoWatchdog() {
        photoWatchdog?.let { handler.removeCallbacks(it) }
        photoWatchdog = null; readingPhoto = null
    }
    private fun showPhotoEnd(token: PhotoReviewRun.Token) {
        val reason = photoRun.endReason(token) ?: return
        stopPhotoWatchdog(); cameraPhoto?.close(); cameraPhoto = null; photoBrand = null
        details.text = "Brand: Not identified"
        photoExtra?.text = "Model: Not identified\nTV IP hint: Not identified"; useBrand?.visibility = View.GONE
        showPhotoTarget(null)
        status.text = if (reason == PhotoReviewRun.EndReason.timeLimit)
            "Photo review timed out. Choose the picture again."
        else "Photo review ended. Choose the picture again."
    }
    private fun watchPhoto(token: PhotoReviewRun.Token) {
        stopPhotoWatchdog(); readingPhoto = token
        val watch = object : Runnable {
            override fun run() {
                if (isDestroyed || isFinishing) return
                if (!photoRun.isReading(token)) { showPhotoEnd(token); return }
                handler.postDelayed(this, 250)
            }
        }
        photoWatchdog = watch; handler.post(watch)
    }
    private fun acceptPhoto(token: PhotoReviewRun.Token): Boolean {
        if (isDestroyed || isFinishing) return false
        if (!photoRun.complete(token)) { showPhotoEnd(token); return false }
        waitingForPhotoWork = false; stopPhotoWatchdog(); return true
    }
    private fun showPhotoBusy() {
        waitingForPhotoWork = true
        status.text = "The previous photo is still finishing. Try again shortly."
        refreshPhotoAvailability()
    }
    private fun refreshPhotoAvailability() {
        if (!visible || isVoice || isDestroyed || isFinishing || !waitingForPhotoWork || photoWork.occupied) return
        waitingForPhotoWork = false
        status.text = "The previous photo has finished. Choose a photo."
    }
    private fun observePhotoWork() {
        photoObservation?.close()
        photoObservation = photoWork.observe { handler.post { refreshPhotoAvailability() } }
        // Catch completion while paused or between a busy check and registration.
        refreshPhotoAvailability()
    }
    private fun selectPhoto(camera: Boolean) {
        if (photoWork.occupied) {
            showPhotoBusy(); return
        }
        clearPhoto()
        // Never reuse a request code in this Activity: a late result must not
        // become the image belonging to a newer selection.
        if (nextPhotoRequestCode > 65_535) {
            status.text = "Close and reopen photo setup before choosing another picture."; return
        }
        val token = photoRun.select()
        try {
            val capture = if (camera) TVPhotoCapture.create(this) else null
            cameraPhoto = capture
            val request = PhotoRequest(nextPhotoRequestCode++, token, capture)
            pendingPhoto = request
            val source = capture?.intent()
                ?: Intent(Intent.ACTION_GET_CONTENT).apply { type = "image/*"; addCategory(Intent.CATEGORY_OPENABLE) }
            startActivityForResult(source, request.code)
        } catch (_: Exception) {
            pendingPhoto = null; photoRun.cancel(token); cameraPhoto?.close(); cameraPhoto = null
            status.text = if (camera) "Camera unavailable. Take a photo in your Camera app, then choose it below."
                else "No photo picker available. Use the instructions below."
        }
    }
    @Deprecated("Platform callback retained for API 26 compatibility")
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        val request = pendingPhoto ?: return
        if (requestCode != request.code) return
        pendingPhoto = null
        request.capture?.revokeAccess()
        if (resultCode != RESULT_OK) { photoRun.cancel(request.token); request.capture?.close(); cameraPhoto = null; return }
        val token = request.token
        if (isDestroyed || isFinishing) { request.capture?.close(); return }
        val work = photoWork.acquire()
        if (work == null) {
            photoRun.cancel(token); request.capture?.close(); cameraPhoto = null
            showPhotoBusy(); return
        }
        if (!photoRun.beginReading(token)) {
            try { request.capture?.close() } finally { photoWork.release(work) }
            showPhotoEnd(token); return
        }
        status.text = "Reading text on this phone…"
        watchPhoto(token)
        try { worker.execute {
            var decoded: Bitmap? = null
            var scanner: TextRecognizer? = null
            try {
                if (!photoRun.isReading(token)) return@execute
                val bitmap: Bitmap = run {
                    // Camera result data can be null. Only the reserved full-size
                    // output is eligible; never fall back to a result thumbnail.
                    val uri = request.capture?.uri ?: data?.data ?: throw IllegalArgumentException("No photo")
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
                        val decoded = contentResolver.openInputStream(uri).use { BitmapFactory.decodeStream(it, null, BitmapFactory.Options().apply { inSampleSize = sample }) } ?: throw IllegalArgumentException("Unreadable photo")
                        val orientation = try { contentResolver.openInputStream(uri).use { stream ->
                            if (stream == null) 1 else android.media.ExifInterface(stream).getAttributeInt(android.media.ExifInterface.TAG_ORIENTATION, 1)
                        } } catch (_: Exception) { 1 }
                        val transform = Matrix()
                        when (orientation) {
                            2 -> transform.setScale(-1f, 1f)
                            3 -> transform.setRotate(180f)
                            4 -> transform.setScale(1f, -1f)
                            5 -> { transform.setRotate(90f); transform.postScale(-1f, 1f) }
                            6 -> transform.setRotate(90f)
                            7 -> { transform.setRotate(-90f); transform.postScale(-1f, 1f) }
                            8 -> transform.setRotate(270f)
                        }
                        if (transform.isIdentity) decoded else Bitmap.createBitmap(decoded, 0, 0, decoded.width, decoded.height, transform, true).also { decoded.recycle() }
                    }
                }
                decoded = bitmap
                if (!photoRun.isReading(token)) return@execute
                val reader = TextRecognition.getClient(TextRecognizerOptions.DEFAULT_OPTIONS)
                scanner = reader
                val result = awaitPhoto(reader.process(InputImage.fromBitmap(bitmap, 0)))
                val text = boundedTVPhotoText(result.textBlocks.asSequence()
                    .flatMap { it.lines.asSequence() }.map { it.text })
                val hints = TVPhotoHints(text ?: "")
                runOnUiThread {
                    if (acceptPhoto(token)) {
                        details.text = "Brand: ${hints.brand ?: "Not identified"}"
                        details.visibility = if (hints.brand == null) View.GONE else View.VISIBLE
                        photoExtra?.text = "Model: ${hints.model ?: "Not identified"}\nTV IP hint: ${hints.address ?: "Not identified"}"
                        photoBrand = hints.brand
                        if (usePhotoAddress != null) showPhotoTarget(hints.vizioCheckTarget)
                        val choice = TutorialContent.choices["chooseTV"]?.firstOrNull { it.id == hints.brand?.lowercase() }
                        useBrand?.apply { this.text = "Use ${choice?.title ?: "brand"} and continue"; visibility = if (choice == null) View.GONE else View.VISIBLE }
                        status.text = when {
                            text == null -> "Photo text could not be reviewed. Choose a closer photo of the model or IP address row."
                            hints.brand == null && hints.model == null && hints.address == null ->
                                "No TV details found. Try a closer photo of the model label or IP address row."
                            else -> "Check these details. Text recognition can make mistakes. Nothing is connected."
                        }
                    }
                }
            } catch (_: Exception) {
                runOnUiThread { if (acceptPhoto(token)) status.text = "Photo could not be read. Choose a clear photo of the label or settings screen." }
            } finally {
                // View invalidation cannot settle provider, OCR or cleanup work.
                try { scanner?.close() } finally {
                    try { decoded?.recycle() } finally {
                        try { request.capture?.close() } finally { photoWork.release(work) }
                    }
                }
            }
        } } catch (_: java.util.concurrent.RejectedExecutionException) {
            try { request.capture?.close() } finally { photoWork.release(work) }
            photoRun.cancel(token); stopPhotoWatchdog()
            if (!isDestroyed && !isFinishing) status.text = "Photo could not start. Close and reopen photo setup."
        }
    }
    private fun <T> awaitPhoto(task: Task<T>): T {
        // Interruption is not proof that ML Kit returned. Wait for the same task;
        // never retry recognition or release its bitmap while it is still in use.
        var interrupted = false
        try {
            while (true) {
                try { return Tasks.await(task) }
                catch (_: InterruptedException) { interrupted = true }
            }
        } finally { if (interrupted) Thread.currentThread().interrupt() }
    }
    override fun onResume() {
        super.onResume(); visible = true
        usePhotoAddress?.isEnabled = true
        readingPhoto?.let { if (!photoRun.isReading(it)) showPhotoEnd(it) }
        if (isVoice) refreshVoicePermissionGuidance() else observePhotoWork()
    }
    override fun onWindowFocusChanged(hasFocus: Boolean) {
        super.onWindowFocusChanged(hasFocus)
        if (!hasFocus && isVoice && running) { stopVoice("Microphone stopped when you left the voice check."); details.text = "No words recognized yet" }
        if (hasFocus && visible && isVoice) refreshVoicePermissionGuidance()
    }
    override fun onPause() {
        visible = false
        photoObservation?.close(); photoObservation = null
        if (isVoice) { stopVoice(); suspendLocalVideo(); if (::details.isInitialized) details.text = "No words recognized yet" }
        super.onPause()
    }
    override fun onDestroy() { stopVoice(); stopPhotoWatchdog(); photoObservation?.close(); photoObservation = null; handler.removeCallbacksAndMessages(null); pendingPhoto = null; photoRun.clear(); cameraPhoto?.close(); cameraPhoto = null; worker.shutdown(); super.onDestroy() }
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
        for (index in values.indices) {
            val i = 40 - values.size + index
            val h = maxOf(2f, height * values[index])
            canvas.drawRoundRect(i * step, (height - h) / 2, i * step + maxOf(1f, step - 2), (height + h) / 2, 2f, 2f, paint)
        }
    }
}
