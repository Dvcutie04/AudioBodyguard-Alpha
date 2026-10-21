import XCTest
@testable import AQSSNativeFeedback
#if canImport(Vision)
import Vision
#endif

final class TVPhotoHintsTests: XCTestCase {
    func testExactRowLimitKeepsTheLastRowAndRejectsTheNextConflict() throws {
        let hundred: [String?] = ["VIZIO", "Model: X1"] + Array(repeating: "other row", count: 97) + ["IP: 10.0.0.2"]
        let text = try XCTUnwrap(boundedTVPhotoText(hundred))
        XCTAssertEqual(text, hundred.compactMap { $0 }.joined(separator: "\n"))
        let hints = TVPhotoHints(text)
        XCTAssertEqual(hints.brand, "VIZIO"); XCTAssertEqual(hints.model, "X1"); XCTAssertEqual(hints.address, "10.0.0.2")
        for conflict in ["LG", "Model: Y2", "IP: 10.0.0.3"] {
            XCTAssertNil(boundedTVPhotoText(hundred + [conflict]), conflict)
        }
    }
    func testExactUtf8BudgetIncludesJoinedSeparators() throws {
        let prefix = ["VIZIO", "Model: X1", "IP: 10.0.0.2"]
        let remaining = 8192 - prefix.joined(separator: "\n").utf8.count - 1
        let padding = String(repeating: "é", count: remaining / 2) + (remaining % 2 == 1 ? "a" : "")
        let rows: [String?] = (prefix + [padding]).map { Optional($0) }
        let text = try XCTUnwrap(boundedTVPhotoText(rows))
        XCTAssertEqual(text.utf8.count, 8192)
        XCTAssertEqual(TVPhotoHints(text).model, "X1")
        let over: [String?] = (prefix + [padding + "a"]).map { Optional($0) }
        XCTAssertNil(boundedTVPhotoText(over))
        XCTAssertNil(TVPhotoHints(text + "a").brand)
        XCTAssertNil(TVPhotoHints(text + "a").model)
        XCTAssertNil(TVPhotoHints(text + "a").address)
    }
    func testMissingBlankOrMultilineRowsCannotBeSilentlyDropped() {
        let prefix: [String?] = ["VIZIO", "Model: X1", "IP: 10.0.0.2"]
        let badRows: [String?] = [nil, "", " ", "\t"] +
            ["\n", "\r", "\r\n", "\u{B}", "\u{C}", "\u{85}", "\u{2028}", "\u{2029}"].map { "other" + $0 + "Model: Y2" }
        for bad in badRows { XCTAssertNil(boundedTVPhotoText(prefix + [bad])) }
    }
    func testRawBudgetCountsEveryLineBreakAndCrLfOnlyOnce() {
        let rows = ["VIZIO", "Model: X1", "IP: 10.0.0.2"] + Array(repeating: "other row", count: 97)
        for separator in ["\n", "\r", "\r\n", "\u{B}", "\u{C}", "\u{85}", "\u{2028}", "\u{2029}"] {
            let text = rows.joined(separator: separator)
            XCTAssertEqual(TVPhotoHints(text).brand, "VIZIO")
            let over = TVPhotoHints(text + separator + "one more row")
            XCTAssertNil(over.brand); XCTAssertNil(over.model); XCTAssertNil(over.address)
        }
        XCTAssertEqual(TVPhotoHints(rows.joined(separator: "\r\n")).model, "X1")
    }
    func testCollectorStopsAtTheFirstRejectionWithoutReadingTheRemainder() {
        var consumed = 0
        let tooMany = AnySequence<String?> {
            AnyIterator<String?> {
                consumed += 1
                guard consumed <= 101 else { XCTFail("Read past the rejected 101st row"); return nil }
                return .some("other row")
            }
        }
        XCTAssertNil(boundedTVPhotoText(tooMany))
        XCTAssertEqual(consumed, 101)
        var earlyConsumed = 0
        let tooLong = AnySequence<String?> {
            AnyIterator<String?> {
                earlyConsumed += 1
                guard earlyConsumed == 1 else { XCTFail("Read another row after the byte limit failed"); return nil }
                return .some(String(repeating: "a", count: 8193))
            }
        }
        XCTAssertNil(boundedTVPhotoText(tooLong))
        XCTAssertEqual(earlyConsumed, 1)
    }
    func testEmptyObservationCollectionInventsNoHints() throws {
        let text = try XCTUnwrap(boundedTVPhotoText([String?]()))
        XCTAssertEqual(text, "")
        let hints = TVPhotoHints(text)
        XCTAssertNil(hints.brand); XCTAssertNil(hints.model); XCTAssertNil(hints.address)
    }
    func testOverOneHundredRowsCannotProducePartialPhotoHints() {
        let rows = ["VIZIO", "Model: X1", "IP: 10.0.0.2"] + Array(repeating: "other row", count: 98)
        let hints = TVPhotoHints(rows.joined(separator: "\n"))
        XCTAssertNil(hints.brand)
        XCTAssertNil(hints.model)
        XCTAssertNil(hints.address)
    }
#if canImport(Vision)
    func testNativeVisionReadsSyntheticVizioLabels() throws {
        guard #available(macOS 12.0, iOS 15.0, *) else { throw XCTSkip("Native Vision text recognition is unavailable on this runtime") }
        let url = try XCTUnwrap(Bundle.module.url(forResource: "tv-photo-labels", withExtension: "png", subdirectory: "Fixtures"))
        let request = VNRecognizeTextRequest()
        request.recognitionLevel = .accurate
        request.usesLanguageCorrection = false
        try VNImageRequestHandler(url: url).perform([request])
        let text = try XCTUnwrap(boundedTVPhotoText((request.results ?? []).lazy.map { $0.topCandidates(1).first?.string }))
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
