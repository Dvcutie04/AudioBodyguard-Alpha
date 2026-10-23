package com.aqss.bodyguard.prototype

import android.app.Activity
import android.app.AlertDialog
import android.content.ActivityNotFoundException
import android.content.Intent
import android.content.res.ColorStateList
import android.graphics.Typeface
import android.view.Gravity
import android.widget.Button
import android.widget.CheckBox
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import android.widget.Toast
import androidx.core.content.pm.PackageInfoCompat
import com.aqss.nativefeedback.PrivateSupportReportSnapshot

@Suppress("DEPRECATION") // Retain the API 26-compatible package lookup.
internal fun installedAppBuildDetails(activity: Activity): String {
    val info = try { activity.packageManager.getPackageInfo(activity.packageName, 0) } catch (_: Exception) { null }
    val version = info?.versionName?.takeIf { it.isNotBlank() } ?: "Unavailable"
    val build = info?.let { PackageInfoCompat.getLongVersionCode(it).toString() } ?: "Unavailable"
    return "Audio Bodyguard\nPlatform: Android\nVersion: $version\nBuild: $build"
}

/** The caller supplies an immutable completed-recap snapshot; review has no input owner. */
internal fun showPrivateSupportReport(activity: Activity, skin: InterfaceTheme, report: PrivateSupportReportSnapshot) {
    val content = LinearLayout(activity).apply {
        orientation = LinearLayout.VERTICAL
        setPadding(skin.dp(20), skin.dp(14), skin.dp(20), skin.dp(14))
        setBackgroundColor(skin.background)
    }
    fun label(parent: LinearLayout, value: String, size: Float, bold: Boolean = false): TextView = TextView(activity).apply {
        text = value; textSize = size; setTextColor(skin.text)
        if (bold) setTypeface(typeface, Typeface.BOLD)
        setPadding(0, skin.dp(8), 0, skin.dp(8)); parent.addView(this)
    }
    val dialog = AlertDialog.Builder(activity).setView(ScrollView(activity).apply { addView(content) }).create()
    val heading = LinearLayout(activity).apply { gravity = Gravity.CENTER_VERTICAL }
    label(heading, "Private support report", 22f, bold = true).layoutParams = LinearLayout.LayoutParams(0, -2, 1f)
    heading.addView(roseButton(activity, skin, "Back", compact = true) { dialog.dismiss() })
    content.addView(heading)
    val choice = CheckBox(activity).apply {
        text = "Include recent sound checks"; isChecked = true
        textSize = 17f; minHeight = skin.dp(48); setTextColor(skin.text)
        buttonTintList = ColorStateList(arrayOf(intArrayOf(android.R.attr.state_checked), intArrayOf()), intArrayOf(skin.accent, skin.muted))
    }
    content.addView(choice, LinearLayout.LayoutParams(-1, -2))
    var reviewedText = report.text(true)
    val preview = label(content, reviewedText, 17f)
    label(content, "Review before sharing\nNo audio, recognized words, photos, TV or network details are included.", 17f)
    choice.setOnCheckedChangeListener { _, checked ->
        reviewedText = report.text(checked); preview.text = reviewedText
    }
    content.addView(Button(activity).apply {
        text = "Share support report"; skin.style(this)
        setOnClickListener {
            val send = Intent(Intent.ACTION_SEND).apply {
                type = "text/plain"; putExtra(Intent.EXTRA_TEXT, reviewedText)
            }
            try { activity.startActivity(Intent.createChooser(send, null)) }
            catch (error: RuntimeException) {
                if (error !is ActivityNotFoundException && error !is SecurityException) throw error
                Toast.makeText(activity, "Sharing is unavailable. You can read the details shown here.", Toast.LENGTH_LONG).show()
            }
        }
    }, LinearLayout.LayoutParams(-1, -2).apply { topMargin = skin.dp(10) })
    dialog.show()
}
