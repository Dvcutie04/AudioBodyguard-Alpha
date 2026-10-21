import XCTest
@testable import AQSSNativeFeedback
#if canImport(Vision)
import Vision
#endif

final class TVPhotoHintsTests: XCTestCase {
#if canImport(Vision)
    func testNativeVisionReadsSyntheticVizioLabels() throws {
        guard #available(macOS 12.0, iOS 15.0, *) else { throw XCTSkip("Native Vision text recognition is unavailable on this runtime") }
        let url = try XCTUnwrap(Bundle.module.url(forResource: "tv-photo-labels", withExtension: "png", subdirectory: "Fixtures"))
        let request = VNRecognizeTextRequest()
        request.recognitionLevel = .accurate
        request.usesLanguageCorrection = false
        try VNImageRequestHandler(url: url).perform([request])
        let text = (request.results ?? []).prefix(100).compactMap { $0.topCandidates(1).first?.string }.joined(separator: "\n")
        let hints = TVPhotoHints(text)
        XCTAssertEqual(hints.brand, "VIZIO", "Synthetic image OCR: \(text)")
        XCTAssertEqual(hints.model, "V505M-K09", "Synthetic image OCR: \(text)")
        XCTAssertEqual(hints.address, "10.20.30.40", "Synthetic image OCR: \(text)")
    }
#endif
    func testVizioAboutLabelsIdentifyOnlyTheLabelledModelAndAddress() {
        let hints = TVPhotoHints("VIZIO\nModel Name: V505M-K09\nIPv4 IP Address: 10.20.30.40\nIPv4 Default Gateway: 10.20.30.1\nDNS: 10.0.0.10")
        XCTAssertEqual(hints.brand, "VIZIO")
        XCTAssertEqual(hints.model, "V505M-K09")
        XCTAssertEqual(hints.address, "10.20.30.40")
    }
    func testIndentedSplitLabelsAndCrLfKeepTheSameMeaning() {
        let hints = TVPhotoHints("  Model\tName:\r\n  V505M-K09\r\n\tIPv4  IP\tAddress:\r\n\t172.16.0.2\r\nIPv4 Default Gateway: 172.16.0.1\r\n")
        XCTAssertEqual(hints.model, "V505M-K09")
        XCTAssertEqual(hints.address, "172.16.0.2")
        XCTAssertEqual(TVPhotoHints("Model Number: X1\r\n").model, "X1")
        XCTAssertEqual(TVPhotoHints("IPv4 IP Address:10.0.0.2").address, "10.0.0.2")
    }
    func testRepeatedAliasesMustAgreeBeforeShowingAHint() {
        let same = TVPhotoHints("Model Name: X1\nModel: X1\nIPv4 IP Address: 10.0.0.2\nIP: 10.0.0.2")
        XCTAssertEqual(same.model, "X1"); XCTAssertEqual(same.address, "10.0.0.2")
        XCTAssertNil(TVPhotoHints("Model Name: X1\nModel: Y2").model)
        XCTAssertNil(TVPhotoHints("IPv4 IP Address: 10.0.0.2\nIP: 10.0.0.3").address)
        XCTAssertNil(TVPhotoHints("IPv4 IP Address: 8.8.8.8\nIP: 10.0.0.3").address)
    }
    func testAnUnreadableLabelledCandidateCannotBeHiddenByAReadableOne() {
        for bad in ["", "192.168.l.25", "http://10.0.0.2", "10.0.0.2:80", "10..0.2", "8.8.8.8"] {
            XCTAssertNil(TVPhotoHints("IP: \(bad)\nIP Address: 10.0.0.3").address, bad)
        }
        for bad in ["", "NO DIGITS", "https://example.invalid/X1", String(repeating: "X", count: 40) + "1"] {
            XCTAssertNil(TVPhotoHints("Model: \(bad)\nModel Code: X1").model, bad)
        }
    }
    func testMisleadingLabelsAndOverlongUtf8StayUnknown() {
        let hints = TVPhotoHints("TV Name: V505M-K09\nProduct model hint: X1\nIPv4 Default Gateway: 10.0.0.1\nDNS IP Address: 10.0.0.10\nIPv6 IP Address: fe80::1\nAddress: 10.0.0.2")
        XCTAssertNil(hints.model); XCTAssertNil(hints.address)
        XCTAssertNil(TVPhotoHints("Model Name:\nIPv4 IP Address: 10.0.0.2").model)
        let oversized = String(repeating: "é", count: 4096) + "\nVIZIO\nModel Name: X1\nIPv4 IP Address: 10.0.0.2"
        let bounded = TVPhotoHints(oversized)
        XCTAssertNil(bounded.brand); XCTAssertNil(bounded.model); XCTAssertNil(bounded.address)
    }
    func testOnlyUnambiguousLabelledHints() {
        let hints = TVPhotoHints("Samsung\nModel Code: QN90C\nIP Address: 192.168.1.25\nSerial: PRIVATE")
        XCTAssertEqual(hints.brand, "SAMSUNG"); XCTAssertEqual(hints.model, "QN90C"); XCTAssertEqual(hints.address, "192.168.1.25")
        XCTAssertNil(TVPhotoHints("Samsung LG\nModel: X1\nModel: Y2\nIP: 10.0.0.2\nIP: 10.0.0.3").brand)
        XCTAssertNil(TVPhotoHints("Model: X1\nModel: Y2").model)
        XCTAssertNil(TVPhotoHints("IP: 10.0.0.2\nIP: 10.0.0.3").address)
    }
    func testLabelsOnTheirOwnLineAndCompactColon() {
        XCTAssertEqual(TVPhotoHints("Model Code:\nQN90C\nIP Address:\n192.168.1.25").address, "192.168.1.25")
        XCTAssertEqual(TVPhotoHints("Model Code:\nQN90C").model, "QN90C")
        XCTAssertEqual(TVPhotoHints("IP:192.168.1.25").address, "192.168.1.25")
        XCTAssertNil(TVPhotoHints("IP:\nGateway: 192.168.1.1").address)
    }
    func testRejectsHostileAndMislabelledEndpoints() {
        for input in ["127.0.0.1", "169.254.169.254", "8.8.8.8", "192.168.1.999", "192.168.01.2", "10.0.0.2:80", "http://10.0.0.2", "::1", "10.0.0.2/path", "10..0.2"] {
            XCTAssertFalse(TVPhotoHints.isPrivateIPv4(input), input)
            XCTAssertNil(TVPhotoHints("IP: \(input)").address)
        }
        XCTAssertNil(TVPhotoHints("Gateway: 192.168.1.1\nDNS: 10.0.0.1\nVisit http://10.0.0.2").address)
        XCTAssertNil(TVPhotoHints(String(repeating: "a", count: 8193) + "\nSamsung").brand)
        XCTAssertNil(TVPhotoHints("IP: 192.168.l.25").address)
        XCTAssertTrue(TVPhotoHints.isPrivateIPv4("172.16.0.2"))
        XCTAssertFalse(TVPhotoHints.isPrivateIPv4("172.32.0.2"))
    }
}
