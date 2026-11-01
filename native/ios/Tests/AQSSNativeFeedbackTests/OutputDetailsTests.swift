import XCTest
@testable import AQSSNativeFeedback

final class OutputDetailsTests: XCTestCase {
    private let build = "Audio Bodyguard\nPlatform: iPhone/iPad\nVersion: 0.37.0\nBuild: 1"
    private let clock: Int64 = 1_793_116_800_000
    private func snapshot(_ types: [IOSOutputKind] = [.speaker], total: Int? = nil,
                          details: String? = nil, os: String = "26.0.1", time: Int64? = nil) throws -> OutputDetailsSnapshot {
        try OutputDetailsSnapshot.capture(buildDetails: details ?? build, osVersion: os,
            portTypes: types, totalReported: total ?? types.count, capturedAtMillis: time ?? clock)
    }

    func testSessionMetadataNeverClaimsActivationPlaybackOrFormat() throws {
        let result = try snapshot()
        XCTAssertTrue(result.text.hasPrefix("Audio Bodyguard iPhone output details (v1)\nCaptured at (phone clock, UTC): 2026-10-27T16:00:00.000Z\n\n\(build)"))
        for line in ["iOS/iPadOS version: 26.0.1", "Output 1: Built-in speaker",
                     "Audio session active: Unknown", "Actual playback route: Unknown", "Negotiated format: Unknown",
                     "Physical output and protection: Not verified", OutputDetailsSnapshot.notice] {
            XCTAssertTrue(result.text.contains(line), line)
        }
        XCTAssertFalse(result.text.contains("44100")); XCTAssertFalse(result.text.contains("48000"))
        XCTAssertTrue(result.text.contains("This check does not activate or configure the audio session."))
    }

    func testNoOutputsRemainExplicitlyUnknown() throws {
        let result = try snapshot([])
        XCTAssertTrue(result.text.contains("Reported outputs: 0")); XCTAssertTrue(result.text.contains("No output ports reported"))
        XCTAssertTrue(result.text.contains("Actual playback route: Unknown"))
    }

    func testBoundedPrefixDisclosesOmittedPorts() throws {
        let result = try snapshot(Array(repeating: .other, count: 16), total: 21)
        XCTAssertEqual(result.portTypes.count, 16); XCTAssertEqual(result.totalReported, 21)
        XCTAssertTrue(result.text.contains("First 16 retained; 5 additional outputs omitted"))
        XCTAssertFalse(result.text.contains("Output 17:"))
    }

    func testMalformedCountsCannotMasqueradeAsCompleteSnapshot() throws {
        XCTAssertThrowsError(try snapshot([.speaker], total: -1))
        XCTAssertThrowsError(try snapshot([.speaker], total: 0))
        XCTAssertThrowsError(try snapshot([], total: 1))
        XCTAssertThrowsError(try snapshot([.speaker], total: 2))
        XCTAssertThrowsError(try snapshot(Array(repeating: .speaker, count: 17)))
    }

    func testPortOrderAndDuplicatesArePreservedWithoutInventingDevices() throws {
        let result = try snapshot([.headphones, .speaker, .speaker, .other])
        XCTAssertEqual(result.portTypes, [.headphones, .speaker, .speaker, .other])
        XCTAssertTrue(result.text.contains("Output 2: Built-in speaker\nOutput 3: Built-in speaker"))
        XCTAssertTrue(result.text.contains("Output 4: Other output"))
    }

    func testCapturedArrayAndTextSurviveLaterEdits() throws {
        var types: [IOSOutputKind] = [.airPlay, .usb]
        let result = try snapshot(types); let original = result.text
        types[0] = .speaker; types.removeAll()
        XCTAssertEqual(result.portTypes, [.airPlay, .usb]); XCTAssertEqual(result.text, original)
        XCTAssertEqual(result.buildDetails, build); XCTAssertEqual(result.capturedAtMillis, clock)
    }

    func testInvalidClockIsRejectedAndBoundaryDatesAreExact() throws {
        XCTAssertThrowsError(try snapshot(time: -1)); XCTAssertThrowsError(try snapshot(time: Int64.max))
        XCTAssertTrue(try snapshot(time: 0).text.contains("1970-01-01T00:00:00.000Z"))
        XCTAssertTrue(try snapshot(time: 253_402_300_799_999).text.contains("9999-12-31T23:59:59.999Z"))
    }

    func testBuildEnvelopeRejectsExtraFieldsControlsAndOtherPlatforms() throws {
        for details in [build + "\nSecret: extra", build.replacingOccurrences(of: "iPhone/iPad", with: "Android"),
                        build.replacingOccurrences(of: "0.37.0", with: "0.37\u{202e}"),
                        build.replacingOccurrences(of: "0.37.0", with: "\u{2028}"),
                        build.replacingOccurrences(of: "Build: 1", with: "Build: 1\t"),
                        build.replacingOccurrences(of: "0.37.0", with: String(repeating: "x", count: 97))] {
            XCTAssertThrowsError(try snapshot(details: details))
        }
    }

    func testOSVersionIsBoundedAndCannotInjectFields() throws {
        for os in ["26\nPhysical output: verified", "26\u{202e}", "", "26..0", "-1.0", "9999.0", String(repeating: "1", count: 1000)] {
            XCTAssertThrowsError(try snapshot(os: os))
        }
        for os in ["15", "18.6", "26.0.1", "Unavailable"] { XCTAssertTrue(try snapshot(os: os).text.contains("iOS/iPadOS version: \(os)")) }
    }

    func testClosedPortVocabularyHasNoFreeTextDeviceNamesOrIdentifiers() throws {
        let result = try snapshot(IOSOutputKind.allCases)
        XCTAssertFalse(result.text.contains("UID:")); XCTAssertFalse(result.text.contains("Address:"))
        XCTAssertFalse(result.text.contains("Device name:")); XCTAssertTrue(result.text.contains("Port names and identifiers: Not included"))
        XCTAssertEqual(result.portTypes, IOSOutputKind.allCases)
    }

    func testLargestAllowedPayloadFitsBothTextLimits() throws {
        let version = String(repeating: "😀", count: 48)
        let result = try snapshot(Array(repeating: .bluetoothA2DP, count: 16), total: Int.max,
                                  details: build.replacingOccurrences(of: "0.37.0", with: version))
        XCTAssertLessThanOrEqual(result.text.utf16.count, OutputDetailsSnapshot.maxUTF16Units)
        XCTAssertLessThanOrEqual(result.text.utf8.count, OutputDetailsSnapshot.maxUTF8Bytes)
    }
}
