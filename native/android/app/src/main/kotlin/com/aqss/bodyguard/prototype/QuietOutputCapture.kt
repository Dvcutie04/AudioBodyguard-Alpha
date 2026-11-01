package com.aqss.bodyguard.prototype

import android.content.Context
import android.media.AudioAttributes
import android.media.AudioFocusRequest
import android.media.AudioFormat
import android.media.AudioManager
import android.media.AudioRouting
import android.media.AudioTrack
import android.os.Build
import android.os.Handler
import android.os.Looper
import android.os.SystemClock
import com.aqss.nativefeedback.*
import java.util.concurrent.atomic.AtomicBoolean

/** All native track operations run on one private worker. No UI/activity is retained. */
internal class QuietOutputCapture(context: Context) {
    private val app = context.applicationContext
    private val foreground = AtomicBoolean(true)
    private val launched = AtomicBoolean(false)
    val control = QuietOutputControl()
    val completed = AtomicBoolean(false)
    private val core = QuietOutputCheck(ForegroundAudioExclusion.process, control,
        { AndroidQuietOutputBackend(app, control) }, { SystemClock.elapsedRealtime() },
        { foreground.get() }, { Thread.sleep(it) })
    val result: QuietOutputResult? get() = core.result
    fun start() {
        if (!launched.compareAndSet(false, true)) return
        try { Thread({ try { core.execute() } finally { completed.set(true) } }, "aqss-quiet-output-check").start() }
        catch (_: Exception) { control.stop(QuietStop.BACKEND_FAILED); completed.set(true) }
    }
    fun stop(reason: QuietStop) { control.stop(reason) }
    fun setForeground(value: Boolean) {
        foreground.set(value)
        if (!value) control.stop(QuietStop.INACTIVE)
    }
}

/** The callbacks carry only a retired control context; they never inspect their routing argument. */
internal class QuietOutputNotices(private val events: QuietOutputEvents) :
    AudioManager.OnAudioFocusChangeListener, AudioRouting.OnRoutingChangedListener {
    override fun onAudioFocusChange(focusChange: Int) { events.focusChanged(focusChange) }
    override fun onRoutingChanged(router: AudioRouting) { events.routeChanged() }
}

internal class AndroidQuietOutputBackend(context: Context, control: QuietOutputControl) : QuietOutputBackend {
    private val manager = checkNotNull(context.getSystemService(AudioManager::class.java))
    private val main = Handler(Looper.getMainLooper())
    private val events = QuietOutputEvents(control)
    private val notices = QuietOutputNotices(events)
    private val attributes = AudioAttributes.Builder().setUsage(AudioAttributes.USAGE_MEDIA)
        .setContentType(AudioAttributes.CONTENT_TYPE_UNKNOWN).build()
    private val request = AudioFocusRequest.Builder(AudioManager.AUDIOFOCUS_GAIN_TRANSIENT)
        .setAudioAttributes(attributes).setAcceptsDelayedFocusGain(false).setWillPauseWhenDucked(true)
        .setOnAudioFocusChangeListener(notices, main).build()
    private var rawTrack: AudioTrack? = null
    override var track: QuietOutputTrack? = null
        private set
    override fun minimumBufferBytes() = AudioTrack.getMinBufferSize(48000,
        AudioFormat.CHANNEL_OUT_MONO, AudioFormat.ENCODING_PCM_16BIT)
    override fun requestFocus() = manager.requestAudioFocus(request)
    override fun open(bufferBytes: Int) {
        check(rawTrack == null)
        val audio = AudioTrack.Builder().setAudioAttributes(attributes)
            .setAudioFormat(AudioFormat.Builder().setSampleRate(48000)
                .setChannelMask(AudioFormat.CHANNEL_OUT_MONO).setEncoding(AudioFormat.ENCODING_PCM_16BIT).build())
            .setTransferMode(AudioTrack.MODE_STREAM).setBufferSizeInBytes(bufferBytes).build()
        rawTrack = audio
        track = AndroidQuietOutputTrack(audio, notices, main)
    }
    override fun retireCallbacks() { events.retire() }
    override fun abandonFocus() = manager.abandonAudioFocusRequest(request)
}

internal class AndroidQuietOutputTrack(private val audio: AudioTrack,
    private val notices: QuietOutputNotices, private val main: Handler) : QuietOutputTrack {
    override fun format() = QuietOutputFormat(audio.state == AudioTrack.STATE_INITIALIZED,
        audio.sampleRate, audio.channelCount, audio.audioFormat == AudioFormat.ENCODING_PCM_16BIT,
        audio.bufferSizeInFrames, audio.bufferCapacityInFrames)
    override fun zeroGain() = audio.setVolume(0f)
    override fun watchRoute() { audio.addOnRoutingChangedListener(notices, main) }
    override fun play() { audio.play() }
    override fun write(samples: ShortArray, offset: Int, count: Int) =
        audio.write(samples, offset, count, AudioTrack.WRITE_NON_BLOCKING)
    override fun routes(): QuietOutputRoutes {
        val plural = Build.VERSION.SDK_INT >= 36
        if (audio.playState != AudioTrack.PLAYSTATE_PLAYING) return QuietOutputRoutes.unavailable(plural)
        return if (Build.VERSION.SDK_INT >= 36) {
            val routes = audio.routedDevices
            QuietOutputRoutes.from(routes.take(16).map { it.type }, routes.size, true)
        } else {
            val route = audio.routedDevice
            if (route == null) QuietOutputRoutes.unavailable(false)
            else QuietOutputRoutes.from(listOf(route.type), 1, false)
        }
    }
    override fun pause() { audio.pause() }
    override fun flush() { audio.flush() }
    override fun unwatchRoute() { audio.removeOnRoutingChangedListener(notices) }
    override fun release() { audio.release() }
}
