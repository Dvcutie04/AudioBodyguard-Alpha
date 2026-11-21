package com.aqss.bodyguard.prototype

import android.app.AlertDialog
import android.app.Dialog
import android.app.DialogFragment
import android.graphics.BitmapFactory
import android.graphics.Typeface
import android.os.Bundle
import android.view.Gravity
import android.view.View
import android.widget.Button
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import org.json.JSONObject

// The fragment restores the guide across rotation without opening any device tools.
@Suppress("DEPRECATION")
class FeaturePictureGuide : DialogFragment() {
    companion object {
        fun step(skin: InterfaceTheme, picture: String, caption: String) = LinearLayout(skin.activity).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(0, skin.dp(6), 0, skin.dp(12))
            addView(ImageView(skin.activity).apply {
                skin.activity.assets.open(picture + ".png").use { setImageBitmap(BitmapFactory.decodeStream(it)) }
                adjustViewBounds = true
                maxWidth = skin.dp(440)
                scaleType = ImageView.ScaleType.FIT_CENTER
                importantForAccessibility = View.IMPORTANT_FOR_ACCESSIBILITY_NO
            }, LinearLayout.LayoutParams(-2, -2))
            addView(TextView(skin.activity).apply {
                text = caption
                textSize = 17f
                setTextColor(skin.text)
                setPadding(0, skin.dp(6), 0, 0)
            }, LinearLayout.LayoutParams(-1, -2))
        }


        fun button(skin: InterfaceTheme, topic: String) = Button(skin.activity).apply {
            text = "Picture guide"
            skin.style(this)
            setOnClickListener {
                val manager = skin.activity.fragmentManager
                if (!manager.isStateSaved && manager.findFragmentByTag("feature-pictures") == null) {
                    FeaturePictureGuide().apply {
                        arguments = Bundle().apply {
                            putString("topic", topic)
                            putBoolean("dark", skin.dark)
                        }
                    }.show(manager, "feature-pictures")
                }
            }
        }
    }

    override fun onCreateDialog(savedInstanceState: Bundle?): Dialog {
        val host = requireNotNull(activity)
        val args = requireNotNull(arguments)
        val skin = InterfaceTheme(host, args.getBoolean("dark"))
        val catalog = host.assets.open("guides.json").bufferedReader().use { JSONObject(it.readText()) }
        val guide = catalog.getJSONObject(requireNotNull(args.getString("topic")))
        val column = LinearLayout(host).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER_HORIZONTAL
            setPadding(skin.dp(16), skin.dp(8), skin.dp(16), skin.dp(16))
        }
        fun caption(value: String, heading: Boolean) = TextView(host).apply {
            text = value
            textSize = if (heading) 21f else 18f
            setTextColor(skin.text)
            if (heading) {
                setTypeface(null, Typeface.BOLD)
                if (android.os.Build.VERSION.SDK_INT >= 28) isAccessibilityHeading = true
            }
        }
        val steps = guide.getJSONArray("steps")
        for (index in 0 until steps.length()) {
            val step = steps.getJSONObject(index)
            column.addView(caption("${index + 1}. " + step.getString("title"), true),
                LinearLayout.LayoutParams(-1, -2).apply { topMargin = skin.dp(16) })
            val image = ImageView(host).apply {
                val bitmap = host.assets.open(step.getString("picture") + ".png").use {
                    BitmapFactory.decodeStream(it)
                }
                setImageBitmap(bitmap)
                adjustViewBounds = true
                maxWidth = skin.dp(440)
                scaleType = ImageView.ScaleType.FIT_CENTER
                importantForAccessibility = View.IMPORTANT_FOR_ACCESSIBILITY_NO
            }
            column.addView(image, LinearLayout.LayoutParams(-2, -2).apply {
                topMargin = skin.dp(8); bottomMargin = skin.dp(8)
            })
            column.addView(caption(step.getString("detail"), false), LinearLayout.LayoutParams(-1, -2))
        }
        val scroll = ScrollView(host).apply {
            id = android.R.id.list
            setBackgroundColor(skin.background)
            addView(column)
        }
        return AlertDialog.Builder(host)
            .setTitle(guide.getString("title"))
            .setView(scroll)
            .setPositiveButton("Back", null)
            .create()
    }
}
