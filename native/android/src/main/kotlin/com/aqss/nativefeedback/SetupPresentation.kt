package com.aqss.nativefeedback

import java.util.Locale

/** Presentation only; a phone label does not identify, pair or authorize a TV. */
enum class SetupPhone(val label: String, val wifiRoute: String? = null) {
    IPHONE("iPhone", "phone_iphone"), PIXEL("Google Pixel", "phone_pixel"),
    GALAXY("Samsung Galaxy", "phone_galaxy"), ANDROID("Android");
    companion object {
        fun androidManufacturer(value: String): SetupPhone = when (value.lowercase(Locale.ROOT)) {
            "samsung" -> GALAXY
            "google" -> PIXEL
            else -> ANDROID
        }
    }
}

object SetupPresentation {
    /** Keep documented shared labels; specialize only actual phone surfaces. */
    fun step(original: SetupStep, phone: SetupPhone): SetupStep {
        if (original.surface != "phone") return original
        val store = if (phone == SetupPhone.IPHONE) "App Store" else "Google Play"
        return when (original.screen) {
            "App Store or Google Play" -> original.copy(
                screen = "${phone.label} • $store",
                instruction = original.instruction.replace("App Store or Google Play", store),
                items = if (phone == SetupPhone.IPHONE) original.items.map { if (it == "Install") "Get" else it } else original.items,
            )
            "Phone apps" -> original.copy(screen = "${phone.label} • Apps")
            "Phone • Wi-Fi" -> original.copy(screen = "${phone.label} • Wi-Fi")
            else -> original
        }
    }
}
