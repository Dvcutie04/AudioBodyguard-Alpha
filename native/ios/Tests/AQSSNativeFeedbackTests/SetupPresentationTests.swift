import XCTest
@testable import AQSSNativeFeedback

final class SetupPresentationTests: XCTestCase {
    func testPhoneStoreUsesItsOwnLabelsAndKeepsTheOriginalCatalog() throws {
        let route = try XCTUnwrap(AQSSSetupContent.routes.first { $0.id == "google_remote" })
        let original = route.steps[1]
        let iphone = AQSSSetupPresentation.step(original, phone: .iphone)
        let android = AQSSSetupPresentation.step(original, phone: .android)
        XCTAssertEqual(iphone.screen, "iPhone • App Store")
        XCTAssertEqual(iphone.items[iphone.focus], "Get")
        XCTAssertEqual(android.screen, "Android • Google Play")
        XCTAssertEqual(android.items[android.focus], "Install")
        XCTAssertEqual(original.screen, "App Store or Google Play")
        XCTAssertEqual(original.items[original.focus], "Install")
    }

    func testEveryPhonePresentationPreservesTheActionAndTvPictures() {
        for route in AQSSSetupContent.routes {
            for original in route.steps {
                for phone in AQSSSetupPhone.allCases {
                    let shown = AQSSSetupPresentation.step(original, phone: phone)
                    XCTAssertEqual(shown.focus, original.focus)
                    XCTAssertEqual(shown.action, original.action)
                    XCTAssertEqual(shown.note, original.note)
                    XCTAssertEqual(shown.pictureKind, original.pictureKind)
                    if original.surface != "phone" { XCTAssertEqual(shown, original) }
                }
            }
        }
    }

    func testActualPhoneFamilyDoesNotGuessAnUnknownManufacturer() {
        XCTAssertEqual(AQSSSetupPhone.androidManufacturer("SAMSUNG"), .galaxy)
        XCTAssertEqual(AQSSSetupPhone.androidManufacturer("Google"), .pixel)
        XCTAssertEqual(AQSSSetupPhone.androidManufacturer("Motorola"), .android)
        XCTAssertEqual(AQSSSetupPhone.androidManufacturer(""), .android)
        XCTAssertEqual(AQSSSetupPhone.iphone.label, "iPhone")
    }
}
