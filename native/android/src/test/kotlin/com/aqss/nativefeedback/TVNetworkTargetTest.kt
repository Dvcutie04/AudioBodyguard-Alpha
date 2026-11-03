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
}
