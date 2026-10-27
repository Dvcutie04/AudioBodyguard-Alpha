package com.aqss.bodyguard.prototype

import android.app.Activity
import android.content.ActivityNotFoundException
import android.content.Intent
import android.os.Build
import android.os.Bundle
import android.text.Editable
import android.text.InputFilter
import android.text.InputType
import android.text.TextWatcher
import android.view.KeyEvent
import android.view.View
import android.view.WindowInsets
import android.view.WindowManager
import android.view.inputmethod.EditorInfo
import android.view.inputmethod.InputMethodManager
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import android.widget.Toast
import com.aqss.nativefeedback.TestSetupField
import com.aqss.nativefeedback.TestSetupReportSnapshot

/** Manual intake only; never opens an audio, discovery or measurement owner. */
class TestSetupActivity : Activity() {
    private data class Retained(val notes: Map<TestSetupField, String>, val report: TestSetupReportSnapshot?)
    private lateinit var skin: InterfaceTheme
    private val notes = mutableMapOf<TestSetupField, String>()
    private var reviewed: TestSetupReportSnapshot? = null
    private var visible = false
    private var shareButton: Button? = null
    private var backCallback: android.window.OnBackInvokedCallback? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        val dark = intent.getBooleanExtra("dark", true)
        setTheme(if (dark) R.style.AQSSMidnightTheme else R.style.AQSSReadOnlyTheme)
        super.onCreate(savedInstanceState)
        skin = InterfaceTheme(this, dark)
        if (Build.VERSION.SDK_INT >= 30) window.setDecorFitsSystemWindows(false)
        window.setSoftInputMode(WindowManager.LayoutParams.SOFT_INPUT_ADJUST_RESIZE)
        (lastNonConfigurationInstance as? Retained)?.let { notes.putAll(it.notes); reviewed = it.report }
        if (Build.VERSION.SDK_INT >= 33) {
            backCallback = android.window.OnBackInvokedCallback { goBack() }.also {
                onBackInvokedDispatcher.registerOnBackInvokedCallback(android.window.OnBackInvokedDispatcher.PRIORITY_DEFAULT, it)
            }
        }
        reviewed?.let(::renderReview) ?: renderForm()
    }

    override fun onResume() { super.onResume(); visible = true; shareButton?.isEnabled = true }
    override fun onPause() { visible = false; super.onPause() }
    override fun onWindowFocusChanged(hasFocus: Boolean) {
        super.onWindowFocusChanged(hasFocus)
        if (hasFocus && visible) shareButton?.isEnabled = true
    }
    override fun onRetainNonConfigurationInstance(): Any = Retained(notes.toMap(), reviewed)
    override fun onDestroy() {
        visible = false
        if (Build.VERSION.SDK_INT >= 33) backCallback?.let { onBackInvokedDispatcher.unregisterOnBackInvokedCallback(it) }
        backCallback = null; shareButton = null
        if (isFinishing) { notes.clear(); reviewed = null }
        super.onDestroy()
    }
    @Deprecated("API 26–32 Back fallback")
    @android.annotation.SuppressLint("GestureBackNavigation") // API 33+ uses the registered platform OnBackInvokedCallback.
    override fun onBackPressed() { goBack() }

    private fun goBack() {
        if (isFinishing || isDestroyed) return
        if (reviewed != null) { reviewed = null; renderForm() } else finish()
    }

    private fun root(title: String): LinearLayout = LinearLayout(this).apply {
        orientation = LinearLayout.VERTICAL
        setPadding(skin.dp(16), skin.dp(28), skin.dp(16), skin.dp(16))
        setBackgroundColor(skin.background)
        importantForAutofill = View.IMPORTANT_FOR_AUTOFILL_NO_EXCLUDE_DESCENDANTS
        val header = LinearLayout(this@TestSetupActivity).apply { gravity = android.view.Gravity.CENTER_VERTICAL }
        header.addView(TextView(this@TestSetupActivity).apply {
            text = title; textSize = 24f; setTextColor(skin.text)
            setTypeface(typeface, android.graphics.Typeface.BOLD)
        }, LinearLayout.LayoutParams(0, -2, 1f))
        header.addView(roseButton(this@TestSetupActivity, skin, "Back", compact = true) { goBack() })
        addView(header)
    }

    private fun words(parent: LinearLayout, value: String, size: Float = 16f): TextView = TextView(this).apply {
        text = value; textSize = size; setTextColor(skin.text)
        setPadding(0, skin.dp(8), 0, skin.dp(8)); parent.addView(this)
    }

    private fun install(root: LinearLayout) {
        setContentView(root)
        root.setOnApplyWindowInsetsListener { view, insets ->
            if (Build.VERSION.SDK_INT >= 30) {
                val bars = insets.getInsets(WindowInsets.Type.systemBars())
                val keyboard = insets.getInsets(WindowInsets.Type.ime())
                view.setPadding(skin.dp(16) + bars.left, skin.dp(12) + bars.top,
                    skin.dp(16) + bars.right, skin.dp(12) + maxOf(bars.bottom, keyboard.bottom))
            }
            insets
        }
    }

    private fun hideKeyboard() {
        val focused = currentFocus
        focused?.windowToken?.let { token ->
            (getSystemService(INPUT_METHOD_SERVICE) as? InputMethodManager)?.hideSoftInputFromWindow(token, 0)
        }
        focused?.clearFocus()
    }

    private fun renderForm() {
        shareButton = null
        val root = root("Test setup")
        val column = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; isFocusableInTouchMode = true }
        words(column, "Record the two-phone test arrangement. These are your notes, not verified measurements.")
        words(column, "Every answer is optional. Leave blank for Unknown. Brief technical details only.", 15f)
        val entries = mutableListOf<EditText>()
        val clear = Button(this).apply { text = "Clear notes"; skin.style(this) }
        fun updateClear() { clear.isEnabled = notes.values.any { it.isNotEmpty() } }
        for (field in TestSetupField.entries) {
            words(column, field.title, 18f)
            val input = EditText(this).apply {
                contentDescription = field.title; hint = field.hint
                setTextColor(skin.text); setHintTextColor(skin.muted); textSize = 16f
                setSingleLine(true); setSelectAllOnFocus(false)
                inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_FLAG_NO_SUGGESTIONS
                imeOptions = EditorInfo.IME_ACTION_DONE or EditorInfo.IME_FLAG_NO_EXTRACT_UI or EditorInfo.IME_FLAG_NO_PERSONALIZED_LEARNING
                filters = arrayOf(InputFilter.LengthFilter(TestSetupReportSnapshot.MAX_FIELD_UNITS))
                isSaveEnabled = false; importantForAutofill = View.IMPORTANT_FOR_AUTOFILL_NO
                minHeight = skin.dp(48); setPadding(skin.dp(12), skin.dp(10), skin.dp(12), skin.dp(10))
                background = skin.shape(skin.raised, 12, border = true)
                setText(notes[field] ?: "")
                addTextChangedListener(object : TextWatcher {
                    override fun beforeTextChanged(s: CharSequence?, start: Int, count: Int, after: Int) = Unit
                    override fun onTextChanged(s: CharSequence?, start: Int, before: Int, count: Int) = Unit
                    override fun afterTextChanged(value: Editable?) { notes[field] = value?.toString() ?: ""; updateClear() }
                })
                setOnEditorActionListener { _, action, event ->
                    if (action == EditorInfo.IME_ACTION_DONE || event?.keyCode == KeyEvent.KEYCODE_ENTER) {
                        hideKeyboard(); true
                    } else false
                }
            }
            entries.add(input); column.addView(input, LinearLayout.LayoutParams(-1, -2))
        }
        words(column, "Notes are temporary. Closing this worksheet clears them.", 15f)
        root.addView(ScrollView(this).apply { addView(column) }, LinearLayout.LayoutParams(-1, 0, 1f))
        clear.setOnClickListener { notes.clear(); entries.forEach { it.setText("") }; hideKeyboard(); updateClear() }
        updateClear(); root.addView(clear, LinearLayout.LayoutParams(-1, -2))
        root.addView(Button(this).apply {
            text = "Review setup report"; skin.style(this, primary = true)
            setOnClickListener {
                if (!visible || !hasWindowFocus() || isFinishing || isDestroyed) return@setOnClickListener
                hideKeyboard()
                val report = try { TestSetupReportSnapshot.capture(installedAppBuildDetails(this@TestSetupActivity), notes, System.currentTimeMillis()) }
                    catch (_: IllegalArgumentException) {
                        Toast.makeText(this@TestSetupActivity, "Check this phone’s date and the notes, then try again.", Toast.LENGTH_LONG).show()
                        return@setOnClickListener
                    }
                reviewed = report; renderReview(report)
            }
        }, LinearLayout.LayoutParams(-1, -2))
        install(root); column.requestFocus()
    }

    private fun renderReview(report: TestSetupReportSnapshot) {
        val root = root("Review setup report")
        val preview = TextView(this).apply {
            text = report.text; textSize = 16f; setTextColor(skin.text); setTextIsSelectable(true)
            setPadding(0, skin.dp(12), 0, skin.dp(12))
        }
        root.addView(ScrollView(this).apply { addView(preview) }, LinearLayout.LayoutParams(-1, 0, 1f))
        words(root, TestSetupReportSnapshot.NOTICE, 14f)
        val share = Button(this).apply { text = "Share setup report"; skin.style(this, primary = true) }
        shareButton = share
        share.setOnClickListener {
            if (!visible || !hasWindowFocus() || isFinishing || isDestroyed || !share.isEnabled || reviewed !== report) return@setOnClickListener
            share.isEnabled = false
            val send = Intent(Intent.ACTION_SEND).apply { type = "text/plain"; putExtra(Intent.EXTRA_TEXT, report.text) }
            try { startActivity(Intent.createChooser(send, null)) }
            catch (error: RuntimeException) {
                share.isEnabled = true
                if (error !is ActivityNotFoundException && error !is SecurityException) throw error
                Toast.makeText(this, "Sharing is unavailable. You can read the report shown here.", Toast.LENGTH_LONG).show()
            }
        }
        root.addView(share, LinearLayout.LayoutParams(-1, -2)); install(root)
    }
}
