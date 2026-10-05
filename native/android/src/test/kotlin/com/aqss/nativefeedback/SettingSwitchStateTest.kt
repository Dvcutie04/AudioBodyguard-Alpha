package com.aqss.nativefeedback

import kotlin.test.Test
import kotlin.test.assertFalse
import kotlin.test.assertTrue
import kotlin.test.assertNull

class SettingSwitchStateTest {
    @Test fun disconnectedAttemptExpiresAtTwoSeconds() {
        val s = SettingSwitchState()
        s.press("captions", false, 10.0)
        assertTrue(s.isOn("captions")); assertTrue(s.isAttempting("captions"))
        s.expire(11.999); assertTrue(s.isOn("captions"))
        s.expire(12.0); assertFalse(s.isOn("captions")); assertNull(s.nextExpiry)
    }
    @Test fun repeatedTapsDoNotExtendAttemptAndOldExpiryCannotEraseNewAttempt() {
        val s = SettingSwitchState()
        s.press("voice", false, 10.0); s.press("voice", false, 11.5)
        s.expire(12.0); assertFalse(s.isOn("voice"))
        s.press("voice", false, 12.1); s.expire(12.5); assertTrue(s.isAttempting("voice"))
        s.expire(14.1); assertFalse(s.isOn("voice"))
    }
    @Test fun attemptsAreIndependentAndVerifiedConnectionPersistsUntilOff() {
        val s = SettingSwitchState()
        s.press("captions", false, 10.0); s.press("background", false, 11.0); s.expire(12.0)
        assertFalse(s.isOn("captions")); assertTrue(s.isOn("background"))
        s.press("captions", true, 12.0); s.expire(100.0)
        assertTrue(s.isOn("captions")); assertFalse(s.isAttempting("captions")); assertFalse(s.isOn("background"))
        s.press("captions", true, 101.0); assertFalse(s.isOn("captions"))
    }
    @Test fun connectionLossAndLifecycleResetTurnOffEverySetting() {
        val s = SettingSwitchState()
        listOf("captions", "profiles", "voice").forEach { s.press(it, true, 10.0) }
        s.press("background", false, 11.0)
        listOf("captions", "profiles", "voice").forEach { assertFalse(s.isOn(it)) }
        s.connectionLost(); assertNull(s.nextExpiry)
        InterfaceContent.settings.forEach { assertFalse(s.isOn(it.id)) }
        s.press("captions", true, 20.0); s.reset(); assertFalse(s.isOn("captions"))
    }
    @Test fun presetsAreExclusiveAndInvalidInputNeverEnablesAnything() {
        val s = SettingSwitchState()
        s.press("dialogue", true, 1.0); s.press("night", true, 2.0)
        assertFalse(s.isOn("dialogue")); assertTrue(s.isOn("night"))
        s.press("dialogue", true, 3.0); assertTrue(s.isOn("dialogue")); assertFalse(s.isOn("night"))
        s.reset()
        listOf(Double.NaN, Double.POSITIVE_INFINITY, -1.0).forEach { s.press("captions", true, it) }
        s.press("invented", true, 1.0); assertFalse(s.isOn("captions")); assertNull(s.nextExpiry)
    }
}
