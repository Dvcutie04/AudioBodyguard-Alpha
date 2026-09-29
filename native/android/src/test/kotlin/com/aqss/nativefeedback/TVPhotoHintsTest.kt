package com.aqss.nativefeedback
import kotlin.test.*

class TVPhotoHintsTest {
    @Test fun onlyUnambiguousLabelledHints() {
        val hints = TVPhotoHints("Samsung\nModel Code: QN90C\nIP Address: 192.168.1.25\nSerial: PRIVATE")
        assertEquals("SAMSUNG", hints.brand); assertEquals("QN90C", hints.model); assertEquals("192.168.1.25", hints.address)
        assertNull(TVPhotoHints("Samsung LG").brand)
        assertNull(TVPhotoHints("Model: X1\nModel: Y2").model)
        assertNull(TVPhotoHints("IP: 10.0.0.2\nIP: 10.0.0.3").address)
    }
    @Test fun labelsOnTheirOwnLineAndCompactColon() {
        assertEquals("192.168.1.25", TVPhotoHints("Model Code:\nQN90C\nIP Address:\n192.168.1.25").address)
        assertEquals("QN90C", TVPhotoHints("Model Code:\nQN90C").model)
        assertEquals("192.168.1.25", TVPhotoHints("IP:192.168.1.25").address)
        assertNull(TVPhotoHints("IP:\nGateway: 192.168.1.1").address)
    }
    @Test fun rejectsHostileAndMislabelledEndpoints() {
        for (input in listOf("127.0.0.1", "169.254.169.254", "8.8.8.8", "192.168.1.999", "192.168.01.2", "10.0.0.2:80", "http://10.0.0.2", "::1", "10.0.0.2/path", "10..0.2")) {
            assertFalse(TVPhotoHints.isPrivateIPv4(input), input)
            assertNull(TVPhotoHints("IP: $input").address)
        }
        assertNull(TVPhotoHints("Gateway: 192.168.1.1\nDNS: 10.0.0.1\nVisit http://10.0.0.2").address)
        assertNull(TVPhotoHints("a".repeat(8193) + "\nSamsung").brand)
        assertNull(TVPhotoHints("IP: 192.168.l.25").address)
        assertTrue(TVPhotoHints.isPrivateIPv4("172.16.0.2")); assertFalse(TVPhotoHints.isPrivateIPv4("172.32.0.2"))
    }
}
