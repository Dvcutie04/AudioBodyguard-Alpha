package com.aqss.bodyguard.prototype

import android.app.Activity
import android.app.AlertDialog
import android.content.Intent
import android.content.ActivityNotFoundException
import android.net.ConnectivityManager
import android.net.NetworkCapabilities
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.os.SystemClock
import android.provider.Settings
import android.text.InputType
import android.text.Editable
import android.text.TextWatcher
import android.view.View
import android.view.Gravity
import android.view.WindowInsets
import android.view.WindowManager
import android.view.inputmethod.InputMethodManager
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import android.widget.Toast
import com.aqss.nativefeedback.LocalTVTarget
import com.aqss.nativefeedback.TVNetworkOutcome
import com.aqss.nativefeedback.TVNetworkResult
import com.aqss.nativefeedback.TVNetworkRunner
import com.aqss.nativefeedback.TVProbeSocket
import com.aqss.nativefeedback.TVTrialOutcome
import com.aqss.nativefeedback.TVTrialReport
import java.lang.ref.WeakReference
import java.net.InetAddress
import java.net.InetSocketAddress
import java.net.Proxy
import java.net.Socket
import java.util.UUID

private object TVNetworkChecks { val runner = TVNetworkRunner() }

/** An explicitly started TCP reachability check, not a TV pairing or controller. */
class TVNetworkCheckActivity : Activity() {
    private lateinit var skin: InterfaceTheme
    private lateinit var address: EditText
    private lateinit var result: TextView
    private lateinit var start: Button
    private lateinit var review: Button
    private var lastOutcome: TVTrialOutcome? = null
    private var reportDialog: AlertDialog? = null
    private var reportShare: Button? = null
    private var token: Long? = null
    private var cancelRequested = false
    private var visible = false
    private var help: AlertDialog? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        val dark = intent.getBooleanExtra("dark", true)
        setTheme(if (dark) R.style.AQSSMidnightTheme else R.style.AQSSReadOnlyTheme)
        super.onCreate(savedInstanceState)
        window.setSoftInputMode(WindowManager.LayoutParams.SOFT_INPUT_ADJUST_RESIZE)
        skin = InterfaceTheme(this, dark)
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL; setPadding(skin.dp(20), skin.dp(20), skin.dp(20), skin.dp(20))
            setBackgroundColor(skin.background)
            isFocusableInTouchMode = true
        }
        val header = LinearLayout(this).apply { gravity = Gravity.CENTER_VERTICAL }
        header.addView(words("VIZIO network check", 24f), LinearLayout.LayoutParams(0, -2, 1f))
        header.addView(button("Back") { finish() }); root.addView(header)
        val content = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        content.addView(words("Phone → Wi-Fi → TV", 20f))
        content.addView(words("Enter the IP address shown in your VIZIO TV’s network settings."))
        address = EditText(this).apply {
            hint = "TV IP address"; contentDescription = "TV IP address"; tag = "tv-network-address"
            inputType = InputType.TYPE_CLASS_PHONE; maxLines = 1; setTextColor(skin.text); setHintTextColor(skin.muted)
            isSaveEnabled = false
        }
        content.addView(address)
        content.addView(words("Check contacts only this address on Wi-Fi. It sends no TV command.", 15f))
        result = words(IDLE).apply { tag = "tv-network-result" }; content.addView(result)
        content.addView(words(LocalTVTarget.BOUNDARY, 15f))
        start = button("Check this address", primary = true) {
            getSystemService(InputMethodManager::class.java)?.hideSoftInputFromWindow(address.windowToken, 0)
            if (token == null) begin() else stop()
        }
        content.addView(start)
        review = button("Review test result") { reviewResult() }.apply { visibility = View.GONE }
        content.addView(review)
        content.addView(button("? Help with this check") { showHelp() })
        address.addTextChangedListener(object : TextWatcher {
            override fun beforeTextChanged(s: CharSequence?, start: Int, count: Int, after: Int) {}
            override fun onTextChanged(s: CharSequence?, start: Int, before: Int, count: Int) {
                if (token == null) { setOutcome(null); result.text = IDLE }
            }
            override fun afterTextChanged(s: Editable?) {}
        })
        root.addView(ScrollView(this).apply { addView(content) }, LinearLayout.LayoutParams(-1, 0, 1f))
        if (Build.VERSION.SDK_INT >= 30) {
            window.setDecorFitsSystemWindows(false)
            root.setOnApplyWindowInsetsListener { view, insets ->
                val bars = insets.getInsets(WindowInsets.Type.systemBars() or WindowInsets.Type.displayCutout())
                val keyboard = insets.getInsets(WindowInsets.Type.ime())
                view.setPadding(skin.dp(20) + bars.left, skin.dp(12) + bars.top,
                    skin.dp(20) + bars.right, skin.dp(12) + maxOf(bars.bottom, keyboard.bottom))
                insets
            }
        }
        setContentView(root)
        root.requestApplyInsets()
    }

    override fun onResume() {
        super.onResume(); visible = true
        intent.getStringExtra(PHOTO_DRAFT_TICKET)?.let { ticket ->
            intent.removeExtra(PHOTO_DRAFT_TICKET)
            takePhotoDraft(ticket)?.let { address.setText(it.address) }
        }
        if (reportDialog?.isShowing == true) reportShare?.isEnabled = true
    }
    override fun onPause() {
        visible = false; stop(); token = null; address.text.clear(); result.text = IDLE
        address.isEnabled = true; start.text = "Check this address"; start.isEnabled = true
        help?.dismiss(); help = null
        super.onPause()
    }
    override fun onDestroy() {
        reportDialog?.dismiss(); reportDialog = null; reportShare = null
        help?.dismiss(); help = null
        super.onDestroy()
    }

    private fun begin() {
        setOutcome(null)
        val target = LocalTVTarget.parse(address.text.toString())
        if (target == null) { result.text = LocalTVTarget.INVALID_ADDRESS; setOutcome(TVTrialOutcome.ADDRESS_REJECTED); return }
        val manager = applicationContext.getSystemService(ConnectivityManager::class.java)
        val network = manager?.activeNetwork
        val capabilities = network?.let { manager.getNetworkCapabilities(it) }
        if (network == null || capabilities == null || !capabilities.hasTransport(NetworkCapabilities.TRANSPORT_WIFI) ||
            !capabilities.hasCapability(NetworkCapabilities.NET_CAPABILITY_NOT_VPN)) {
            result.text = "Connect to your home Wi-Fi before checking. A VPN or another route may prevent this check."
            setOutcome(TVTrialOutcome.WIFI_REQUIRED); return
        }
        val owner = WeakReference(this)
        val main = Handler(Looper.getMainLooper())
        val id = TVNetworkChecks.runner.start(target, {
            object : TVProbeSocket {
                private val socket = Socket(Proxy.NO_PROXY)
                override fun connect(target: LocalTVTarget, port: Int, timeoutMillis: Int) {
                    network.bindSocket(socket)
                    socket.connect(InetSocketAddress(InetAddress.getByAddress(target.addressBytes()), port), timeoutMillis)
                }
                override fun close() { socket.close() }
            }
        }) { finished, value -> main.post { owner.get()?.completed(finished, value) } }
        if (id == null) {
            result.text = "A previous network check is still closing or needs an app restart. Try again after it finishes."
            setOutcome(TVTrialOutcome.CHECK_UNAVAILABLE); return
        }
        token = id; cancelRequested = false; address.isEnabled = false; start.text = "Stop check"
        result.text = "Checking the address you entered…"
    }

    private fun stop() {
        cancelRequested = true
        token?.let { TVNetworkChecks.runner.cancel(it) }
        if (token != null) { start.isEnabled = false; result.text = "Stopping the network check…" }
    }

    private fun completed(id: Long, value: TVNetworkResult) {
        if (!visible || token != id || isFinishing || isDestroyed) return
        token = null; address.isEnabled = true; start.text = "Check this address"; start.isEnabled = true
        val outcome = if (cancelRequested && value.outcome != TVNetworkOutcome.CLEANUP_UNRESOLVED)
            TVNetworkOutcome.STOPPED else value.outcome
        setOutcome(when (outcome) {
            TVNetworkOutcome.REACHABLE -> TVTrialOutcome.SERVICE_ANSWERED_UNVERIFIED
            TVNetworkOutcome.NOT_REACHED -> TVTrialOutcome.NO_SERVICE_RESPONSE
            TVNetworkOutcome.STOPPED -> TVTrialOutcome.CHECK_STOPPED
            TVNetworkOutcome.CLEANUP_UNRESOLVED -> TVTrialOutcome.CLEANUP_UNRESOLVED
        })
        result.text = when (outcome) {
            TVNetworkOutcome.REACHABLE -> "A network service answered. TV pairing is still needed."
            TVNetworkOutcome.NOT_REACHED -> "Could not reach the service. Check home Wi-Fi and TV power, then try again."
            TVNetworkOutcome.STOPPED -> "Check stopped. Start again only when you are ready."
            TVNetworkOutcome.CLEANUP_UNRESOLVED -> "Network cleanup is unresolved. Close and restart the app before checking again."
        }
    }

    private fun setOutcome(value: TVTrialOutcome?) {
        lastOutcome = value
        review.visibility = if (value == null) View.GONE else View.VISIBLE
    }

    private fun reviewResult() {
        val outcome = lastOutcome ?: return
        if (!visible || token != null || isFinishing || isDestroyed || !hasWindowFocus() || reportDialog?.isShowing == true) return
        val frozen = try {
            TVTrialReport.capture(installedAppBuildDetails(this), outcome, System.currentTimeMillis())
        } catch (_: IllegalArgumentException) {
            Toast.makeText(this, "The installed build or phone clock could not be included. No report was prepared.", Toast.LENGTH_LONG).show()
            return
        }
        getSystemService(InputMethodManager::class.java)?.hideSoftInputFromWindow(address.windowToken, 0)
        address.clearFocus()
        address.text.clear(); setOutcome(null); result.text = IDLE
        val column = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(skin.dp(16), skin.dp(12), skin.dp(16), skin.dp(12))
            setBackgroundColor(skin.background)
        }
        val share = button("Share test result", primary = true) {}
        val dialog = object : AlertDialog(this) {
            override fun onWindowFocusChanged(hasFocus: Boolean) {
                super.onWindowFocusChanged(hasFocus)
                if (hasFocus && visible && isShowing) share.isEnabled = true
            }
        }
        val header = LinearLayout(this).apply { gravity = Gravity.CENTER_VERTICAL }
        header.addView(words("Review test result", 22f), LinearLayout.LayoutParams(0, -2, 1f))
        header.addView(button("Back") { dialog.dismiss() }); column.addView(header)
        column.addView(ScrollView(this).apply {
            addView(words(frozen.text, 16f).apply { tag = "tv-network-report-preview"; setTextIsSelectable(true) })
        }, LinearLayout.LayoutParams(-1, 0, 1f))
        column.addView(words(TVTrialReport.NOTICE, 14f))
        column.addView(share, LinearLayout.LayoutParams(-1, -2))
        dialog.setView(column)
        dialog.setOnDismissListener {
            if (reportDialog === dialog) { reportDialog = null; reportShare = null }
        }
        share.setOnClickListener {
            if (!visible || isFinishing || isDestroyed || reportDialog !== dialog || !dialog.isShowing ||
                dialog.window?.decorView?.hasWindowFocus() != true || !share.isEnabled) return@setOnClickListener
            share.isEnabled = false
            val send = Intent(Intent.ACTION_SEND).apply { type = "text/plain"; putExtra(Intent.EXTRA_TEXT, frozen.text) }
            try { startActivity(Intent.createChooser(send, null)) }
            catch (error: RuntimeException) {
                share.isEnabled = true
                if (error !is ActivityNotFoundException && error !is SecurityException) throw error
                Toast.makeText(this, "Sharing is unavailable. You can read the report shown here.", Toast.LENGTH_LONG).show()
            }
        }
        reportDialog = dialog; reportShare = share; dialog.show()
        val display = resources.displayMetrics
        dialog.window?.setLayout(minOf(display.widthPixels - skin.dp(24), skin.dp(680)), (display.heightPixels * .85f).toInt())
    }

    private fun words(value: String, size: Float = 18f) = TextView(this).apply {
        text = value; textSize = size; setTextColor(skin.text)
        setPadding(0, skin.dp(10), 0, skin.dp(10))
    }
    private fun button(title: String, primary: Boolean = false, action: () -> Unit) = Button(this).apply {
        text = title; skin.style(this, primary); setOnClickListener { action() }
    }
    private fun showHelp() {
        help = AlertDialog.Builder(this).setTitle("Help with this check")
            .setMessage("Use the same home Wi-Fi for phone and TV. Guest Wi-Fi or device isolation can prevent contact; this check cannot diagnose your router’s policy.\n\nThis tries TCP ports 7345 and 9000 for up to four seconds each, on one private IPv4 address. These are SmartCast research candidates, not a guarantee for every VIZIO model. An answer proves only service reachability at that moment.\n\nThe address and result clear when you leave the foreground. No command, audio, scan or DNS lookup is performed. Permission restrictions can also cause a failed check.\n\nReview test result removes the address and opens a historical copy. You can then choose Share. It contains the app build and a fixed result description, without TV addresses, Wi-Fi names, passwords, photos or audio. Nothing is sent automatically.")
            .setPositiveButton("Done", null)
            .setNeutralButton("Open app settings") { _, _ ->
                startActivity(Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS, Uri.parse("package:$packageName")))
            }.create().also { it.show() }
    }

    companion object {
        private const val IDLE = "Ready to check the address you enter."
        private const val PHOTO_DRAFT_TICKET = "vizioPhotoDraftTicket"
        private const val PHOTO_DRAFT_MILLIS = 10_000L
        private data class PhotoDraft(val ticket: String, val target: LocalTVTarget, val expiresAt: Long)
        // Only the opaque ticket travels through the Activity intent.
        private var photoDraft: PhotoDraft? = null

        internal fun openPhotoDraft(activity: Activity, target: LocalTVTarget, dark: Boolean): Boolean {
            val ticket = UUID.randomUUID().toString()
            photoDraft = PhotoDraft(ticket, target, SystemClock.elapsedRealtime() + PHOTO_DRAFT_MILLIS)
            Handler(Looper.getMainLooper()).postDelayed({ discardPhotoDraft(ticket) }, PHOTO_DRAFT_MILLIS)
            val intent = Intent(activity, TVNetworkCheckActivity::class.java)
                .putExtra("dark", dark).putExtra(PHOTO_DRAFT_TICKET, ticket)
            try {
                activity.startActivity(intent)
            } catch (error: RuntimeException) {
                discardPhotoDraft(ticket)
                if (error !is ActivityNotFoundException && error !is SecurityException) throw error
                Toast.makeText(activity, "Could not open the VIZIO network check.", Toast.LENGTH_SHORT).show()
                return false
            }
            return true
        }

        private fun takePhotoDraft(ticket: String): LocalTVTarget? {
            val draft = photoDraft?.takeIf { it.ticket == ticket } ?: return null
            photoDraft = null
            return draft.target.takeIf { SystemClock.elapsedRealtime() < draft.expiresAt }
        }

        private fun discardPhotoDraft(ticket: String) {
            if (photoDraft?.ticket == ticket) photoDraft = null
        }
    }
}
