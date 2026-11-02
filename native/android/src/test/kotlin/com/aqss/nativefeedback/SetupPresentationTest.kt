package com.aqss.nativefeedback

import kotlin.test.Test
import kotlin.test.assertEquals

class SetupPresentationTest {
    @Test fun phoneStoreUsesItsOwnLabelsWithoutChangingTheCatalog() {
        val original = SetupContent.routes.first { it.id == "google_remote" }.steps[1]
        val iphone = SetupPresentation.step(original, SetupPhone.IPHONE)
        val android = SetupPresentation.step(original, SetupPhone.ANDROID)
        assertEquals("iPhone • App Store", iphone.screen)
        assertEquals("Get", iphone.items[iphone.focus])
        assertEquals("Android • Google Play", android.screen)
        assertEquals("Install", android.items[android.focus])
        assertEquals("App Store or Google Play", original.screen)
        assertEquals("Install", original.items[original.focus])
    }

    @Test fun allPresentationsKeepActionsTargetsAndTvPictures() {
        for (route in SetupContent.routes) for (original in route.steps) for (phone in SetupPhone.entries) {
            val shown = SetupPresentation.step(original, phone)
            assertEquals(original.focus, shown.focus)
            assertEquals(original.action, shown.action)
            assertEquals(original.note, shown.note)
            assertEquals(original.pictureKind, shown.pictureKind)
            if (original.surface != "phone") assertEquals(original, shown)
        }
    }

    @Test fun unknownManufacturerIsNotPresentedAsAPixel() {
        assertEquals(SetupPhone.GALAXY, SetupPhone.androidManufacturer("SAMSUNG"))
        assertEquals(SetupPhone.PIXEL, SetupPhone.androidManufacturer("Google"))
        assertEquals(SetupPhone.ANDROID, SetupPhone.androidManufacturer("Motorola"))
        assertEquals(SetupPhone.ANDROID, SetupPhone.androidManufacturer(""))
    }
}
