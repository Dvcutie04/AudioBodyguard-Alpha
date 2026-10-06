package com.aqss.bodyguard.prototype

import android.app.Activity
import android.app.AlertDialog
import android.content.Intent
import android.graphics.Canvas
import android.graphics.Paint
import android.graphics.Path
import android.graphics.Typeface
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.view.Gravity
import android.view.View
import android.view.WindowInsets
import android.widget.Button
import android.widget.LinearLayout
import android.widget.ProgressBar
import android.widget.ScrollView
import android.widget.TextView
import android.window.OnBackInvokedCallback
import android.window.OnBackInvokedDispatcher
import com.aqss.nativefeedback.SetupContent
import com.aqss.nativefeedback.SetupRoute
import com.aqss.nativefeedback.SetupStep
import java.util.ArrayDeque

/** Local illustrated instructions. Finishing a guide changes no connection state. */
class SetupGuideActivity : Activity() {
    companion object {
        const val COMPLETED_ROUTE = "completedPictureRoute"
        const val COMPLETED_TV_ROUTE = "completedTVPictureRoute"
        const val SELECTED_SYSTEM = "selectedSetupSystem"
        private val repeatedPictureNotes = setOf(
            "Use your real device. This picture is an illustration.",
            "Finishing this guide does not connect Audio Bodyguard or activate protection.",
            "Use the numbered highlight on your real device. This illustration does not confirm a connection to Audio Bodyguard."
        )
    }
    private lateinit var skin: InterfaceTheme
    private lateinit var root: LinearLayout
    private lateinit var header: LinearLayout
    private lateinit var content: LinearLayout
    private lateinit var controls: LinearLayout
    private lateinit var scroll: ScrollView
    private lateinit var progressLabel: TextView
    private lateinit var progressBar: ProgressBar
    private lateinit var backButton: Button
    private lateinit var nextButton: Button
    private var renderVersion = 0
    private var groupId = ""
    private var routeId: String? = null
    private var index = -1
    private var mismatch = false
    private var detailsExpanded = false
    private var pickerExpanded = false
    private var referencesExpanded = false
    private val history = ArrayDeque<Bundle>()
    private var completedTVRoute: String? = null
    private var selectedSystem: String? = null
    private var backCallback: OnBackInvokedCallback? = null
    private val group get(): com.aqss.nativefeedback.SetupGroup? {
        val original = SetupContent.groups.firstOrNull { it.id == groupId } ?: return null
        if (groupId == "phone") return original.copy(routes = original.routes.filter { it != "phone_iphone" }, primaryRoutes = original.primaryRoutes.filter { it != "phone_iphone" })
        val tv = SetupContent.groups.firstOrNull { it.id == (selectedSystem ?: intent.getStringExtra("deviceGroup")) }
        if (groupId !in listOf("google", "alexa", "both") || tv == null) return original
        val routes = original.routes.filter { it in tv.routes }
        val vizio = listOf("vizio_google", "vizio_alexa").filter { it in routes }
        val primary = if (vizio.isEmpty()) original.primaryRoutes.filter { it in routes } else vizio
        val preferred = listOf("vidaa_google", "vidaa_alexa", "google_setup", "sony_new", "fire_alexa").filter { it in routes }
        return original.copy(title = "${original.title} • ${tv.title}", routes = routes, primaryRoutes = primary.ifEmpty { (preferred.ifEmpty { routes }).take(3) })
    }
    private val route get() = SetupContent.routes.firstOrNull { it.id == routeId }
    private val phoneRoute get() = when (Build.MANUFACTURER.lowercase()) { "samsung" -> "phone_galaxy"; "google" -> "phone_pixel"; else -> null }
    private fun startingRoute(): String? = when {
        groupId == "voice" -> "voice"
        groupId == "phone" -> phoneRoute
        platforms.isNotEmpty() -> null
        else -> group?.primaryRoutes?.singleOrNull()
    }
    private val platforms get() = when (groupId) {
        "tcl" -> listOf("Roku TV" to "tcl_roku", "Google TV / Android TV" to "tcl_google", "Fire TV" to "tcl_fire")
        "hisense" -> listOf("Roku TV" to "hisense_roku", "Google TV / Android TV" to "hisense_google", "VIDAA" to "hisense_vidaa", "Fire TV" to "hisense_fire")
        "philips" -> listOf("Google TV / Android TV" to "philips_google", "Roku TV" to "philips_roku")
        "insignia" -> listOf("Roku TV" to "insignia_roku", "Fire TV" to "insignia_fire")
        else -> emptyList()
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        val dark = intent.getBooleanExtra("dark", true)
        setTheme(if (dark) R.style.AQSSMidnightTheme else R.style.AQSSReadOnlyTheme)
        super.onCreate(savedInstanceState)
        skin = InterfaceTheme(this, dark)
        groupId = (savedInstanceState?.getString("group") ?: intent.getStringExtra("group") ?: "")
            .takeIf { id -> SetupContent.groups.any { it.id == id } } ?: ""
        selectedSystem = savedInstanceState?.getString(SELECTED_SYSTEM) ?: intent.getStringExtra("deviceGroup")
        val companion = if (savedInstanceState == null && groupId == "phone") SetupContent.groups.firstOrNull {
            it.id == selectedSystem && "roku_phone" in it.routes && it.primaryRoutes.isNotEmpty() && it.primaryRoutes.all { route -> route in listOf("roku_network", "roku_model") }
        } else null
        if (companion != null) groupId = companion.id
        routeId = if (savedInstanceState == null) { if (companion != null) "roku_phone" else startingRoute() } else savedInstanceState.getString("route")?.takeIf { group?.routes?.contains(it) == true }
        completedTVRoute = savedInstanceState?.getString("completedTVRoute")?.takeIf { it in listOf("roku_network", "roku_model") }
        completedTVRoute?.let { setResult(RESULT_OK, Intent().putExtra(COMPLETED_TV_ROUTE, it)) }
        index = if (savedInstanceState == null && groupId == "voice") 0 else (savedInstanceState?.getInt("index", -1) ?: -1).takeIf { it == -1 || route?.steps?.indices?.contains(it) == true } ?: -1
        mismatch = savedInstanceState?.getBoolean("mismatch", false) ?: false
        detailsExpanded = savedInstanceState?.getBoolean("details") ?: false
        pickerExpanded = savedInstanceState?.getBoolean("picker") ?: false
        referencesExpanded = savedInstanceState?.getBoolean("references") ?: false
        @Suppress("DEPRECATION")
        val savedHistory = savedInstanceState?.getParcelableArrayList<Bundle>("setupHistory")
        savedHistory?.takeLast(100)?.let { history.addAll(it) }
        root = column().apply { setBackgroundColor(skin.background) }
        header = column().apply { setPadding(dp(16), dp(12), dp(16), dp(12)); setBackgroundColor(skin.surface) }
        content = column().apply { setPadding(dp(20), dp(20), dp(20), dp(20)) }
        controls = column().apply { setPadding(dp(16), dp(12), dp(16), dp(12)); setBackgroundColor(skin.surface) }
        scroll = ScrollView(this).apply { addView(content); clipToPadding = true }
        val topRow = LinearLayout(this).apply { gravity = Gravity.CENTER_VERTICAL }
        progressLabel = TextView(this).apply { textSize = 17f; setTextColor(skin.text); setTypeface(null, Typeface.BOLD) }
        topRow.addView(progressLabel, LinearLayout.LayoutParams(0, -2, 1f))
        topRow.addView(roseButton(this, skin, if (intent.getBooleanExtra("returningToTutorial", false)) "Back to Tutorial" else "Close") { finish() }); header.addView(topRow)
        progressBar = ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal).apply {
            progressTintList = android.content.res.ColorStateList.valueOf(skin.accent)
            importantForAccessibility = View.IMPORTANT_FOR_ACCESSIBILITY_NO
        }
        header.addView(progressBar, LinearLayout.LayoutParams(-1, dp(6)).apply { topMargin = dp(10) })
        val footer = LinearLayout(this)
        backButton = button("Back") { back() }
        nextButton = button("Next", primary = true) { advance() }
        footer.addView(backButton, LinearLayout.LayoutParams(-2, -2).apply { marginEnd = dp(12) })
        footer.addView(nextButton, LinearLayout.LayoutParams(0, -2, 1f))
        controls.addView(footer)
        root.addView(header); root.addView(scroll, LinearLayout.LayoutParams(-1, 0, 1f)); root.addView(controls)
        setContentView(root)
        @Suppress("DEPRECATION")
        window.decorView.systemUiVisibility = if (dark) 0 else View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR or View.SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR
        @Suppress("DEPRECATION")
        window.statusBarColor = skin.background
        @Suppress("DEPRECATION")
        window.navigationBarColor = skin.surface
        if (Build.VERSION.SDK_INT >= 30) {
            window.setDecorFitsSystemWindows(false)
            root.setOnApplyWindowInsetsListener { v, insets ->
                val bars = insets.getInsets(WindowInsets.Type.systemBars() or WindowInsets.Type.displayCutout())
                v.setPadding(bars.left, bars.top, bars.right, bars.bottom); insets
            }
        }
        if (Build.VERSION.SDK_INT >= 33) {
            backCallback = OnBackInvokedCallback { back() }.also { onBackInvokedDispatcher.registerOnBackInvokedCallback(OnBackInvokedDispatcher.PRIORITY_DEFAULT, it) }
        }
        render()
    }
    private fun dp(v: Int) = skin.dp(v)
    private fun column() = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
    private fun words(box: LinearLayout, value: String, size: Float = 16f, color: Int = skin.text, bold: Boolean = false): TextView {
        val view = TextView(this).apply {
            text = value; textSize = size; setTextColor(color); setPadding(0, 0, 0, dp(12))
            if (bold) setTypeface(null, Typeface.BOLD)
        }
        box.addView(view, LinearLayout.LayoutParams(-1, -2)); return view
    }
    private fun button(title: String, primary: Boolean = false, action: () -> Unit) = Button(this).apply {
        text = title; skin.style(this, primary); setOnClickListener { action() }
    }
    private fun action(box: LinearLayout, title: String, primary: Boolean = false, block: () -> Unit) {
        box.addView(button(title, primary, block).apply { gravity = Gravity.START or Gravity.CENTER_VERTICAL }, LinearLayout.LayoutParams(-1, -2).apply { bottomMargin = dp(10) })
    }
    private fun chooseGroup(id: String) {
        remember(); groupId = id; routeId = startingRoute(); index = if (id == "voice") 0 else -1; mismatch = false; detailsExpanded = false; pickerExpanded = false; referencesExpanded = false; render()
    }
    private fun location() = Bundle().apply {
        putString("group", groupId); putString("route", routeId); putInt("index", index); putBoolean("mismatch", mismatch)
        putBoolean("details", detailsExpanded); putBoolean("picker", pickerExpanded); putBoolean("references", referencesExpanded)
    }
    private fun remember() {
        if (history.size >= 100) history.removeFirst()
        history.addLast(location())
    }
    private fun chooseRoute(id: String) {
        remember(); routeId = id; index = -1; mismatch = false; detailsExpanded = false; referencesExpanded = false; render()
    }
    private fun resumeIndex(route: SetupRoute): Int? = getSharedPreferences("aqss-presentation", MODE_PRIVATE).getInt("setup-progress-${route.id}", -1).takeIf { route.id != "voice" && it in route.steps.indices }
    private fun saveProgress(route: SetupRoute, value: Int?) {
        if (value != null && resumeIndex(route) == value) return
        val edit = getSharedPreferences("aqss-presentation", MODE_PRIVATE).edit()
        if (value == null) edit.remove("setup-progress-${route.id}") else edit.putInt("setup-progress-${route.id}", value)
        edit.apply()
    }
    private fun render(preserveScroll: Boolean = false) {
        val oldScroll = if (preserveScroll) scroll.scrollY else 0
        val version = ++renderVersion
        if (groupId !in listOf("", "google", "alexa", "both", "neither", "phone", "voice")) selectedSystem = groupId
        setResult(RESULT_OK, resultPayload())
        content.removeAllViews()
        val route = route
        val step = route?.steps?.getOrNull(index)?.let { original ->
            if (original.screen == "App Store or Google Play") original.copy(screen = "Android • Google Play", instruction = original.instruction.replace("App Store or Google Play", "Google Play")) else original
        }
        if (route != null && route.id != "voice" && step != null && !mismatch) saveProgress(route, index)
        progressLabel.text = if (route != null && index >= 0) "Step ${index + 1} of ${route.steps.size}" else "Illustrated setup"
        progressBar.visibility = if (route != null && index >= 0) View.VISIBLE else View.GONE
        if (route != null && index >= 0) { progressBar.max = route.steps.size; progressBar.setProgress(index + 1, false) }
        val heading = words(content, if (mismatch) "Find the right screen" else step?.title ?: route?.title ?: group?.title ?: "Choose your TV or app", 28f, bold = true).apply {
            if (Build.VERSION.SDK_INT >= 28) isAccessibilityHeading = true
            accessibilityLiveRegion = View.ACCESSIBILITY_LIVE_REGION_POLITE
        }
        when {
            mismatch -> mismatchContent(route)
            route != null && step != null -> {
                words(content, when (step.surface) { "tv" -> "On your TV · use the remote"; "both" -> "Your TV + your phone"; else -> "On your phone" }, 15f, skin.accent, true)
                words(content, step.instruction, 16f, bold = true)
                content.addView(if (route.id == "roku_network" || route.id == "roku_model") rokuIllustration(step, index + 1, route.id) else if (route.id == "philips_voice_remote" && index in 1..2) profileIllustration(step, index + 1) else illustration(step, index + 1, route.id == "vizio_walmart" && index == 2), LinearLayout.LayoutParams(-1, -2).apply { bottomMargin = dp(18) })
                action(content, if (detailsExpanded) "Hide help" else "Need help?") { detailsExpanded = !detailsExpanded; render(true) }
                if (detailsExpanded) {
                    if (step.note !in repeatedPictureNotes) words(content, step.note, color = skin.muted)
                    action(content, "My screen looks different") { remember(); mismatch = true; detailsExpanded = false; referencesExpanded = false; render() }
                    action(content, if (referencesExpanded) "Hide reference links" else "Reference links") { referencesExpanded = !referencesExpanded; render(true) }
                    if (referencesExpanded) sources(route)
                }
            }
            route != null -> intro(route)
            platforms.isNotEmpty() -> {
                words(content, "Choose the name on your TV’s home screen.", color = skin.muted)
                for ((name, id) in platforms) {
                    content.addView(button(name) { chooseGroup(id) }.apply {
                        setCompoundDrawablesWithIntrinsicBounds(InterfaceSymbol(skin, "tv", skin.accent), null, null, null)
                        compoundDrawablePadding = dp(12); gravity = Gravity.START or Gravity.CENTER_VERTICAL; minHeight = dp(64)
                    }, LinearLayout.LayoutParams(-1, -2).apply { bottomMargin = dp(12) })
                }
                action(content, if (detailsExpanded) "Hide help" else "Need help?") { detailsExpanded = !detailsExpanded; render(true) }
                if (detailsExpanded) {
                    words(content, "Match the name on your TV’s Home screen. If you’re unsure, use the identification pictures.", color = skin.muted)
                    action(content, "Help identify my TV") { chooseRoute("identify") }
                }
            }
            group != null -> {
                val selectedGroup = group!!
                words(content, if (selectedGroup.routes.isEmpty()) "No documented route for this combination. Choose the system shown on your TV." else "Start here. Follow one picture at a time.", color = skin.muted)
                if (selectedGroup.routes.isEmpty()) action(content, "Choose another TV or app") { chooseGroup("") }
                selectedGroup.primaryRoutes.forEach { id -> SetupContent.routes.firstOrNull { it.id == id }?.let { guide ->
                    action(content, if (id == "roku_network") "Start TV setup" else guide.title, selectedGroup.primaryRoutes.size == 1) { chooseRoute(id) }
                } }
                if (selectedGroup.routes.any { it !in selectedGroup.primaryRoutes }) action(content, if (pickerExpanded) "Hide other options" else "Other setup options") { pickerExpanded = !pickerExpanded; render(true) }
                if (pickerExpanded) selectedGroup.routes.filter { it !in selectedGroup.primaryRoutes }.forEach { id -> SetupContent.routes.firstOrNull { it.id == id }?.let { guide -> action(content, guide.title) { chooseRoute(id) } } }
            }
            else -> {
                words(content, "Choose a name to start the pictures.", color = skin.muted)
                SetupContent.groups.filter { it.id !in listOf("both", "neither") && !it.id.contains("_") }.forEach { choice -> action(content, choice.title) { chooseGroup(choice.id) } }
            }
        }
        backButton.visibility = if (group != null || route != null || history.isNotEmpty()) View.VISIBLE else View.GONE
        backButton.text = if (mismatch) "Return to step" else "Back"
        nextButton.visibility = if (route != null && !mismatch) View.VISIBLE else View.GONE
        if (route != null && !mismatch) nextButton.text = if (index < 0) {
            if (resumeIndex(route) == null) { if (route.id == "roku_phone") "Start part two" else "Start guide" } else "Resume guide"
        } else if (index == route.steps.lastIndex) {
            if (route.id == "voice") "Open Voice check" else if (route.id in listOf("roku_network", "roku_model")) "Finish part one" else if (route.id == "roku_phone") "Finish part two" else "Finish guide"
        } else "Next"
        scroll.post {
            // Ignore callbacks for a replaced step or an Activity that is closing.
            if (version == renderVersion && !isFinishing && !isDestroyed) {
                scroll.scrollTo(0, oldScroll)
                if (!preserveScroll) heading.sendAccessibilityEvent(android.view.accessibility.AccessibilityEvent.TYPE_VIEW_FOCUSED)
            }
        }
    }
    private fun advance() {
        val route = route ?: return
        if (mismatch || isFinishing) return
        if (index == route.steps.lastIndex) {
            if (route.id in listOf("roku_network", "roku_model")) {
                remember()
                saveProgress(route, null); completedTVRoute = route.id
            setResult(RESULT_OK, resultPayload())
                routeId = "roku_phone"; index = -1; detailsExpanded = false; referencesExpanded = false; render(); return
            }
            if (route.id == "voice" && !intent.getBooleanExtra("returnToVoice", false)) startActivity(Intent(this, InputAssistanceActivity::class.java).putExtra("mode", "voice").putExtra("dark", skin.dark))
            saveProgress(route, null)
            if (route.id != "voice") setResult(RESULT_OK, resultPayload().putExtra(COMPLETED_ROUTE, route.id))
            finish()
        } else { remember(); index = if (index < 0) resumeIndex(route) ?: 0 else index + 1; detailsExpanded = false; referencesExpanded = false; render() }
    }
    private fun intro(route: SetupRoute) {
        words(content, if (route.id.startsWith("phone_")) "Have your phone and home Wi-Fi password ready." else if (route.id == "roku_phone") "Keep your phone and TV on the same Wi-Fi." else if (route.steps.first().surface == "tv") "Have your TV remote ready." else "Have your phone and TV ready.")
        words(content, "${route.steps.size} pictures. One step at a time.", 18f, skin.accent)
        words(content, route.appliesTo, 13f, skin.muted)
        resumeIndex(route)?.let { saved -> words(content, "Continue at picture ${saved + 1}.", color = skin.accent) }
        action(content, if (detailsExpanded) "Hide help" else "Need help?") { detailsExpanded = !detailsExpanded; render(true) }
        if (detailsExpanded) {
            if (!route.id.startsWith("phone_")) action(content, "Phone Wi-Fi pictures") { chooseGroup("phone") }
            if ((group?.routes?.size ?: 0) > 1) action(content, "Other setup options") {
                remember(); routeId = null; index = -1; mismatch = false; detailsExpanded = false; pickerExpanded = true; referencesExpanded = false; render()
            }
            words(content, "Use the official setup screens for passwords and approvals.", color = skin.muted)
            if (route.id in listOf("roku_network", "roku_model")) action(content, "I’m already in Settings") { remember(); index = 2; detailsExpanded = false; referencesExpanded = false; render() }
            if (resumeIndex(route) != null) action(content, "Start from the beginning") { remember(); saveProgress(route, null); index = 0; detailsExpanded = false; render() }
            words(content, if (route.models.isEmpty()) "Menu-family guide · compare with your device." else "Documented model examples: ${route.models.joinToString()}", color = skin.muted)
            words(content, "Labels, layout and services can differ by country, software and language. Compare each picture with your own screen.", color = skin.muted)
            action(content, "My screen looks different") { remember(); mismatch = true; detailsExpanded = false; referencesExpanded = false; render() }
            action(content, if (referencesExpanded) "Hide reference links" else "Reference links") { referencesExpanded = !referencesExpanded; render(true) }
            if (referencesExpanded) sources(route)
        }
    }
    private fun resultPayload() = Intent().putExtra(SELECTED_SYSTEM, selectedSystem).putExtra(COMPLETED_TV_ROUTE, completedTVRoute)
    private fun sources(route: SetupRoute) {
        words(content, "Manufacturer references", 18f, bold = true)
        route.sources.forEach { id -> SetupContent.sources.firstOrNull { it.id == id }?.let { source ->
            words(content, source.title, color = skin.muted)
            action(content, "Open reference in browser") {
                try { startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(source.url))) }
                catch (_: android.content.ActivityNotFoundException) { AlertDialog.Builder(this).setTitle("Open official instructions").setMessage(source.url).setPositiveButton("Close", null).show() }
            }
        } }
    }
    private fun mismatchContent(route: SetupRoute?) {
        words(content, "Choose the name or menu that matches your device.")
        action(content, "Choose another model or menu") { remember(); routeId = null; index = -1; mismatch = false; pickerExpanded = true; detailsExpanded = false; render() }
        action(content, "Choose another TV or app") { chooseGroup("") }
        if (route != null) {
            action(content, if (detailsExpanded) "Hide help" else "Need help?") { detailsExpanded = !detailsExpanded; render(true) }
            if (detailsExpanded) { words(content, route.appliesTo); sources(route) }
        }
    }
    private fun rokuIllustration(step: SetupStep, number: Int, routeId: String): View {
        val box = column().apply { setPadding(dp(14), dp(14), dp(14), dp(14)); background = skin.shape(skin.raised, 18)
            importantForAccessibility = View.IMPORTANT_FOR_ACCESSIBILITY_YES
            contentDescription = "Roku picture $number. Left menu and right panel. Highlighted: ${step.items[step.focus]}. ${step.instruction}" }
        words(box, "Picture $number · Roku menu layout", 12f, skin.muted)
        if (number == 1) {
            box.addView(SetupActionPicture(this, skin, "tv", "home"), LinearLayout.LayoutParams(-1, dp(80)))
            words(box, "Press the Home button on your TV remote", 15f, skin.accent)
            return box
        }
        val blue = android.graphics.Color.rgb(5, 56, 145)
        val panel = column().apply { setPadding(dp(12), dp(12), dp(12), dp(12)); background = skin.shape(blue, 10); importantForAccessibility = View.IMPORTANT_FOR_ACCESSIBILITY_NO_HIDE_DESCENDANTS }
        words(panel, step.screen, 18f, android.graphics.Color.WHITE, true)
        val columns = LinearLayout(this).apply { gravity = Gravity.TOP }
        val left = column(); val right = column()
        columns.addView(left, LinearLayout.LayoutParams(0, -2, 1f).apply { marginEnd = dp(8) }); columns.addView(right, LinearLayout.LayoutParams(0, -2, 1f)); panel.addView(columns)
        val model = routeId == "roku_model"
        fun row(parent: LinearLayout, label: String, selected: Boolean) {
            parent.addView(TextView(this).apply {
                text = if (selected) "$number → $label" else label; textSize = 12f
                setPadding(dp(6), dp(7), dp(6), dp(7)); setTextColor(if (selected) android.graphics.Color.BLACK else android.graphics.Color.WHITE)
                background = skin.shape(if (selected) android.graphics.Color.WHITE else blue, 3)
                if (selected) setTypeface(null, Typeface.BOLD)
            }, LinearLayout.LayoutParams(-1, -2).apply { bottomMargin = dp(4) })
        }
        val names = if (number == 2) listOf("Home", "Settings", "Streaming Store") else if (model) listOf("Accessibility", "Audio", "Home screen", "System", "Power") else listOf("Network", "Remotes & devices", "Theme", "Display type", "TV inputs")
        names.forEach { row(left, it, if (number == 2) it == "Settings" else number == 3 && it == (if (model) "System" else "Network")) }
        if (number == 5) step.items.forEachIndexed { i, item -> row(right, item, i == step.focus) }
        else if (number >= 3) (if (model) listOf("About", "Power", "System update") else listOf("About", "Check connection", "Set up connection", "Bandwidth saver")).forEach { row(right, it, number == 4 && it == "About") }
        else row(right, "App tiles", false)
        box.addView(panel)
        words(box, if (number == 5) "Read the highlighted field on your TV" else "Use the remote arrows, then press Right", 13f, skin.accent)
        return box
    }

    private fun profileIllustration(step: SetupStep, number: Int): View {
        val box = column().apply {
            setPadding(dp(14), dp(14), dp(14), dp(14)); background = skin.shape(skin.raised, 18)
            contentDescription = "Picture $number. Profile icon at upper right. Highlighted: ${step.items[step.focus]}. ${step.instruction}"
            importantForAccessibility = View.IMPORTANT_FOR_ACCESSIBILITY_YES
        }
        words(box, "Picture $number · upper-right profile menu", 13f, skin.muted)
        val screen = column().apply { setPadding(dp(12), dp(12), dp(12), dp(12)); background = skin.shape(skin.surface, 10); importantForAccessibility = View.IMPORTANT_FOR_ACCESSIBILITY_NO_HIDE_DESCENDANTS }
        val top = LinearLayout(this).apply { gravity = Gravity.CENTER_VERTICAL }
        top.addView(TextView(this).apply { text = "Google TV"; textSize = 16f; setTextColor(skin.text) }, LinearLayout.LayoutParams(0, -2, 1f))
        top.addView(TextView(this).apply { text = if (number == 2) "2 → Profile" else "Profile"; textSize = 13f; setPadding(dp(8), dp(10), dp(8), dp(10)); setTextColor(if (number == 2) skin.controlText else skin.text); background = skin.shape(if (number == 2) skin.control else skin.raised, 8) })
        screen.addView(top)
        val body = LinearLayout(this).apply { gravity = Gravity.TOP }
        val home = column(); words(home, "For you · Apps", 12f, skin.muted); words(home, "▣   ▣   ▣", 24f, skin.outline); words(home, "TV home content", 12f, skin.muted)
        body.addView(home, LinearLayout.LayoutParams(0, -2, 1f))
        if (number == 3) {
            val menu = column().apply { setPadding(dp(8), dp(8), dp(8), dp(8)); background = skin.shape(skin.raised, 8) }
            words(menu, "Your account", 12f, skin.muted)
            menu.addView(TextView(this).apply { text = "3 → Settings"; textSize = 14f; setTypeface(null, Typeface.BOLD); setPadding(dp(8), dp(10), dp(8), dp(10)); setTextColor(skin.controlText); background = skin.shape(skin.control, 8) })
            body.addView(menu, LinearLayout.LayoutParams(0, -2, 1f))
        }
        screen.addView(body); box.addView(screen); words(box, "Use the remote arrows, then OK", 13f, skin.accent)
        return box
    }

    private fun illustration(step: SetupStep, number: Int, showsTVCode: Boolean): View {
        val screenOnTV = step.surface == "tv" || showsTVCode
        val box = column().apply {
            setPadding(dp(14), dp(14), dp(14), dp(14)); background = skin.shape(skin.raised, 22)
            importantForAccessibility = View.IMPORTANT_FOR_ACCESSIBILITY_YES
            contentDescription = "Illustration $number. ${if (showsTVCode) "TV screen with code; scan it with the phone camera" else step.surface}: ${step.screen}. Highlighted: ${step.items[step.focus]}. Action: ${step.action}. ${step.instruction}"
        }
        words(box, "Illustration", 11f, skin.muted, true).importantForAccessibility = View.IMPORTANT_FOR_ACCESSIBILITY_NO
        if (step.surface == "both") box.addView(SetupActionPicture(this, skin, "both", step.action), LinearLayout.LayoutParams(-1, dp(64)))
        val screen = column().apply { setPadding(dp(12), dp(12), dp(12), dp(12)); background = skin.shape(skin.surface, if (screenOnTV) 12 else 26, true); importantForAccessibility = View.IMPORTANT_FOR_ACCESSIBILITY_NO_HIDE_DESCENDANTS }
        box.addView(screen, LinearLayout.LayoutParams(-1, -2).apply { if (step.surface == "phone") { marginStart = dp(10); marginEnd = dp(10) } })
        if (!screenOnTV) words(screen, "9:41                         ● ▰", 10f, skin.muted)
        words(screen, step.screen, 17f, bold = true)
        step.items.forEachIndexed { i, item ->
            val row = LinearLayout(this).apply {
                gravity = Gravity.CENTER_VERTICAL; setPadding(dp(10), dp(10), dp(10), dp(10)); minimumHeight = dp(48)
                background = skin.shape(if (i == step.focus) skin.control else skin.raised, 9, true)
            }
            val ink = if (i == step.focus) skin.controlText else skin.muted
            row.addView(TextView(this).apply { text = if (i == step.focus) number.toString() else "○"; textSize = 14f; setTypeface(null, Typeface.BOLD); setTextColor(ink); gravity = Gravity.CENTER }, LinearLayout.LayoutParams(dp(30), -2))
            row.addView(TextView(this).apply { text = item; textSize = 15f; setTextColor(ink); if (i == step.focus) setTypeface(null, Typeface.BOLD) }, LinearLayout.LayoutParams(0, -2, 1f))
            row.addView(TextView(this).apply { text = if (i == step.focus) "←" else "›"; textSize = 20f; setTextColor(ink) }, LinearLayout.LayoutParams(dp(22), -2))
            screen.addView(row, LinearLayout.LayoutParams(-1, -2).apply { bottomMargin = dp(8) })
        }
        if (screenOnTV) {
            box.addView(View(this).apply { setBackgroundColor(skin.outline) }, LinearLayout.LayoutParams(dp(14), dp(12)).apply { gravity = Gravity.CENTER })
            box.addView(View(this).apply { background = skin.shape(skin.outline, 4) }, LinearLayout.LayoutParams(dp(90), dp(4)).apply { gravity = Gravity.CENTER })
        } else screen.addView(View(this).apply { background = skin.shape(skin.muted, 4) }, LinearLayout.LayoutParams(dp(70), dp(4)).apply { gravity = Gravity.CENTER; topMargin = dp(8) })
        box.addView(SetupActionPicture(this, skin, if (step.surface == "both") "phone" else step.surface, step.action), LinearLayout.LayoutParams(-1, dp(64)).apply { topMargin = dp(8) })
        return box
    }
    private fun back() {
        val previous = history.pollLast() ?: run { finish(); return }
        groupId = previous.getString("group") ?: ""; routeId = previous.getString("route"); index = previous.getInt("index", -1); mismatch = previous.getBoolean("mismatch")
        detailsExpanded = previous.getBoolean("details"); pickerExpanded = previous.getBoolean("picker"); referencesExpanded = previous.getBoolean("references")
        render()
    }
    @Deprecated("Compatibility for Android 12 and earlier")
    override fun onBackPressed() { back() }
    override fun onSaveInstanceState(outState: Bundle) {
        outState.putAll(location()); outState.putString("completedTVRoute", completedTVRoute); outState.putString(SELECTED_SYSTEM, selectedSystem); outState.putParcelableArrayList("setupHistory", ArrayList(history)); super.onSaveInstanceState(outState)
    }
    override fun onDestroy() {
        if (Build.VERSION.SDK_INT >= 33) backCallback?.let { onBackInvokedDispatcher.unregisterOnBackInvokedCallback(it) }
        super.onDestroy()
    }
}

/** Pictograms show the physical device and gesture without depending on a language. */
internal class SetupActionPicture(activity: Activity, private val skin: InterfaceTheme, private val surface: String, private val action: String) : View(activity) {
    private val paint = Paint(Paint.ANTI_ALIAS_FLAG)
    init { importantForAccessibility = IMPORTANT_FOR_ACCESSIBILITY_NO }
    override fun onDraw(c: Canvas) {
        super.onDraw(c)
        c.save(); val scale = minOf(width / 210f, height / 80f); c.translate((width - 210 * scale) / 2, (height - 80 * scale) / 2); c.scale(scale, scale)
        paint.color = skin.violet; paint.style = Paint.Style.STROKE; paint.strokeWidth = 2.5f; paint.strokeCap = Paint.Cap.ROUND
        if (surface == "both") {
            c.drawRoundRect(10f, 18f, 84f, 62f, 6f, 6f, paint); c.drawLine(47f, 62f, 47f, 70f, paint); c.drawLine(30f, 70f, 64f, 70f, paint)
        } else {
            c.drawRoundRect(29f, 4f, 70f, 76f, 12f, 12f, paint)
            if (surface == "tv") {
                c.drawCircle(49.5f, 47f, 15f, paint); c.drawCircle(49.5f, 47f, 5f, paint)
                c.drawLine(40f, 18f, 49f, 11f, paint); c.drawLine(49f, 11f, 58f, 18f, paint); c.drawLine(42f, 18f, 42f, 25f, paint); c.drawLine(56f, 18f, 56f, 25f, paint); c.drawLine(42f, 25f, 56f, 25f, paint)
            } else { c.drawLine(42f, 11f, 57f, 11f, paint); c.drawLine(43f, 68f, 56f, 68f, paint) }
        }
        c.drawLine(91f, 40f, 115f, 40f, paint); c.drawLine(108f, 33f, 115f, 40f, paint); c.drawLine(108f, 47f, 115f, 40f, paint)
        paint.style = Paint.Style.FILL; paint.color = skin.control; c.drawRoundRect(130f, 10f, 201f, 70f, 14f, 14f, paint)
        paint.style = Paint.Style.STROKE; paint.color = skin.controlText
        when {
            surface == "both" -> { c.drawRoundRect(153f, 17f, 179f, 63f, 5f, 5f, paint); c.drawLine(161f, 57f, 171f, 57f, paint) }
            action == "home" -> { val p = Path(); p.moveTo(148f, 38f); p.lineTo(165f, 23f); p.lineTo(182f, 38f); p.moveTo(152f, 35f); p.lineTo(152f, 56f); p.lineTo(178f, 56f); p.lineTo(178f, 35f); c.drawPath(p, paint) }
            action == "settings" -> { c.drawCircle(165f, 40f, 12f, paint); c.drawCircle(165f, 40f, 4f, paint); for (i in 0..7) { c.save(); c.rotate(i * 45f, 165f, 40f); c.drawLine(165f, 24f, 165f, 28f, paint); c.restore() } }
            action == "type" -> { c.drawRoundRect(144f, 26f, 187f, 54f, 4f, 4f, paint); for (y in listOf(33f, 41f)) for (x in listOf(151f, 160f, 169f, 178f)) c.drawPoint(x, y, paint); c.drawLine(154f, 48f, 177f, 48f, paint) }
            action == "scan" -> { for ((x,y) in listOf(147f to 23f, 184f to 23f, 147f to 57f, 184f to 57f)) { c.drawLine(x, y, x + if (x < 160) 8f else -8f, y, paint); c.drawLine(x,y,x,y + if (y < 40) 8f else -8f, paint) }; c.drawCircle(165f, 40f, 8f, paint) }
            action == "speak" -> { c.drawRoundRect(160f, 23f, 171f, 44f, 5f, 5f, paint); c.drawArc(153f, 26f, 178f, 51f, 0f, 180f, false, paint); c.drawLine(165f, 51f, 165f, 59f, paint) }
            action == "stop" -> { paint.style = Paint.Style.FILL; c.drawRoundRect(153f, 28f, 178f, 53f, 3f, 3f, paint) }
            action == "check" -> { c.drawOval(145f, 29f, 187f, 51f, paint); c.drawCircle(166f, 40f, 6f, paint) }
            else -> { c.drawCircle(165f, 30f, 9f, paint); val p = Path(); p.moveTo(157f, 58f); p.lineTo(154f, 42f); p.lineTo(161f, 46f); p.lineTo(161f, 30f); p.quadTo(165f, 25f, 169f, 30f); p.lineTo(169f, 41f); p.lineTo(178f, 43f); p.lineTo(176f, 58f); c.drawPath(p, paint) }
        }
        c.restore()
    }
}
