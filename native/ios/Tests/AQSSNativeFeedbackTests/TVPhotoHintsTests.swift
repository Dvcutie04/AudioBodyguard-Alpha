import XCTest
@testable import AQSSNativeFeedback

final class TVPhotoHintsTests: XCTestCase {
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
