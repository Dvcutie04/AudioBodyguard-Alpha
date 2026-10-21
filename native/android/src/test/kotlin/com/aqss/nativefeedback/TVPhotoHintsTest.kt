package com.aqss.nativefeedback
import kotlin.test.*

class TVPhotoHintsTest {
    @Test fun overOneHundredRowsCannotProducePartialPhotoHints() {
        val rows = listOf("VIZIO", "Model: X1", "IP: 10.0.0.2") + List(98) { "other row" }
        val hints = TVPhotoHints(rows.joinToString("\n"))
        assertNull(hints.brand)
        assertNull(hints.model)
        assertNull(hints.address)
    }
    @Test fun vizioAboutLabelsIdentifyOnlyTheLabelledModelAndAddress() {
        val hints = TVPhotoHints("VIZIO\nModel Name: V505M-K09\nIPv4 IP Address: 10.20.30.40\nIPv4 Default Gateway: 10.20.30.1\nDNS: 10.0.0.10")
        assertEquals("VIZIO", hints.brand)
        assertEquals("V505M-K09", hints.model)
        assertEquals("10.20.30.40", hints.address)
    }
    @Test fun indentedSplitLabelsAndCrLfKeepTheSameMeaning() {
        val hints = TVPhotoHints("  Model\tName:\r\n  V505M-K09\r\n\tIPv4  IP\tAddress:\r\n\t172.16.0.2\r\nIPv4 Default Gateway: 172.16.0.1\r\n")
        assertEquals("V505M-K09", hints.model)
        assertEquals("172.16.0.2", hints.address)
        assertEquals("X1", TVPhotoHints("Model Number: X1\r\n").model)
        assertEquals("10.0.0.2", TVPhotoHints("IPv4 IP Address:10.0.0.2").address)
    }
    @Test fun repeatedAliasesMustAgreeBeforeShowingAHint() {
        val same = TVPhotoHints("Model Name: X1\nModel: X1\nIPv4 IP Address: 10.0.0.2\nIP: 10.0.0.2")
        assertEquals("X1", same.model); assertEquals("10.0.0.2", same.address)
        assertNull(TVPhotoHints("Model Name: X1\nModel: Y2").model)
        assertNull(TVPhotoHints("IPv4 IP Address: 10.0.0.2\nIP: 10.0.0.3").address)
        assertNull(TVPhotoHints("IPv4 IP Address: 8.8.8.8\nIP: 10.0.0.3").address)
    }
    @Test fun anUnreadableLabelledCandidateCannotBeHiddenByAReadableOne() {
        for (bad in listOf("", "192.168.l.25", "http://10.0.0.2", "10.0.0.2:80", "10..0.2", "8.8.8.8")) {
            assertNull(TVPhotoHints("IP: $bad\nIP Address: 10.0.0.3").address, bad)
        }
        for (bad in listOf("", "NO DIGITS", "https://example.invalid/X1", "X".repeat(40) + "1")) {
            assertNull(TVPhotoHints("Model: $bad\nModel Code: X1").model, bad)
        }
    }
    @Test fun misleadingLabelsAndOverlongUtf8StayUnknown() {
        val hints = TVPhotoHints("TV Name: V505M-K09\nProduct model hint: X1\nIPv4 Default Gateway: 10.0.0.1\nDNS IP Address: 10.0.0.10\nIPv6 IP Address: fe80::1\nAddress: 10.0.0.2")
        assertNull(hints.model); assertNull(hints.address)
        assertNull(TVPhotoHints("Model Name:\nIPv4 IP Address: 10.0.0.2").model)
        val oversized = "é".repeat(4096) + "\nVIZIO\nModel Name: X1\nIPv4 IP Address: 10.0.0.2"
        val bounded = TVPhotoHints(oversized)
        assertNull(bounded.brand); assertNull(bounded.model); assertNull(bounded.address)
    }
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
