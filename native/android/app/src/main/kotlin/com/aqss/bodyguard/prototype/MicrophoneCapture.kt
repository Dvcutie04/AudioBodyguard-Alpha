package com.aqss.bodyguard.prototype

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.media.*
import android.os.Build
import android.os.SystemClock
import com.aqss.nativefeedback.PcmInputLevel
import com.aqss.nativefeedback.ForegroundMicrophoneGate
import com.aqss.nativefeedback.SoundCheckEnd
import com.aqss.nativefeedback.SoundCheckRecaps
import java.util.concurrent.atomic.AtomicBoolean
import java.util.concurrent.atomic.AtomicReference

internal data class InputFrame(val receivedAtMs: Long, val level: PcmInputLevel)

/** One bounded foreground capture. The worker alone releases its recorder and raw buffer. */
internal class MicrophoneCapture(context: Context) {
    private val gate = ForegroundMicrophoneGate.process
    private val recaps = SoundCheckRecaps.process
    private var recapToken: SoundCheckRecaps.Token? = null
    private data class End(val reason: SoundCheckEnd, val message: String)
    private var lease: ForegroundMicrophoneGate.Lease? = null
    private val app = context.applicationContext
    private val launched = AtomicBoolean(false)
    private val lock = Any()
    private var recorder: AudioRecord? = null
    private val cancelled = AtomicBoolean(false)
    private val latest = AtomicReference<InputFrame?>(null)
    private val result = AtomicReference<End?>(null)
    val completed = AtomicBoolean(false)
    @Volatile var cleanupFailed = false
        private set
    @Volatile var description = "Input details pending"
        private set

    fun takeLatest(): InputFrame? = latest.getAndSet(null)
    val stopReason: String get() = result.get()?.message ?: "Microphone stopped"
    fun noteDisplayedInput() { recaps.observe(recapToken) }
    private fun end(reason: SoundCheckEnd, message: String) { result.compareAndSet(null, End(reason, message)) }

    fun start() {
        if (!launched.compareAndSet(false, true)) return
        val reservation = gate.acquire()
        if (reservation == null) {
            cleanupFailed = gate.blocked
            result.set(End(if (gate.blocked) SoundCheckEnd.CLEANUP_FAILED else SoundCheckEnd.INPUT_UNAVAILABLE, if (gate.blocked) "Microphone cleanup failed. Force stop this app in Android Settings before trying again."
                else "Another microphone tool is using or closing the input. Stop it, then tap Start."))
            completed.set(true)
            return
        }
        lease = reservation
        recapToken = recaps.begin()
        try { Thread({ capture() }, "aqss-microphone-check").start() }
        catch (_: Exception) {
            end(SoundCheckEnd.COULD_NOT_START, "Microphone worker could not start. Tap Start to retry.")
            recaps.finish(recapToken, SoundCheckEnd.COULD_NOT_START)
            gate.release(lease, cleanupSucceeded = true); lease = null
            completed.set(true)
        }
    }

    fun stop(reason: SoundCheckEnd, message: String) {
        end(reason, message)
        cancelled.set(true)
        latest.set(null)
        // Stop can interrupt a blocking read; release waits for that read's worker to exit.
        synchronized(lock) { try { recorder?.stop() } catch (_: Exception) {} }
    }

    private fun capture() {
        var owned: AudioRecord? = null
        var samples: ShortArray? = null
        var recordingCallback: AudioManager.AudioRecordingCallback? = null
        try {
            if (cancelled.get()) return
            if (!hasPermission()) { end(SoundCheckEnd.PERMISSION_CHANGED, "Microphone permission is unavailable."); return }
            val rate = listOf(16000, 48000).firstOrNull {
                AudioRecord.getMinBufferSize(it, AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT) > 0
            } ?: throw IllegalStateException("No supported input format")
            val frames = rate / 10
            val minimum = AudioRecord.getMinBufferSize(rate, AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT)
            require(minimum in 1..1_048_576)
            val manager = app.getSystemService(AudioManager::class.java)
            val unprocessed = manager.getProperty(AudioManager.PROPERTY_SUPPORT_AUDIO_SOURCE_UNPROCESSED) == "true"
            val source = if (unprocessed) MediaRecorder.AudioSource.UNPROCESSED else MediaRecorder.AudioSource.VOICE_RECOGNITION
            val builder = AudioRecord.Builder().setAudioSource(source).setAudioFormat(
                AudioFormat.Builder().setSampleRate(rate).setChannelMask(AudioFormat.CHANNEL_IN_MONO)
                    .setEncoding(AudioFormat.ENCODING_PCM_16BIT).build()
            ).setBufferSizeInBytes(maxOf(minimum, frames * 4))
            if (Build.VERSION.SDK_INT >= 30) builder.setPrivacySensitive(true)
            val audio = builder.build()
            owned = audio
            check(audio.state == AudioRecord.STATE_INITIALIZED)
            if (Build.VERSION.SDK_INT >= 29) {
                val callback = object : AudioManager.AudioRecordingCallback() {
                    override fun onRecordingConfigChanged(configs: MutableList<AudioRecordingConfiguration>) {
                        if (cancelled.get() || completed.get()) return
                        if (configs.any { it.clientAudioSessionId == audio.audioSessionId && it.isClientSilenced }) {
                            stop(SoundCheckEnd.INPUT_BLOCKED, "Android blocked microphone input. Check microphone privacy and other recording apps.")
                        }
                    }
                }
                audio.registerAudioRecordingCallback(app.mainExecutor, callback)
                recordingCallback = callback
            }
            synchronized(lock) {
                if (cancelled.get()) return
                recorder = audio
                audio.startRecording()
            }
            check(audio.recordingState == AudioRecord.RECORDSTATE_RECORDING)
            samples = ShortArray(frames)
            val started = SystemClock.elapsedRealtime()
            var lastData = started
            var routeId: Int? = null
            while (!cancelled.get()) {
                if (SystemClock.elapsedRealtime() - started >= 30_000) {
                    end(SoundCheckEnd.TIME_LIMIT, "30-second check finished. Tap Start for another check."); break
                }
                if (!hasPermission()) {
                    end(SoundCheckEnd.PERMISSION_CHANGED, "Microphone permission was removed. Tap Start to check permission."); break
                }
                val count = audio.read(samples, 0, frames, AudioRecord.READ_BLOCKING)
                if (cancelled.get()) break
                if (count < 0) {
                    end(SoundCheckEnd.INPUT_UNAVAILABLE, "Microphone input stopped (code $count). Tap Start to try again."); break
                }
                val now = SystemClock.elapsedRealtime()
                if (count == 0) {
                    if (now - lastData >= 2000) { end(SoundCheckEnd.NO_SAMPLES, "No microphone samples arrived. Tap Start to retry."); break }
                    Thread.sleep(20) // Prevent spinning if an OEM returns zero from a blocking read.
                    continue
                }
                if (Build.VERSION.SDK_INT >= 29 && audio.activeRecordingConfiguration?.isClientSilenced == true) {
                    end(SoundCheckEnd.INPUT_BLOCKED, "Android blocked microphone input. Check microphone privacy and other recording apps."); break
                }
                val route = audio.routedDevice
                if (routeId != null && route?.id != routeId) {
                    end(SoundCheckEnd.ROUTE_CHANGED, "Microphone route changed. Tap Start to check the new input."); break
                }
                routeId = route?.id
                val routeText = if (route?.type == AudioDeviceInfo.TYPE_BUILTIN_MIC) "Built-in microphone" else "Android-selected microphone"
                description = "$routeText · $rate Hz · mono\n${if (unprocessed) "Unprocessed input requested" else "Voice-recognition input requested"}\nInput processing and gain can vary by phone."
                val level = PcmInputLevel.measure(samples, count)
                samples.fill(0)
                lastData = now
                latest.set(InputFrame(now, level)) // One summary slot: no growing UI message queue.
            }
        } catch (_: SecurityException) {
            end(SoundCheckEnd.PERMISSION_CHANGED, "Microphone access was blocked. Check permission and microphone privacy.")
        } catch (_: Exception) {
            end(SoundCheckEnd.INPUT_UNAVAILABLE, "Microphone could not run. Close other recording apps, then tap Start to retry.")
        } finally {
            cancelled.set(true)
            latest.set(null)
            synchronized(lock) {
                recorder = null
                owned?.let { audio ->
                    if (Build.VERSION.SDK_INT >= 29) recordingCallback?.let {
                        try { audio.unregisterAudioRecordingCallback(it) } catch (_: Exception) {}
                    }
                    try { audio.stop() } catch (_: Exception) {}
                    try { audio.release() } catch (_: Exception) {
                        cleanupFailed = true
                        result.set(End(SoundCheckEnd.CLEANUP_FAILED, "Microphone cleanup failed. Force stop this app in Android Settings before trying again."))
                    }
                }
            }
            samples?.fill(0)
            recaps.finish(recapToken, result.get()?.reason ?: SoundCheckEnd.INPUT_UNAVAILABLE)
            gate.release(lease, cleanupSucceeded = !cleanupFailed); lease = null
            completed.set(true)
        }
    }

    private fun hasPermission() = app.checkSelfPermission(Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED
}
