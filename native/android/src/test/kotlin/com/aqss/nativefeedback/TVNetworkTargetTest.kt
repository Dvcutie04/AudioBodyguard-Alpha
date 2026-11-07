package com.aqss.nativefeedback

import kotlin.test.*

class TVNetworkTargetTest {
    @Test fun onlyCanonicalPrivateUnicastCandidatesAreAccepted() {
        for (value in listOf("10.0.0.1", "10.255.255.254", "172.16.0.1", "172.31.255.254", "192.168.1.105")) {
            assertEquals(value, LocalTVTarget.parse(value)?.address)
        }
        val target = assertNotNull(LocalTVTarget.parse(" 192.168.1.105\n"))
        assertContentEquals(byteArrayOf(192.toByte(), 168.toByte(), 1, 105), target.addressBytes())
        target.addressBytes()[0] = 1
        assertEquals(192.toByte(), target.addressBytes()[0])
    }

    @Test fun noDnsUrlPublicLoopbackBroadcastOrAlternateNumberSyntax() {
        for (value in listOf("", "tv.local", "https://192.168.1.2", "192.168.1.2:7345", "8.8.8.8",
            "127.0.0.1", "0.0.0.0", "169.254.1.1", "224.0.0.1", "255.255.255.255",
            "172.15.1.1", "172.32.1.1", "192.169.1.1", "10.0.0.0", "10.0.0.255",
            "::1", "::ffff:192.168.1.1", "192.168.1", "192..1.1", "192.168.1.1.",
            "192.168.1.256", "192.168.01.1", "+10.0.0.1", "0xa000001", "167772161",
            "１０.0.0.1", "10.0.0.1/path", "10.0.0.1\n10.0.0.2", " ".repeat(65))) {
            assertNull(LocalTVTarget.parse(value), value)
        }
    }

    @Test fun workAndEvidenceScopeStayBounded() {
        assertEquals(listOf(7345, 9000), LocalTVTarget.PORTS)
        assertEquals(4000, LocalTVTarget.TIMEOUT_MILLIS)
        assertEquals("TV identity, pairing and audio protection are not verified.", LocalTVTarget.BOUNDARY)
    }

    @Test fun everyTrialOutcomeIsHistoricalPrivateAndNeverPairingEvidence() {
        val build = "Audio Bodyguard\nPlatform: Android\nVersion: 0.45-friend-trial\nBuild: 48"
        for (outcome in TVTrialOutcome.entries) {
            val report = TVTrialReport.capture(build, outcome, 0)
            assertTrue(report.text.contains("Outcome: ${outcome.name}"))
            assertTrue(report.text.contains("1970-01-01T00:00:00.000Z"))
            assertTrue(report.text.contains("TV identity: Not verified\nTV pairing: Not verified\nAudio protection: Not verified"))
            assertTrue(report.text.contains(build))
            assertFalse(report.text.contains("192.168.1.105"))
            assertTrue(report.text.toByteArray(Charsets.UTF_8).size < 4096)
        }
    }

    @Test fun trialFollowUpKeepsReachabilitySeparateFromReviewAndPairing() {
        assertEquals(TVTrialFollowUp.ADDRESS_PICTURES, TVTrialOutcome.ADDRESS_REJECTED.followUp)
        assertEquals(TVTrialFollowUp.PHONE_WIFI, TVTrialOutcome.WIFI_REQUIRED.followUp)
        assertEquals(TVTrialFollowUp.PHONE_WIFI, TVTrialOutcome.NO_SERVICE_RESPONSE.followUp)
        assertEquals(TVTrialFollowUp.REVIEW, TVTrialOutcome.SERVICE_ANSWERED_UNVERIFIED.followUp)
        for (outcome in listOf(TVTrialOutcome.CHECK_UNAVAILABLE, TVTrialOutcome.CHECK_STOPPED, TVTrialOutcome.CLEANUP_UNRESOLVED)) {
            assertNull(outcome.followUp)
        }
    }

    @Test fun trialReviewRetainsOneImmutableOutcomeAndExactBuild() {
        val build = "Audio Bodyguard\nPlatform: Android\nVersion: 0.45-friend-trial\nBuild: 48"
        val first = TVTrialReport.capture(build, TVTrialOutcome.SERVICE_ANSWERED_UNVERIFIED, 0)
        TVTrialReport.capture(build, TVTrialOutcome.NO_SERVICE_RESPONSE, 1000)
        assertTrue(first.text.contains("Outcome: SERVICE_ANSWERED_UNVERIFIED"))
        assertFalse(first.text.contains("NO_SERVICE_RESPONSE"))
        assertFailsWith<IllegalArgumentException> { TVTrialReport.capture(build + "\nTV IP: secret", TVTrialOutcome.CHECK_STOPPED, 0) }
        assertFailsWith<IllegalArgumentException> { TVTrialReport.capture(build, TVTrialOutcome.CHECK_STOPPED, -1) }
        assertFailsWith<IllegalArgumentException> { TVTrialReport.capture(build, TVTrialOutcome.CHECK_STOPPED, 253_402_300_800_000) }
        assertFailsWith<IllegalArgumentException> { TVTrialReport.capture(build.replace("Build: 48", "Build: 10.1"), TVTrialOutcome.CHECK_STOPPED, 0) }
    }
}
