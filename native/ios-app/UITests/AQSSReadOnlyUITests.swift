import XCTest
import UIKit

final class AQSSReadOnlyUITests: XCTestCase {
    override func setUpWithError() throws {
        continueAfterFailure = false
        XCUIDevice.shared.orientation = .portrait
    }
    func testSimplifiedSetupAndContextualJumps() { checkSimplifiedSetup(large: false) }
    func testTVNetworkRejectsPublicAddressWithoutContact() {
        let app = launch()
        tab("devices", app); tap("? Device help", app); tap("VIZIO network check", app)
        let field = app.textFields["tv-network-address"]
        XCTAssertTrue(field.waitForExistence(timeout: 5))
        XCTAssertFalse(app.buttons["tv-network-start-stop"].isEnabled)
        field.tap(); field.typeText("8.8.8.8")
        tap("Check this address", app, scroll: app.scrollViews["tv-network-scroll"])
        label("Enter the private IPv4 address shown in your TV’s network settings.", app)
        XCTAssertEqual(app.staticTexts["tv-network-boundary"].label,
                       "TV identity, pairing and audio protection are not verified.")
        XCTAssertEqual(app.alerts.count, 0, "Rejected input must not request local-network access")
        app.buttons["tv-network-back"].tap()
        label("Connection not verified", app)
    }
    func testTVNetworkVisitClearsDraftOnBackgroundAndBack() {
        let app = launch()
        tab("devices", app); tap("? Device help", app); tap("VIZIO network check", app)
        let field = app.textFields["tv-network-address"]
        XCTAssertTrue(field.waitForExistence(timeout: 5))
        field.tap(); field.typeText("192.168.1.105")
        // No Start: this UI test makes no network attempt on the CI host.
        XCUIDevice.shared.press(.home); app.activate()
        XCTAssertEqual(field.value as? String, "TV IP address")
        XCTAssertEqual(app.staticTexts["tv-network-result"].label, "Ready to check the address you enter.")
        app.buttons["tv-network-back"].tap(); tap("VIZIO network check", app)
        XCTAssertEqual(app.textFields["tv-network-address"].value as? String, "TV IP address")
        app.buttons["tv-network-back"].tap()
    }

    func testTVNetworkRejectedResultCanBeReviewedPrivately() {
        let app = launch()
        tab("devices", app); tap("? Device help", app); tap("VIZIO network check", app)
        let field = app.textFields["tv-network-address"]
        XCTAssertTrue(field.waitForExistence(timeout: 5))
        XCTAssertFalse(app.buttons["tv-network-review"].exists)
        field.tap(); field.typeText("8.8.8.8")
        tap("Check this address", app, scroll: app.scrollViews["tv-network-scroll"])
        tap("Review test result", app, scroll: app.scrollViews["tv-network-scroll"])
        let preview = app.staticTexts["tv-network-report-preview"]
        XCTAssertTrue(preview.waitForExistence(timeout: 5))
        XCTAssertTrue(preview.label.contains("Outcome: ADDRESS_REJECTED"))
        XCTAssertTrue(preview.label.contains("No native check started"))
        XCTAssertFalse(preview.label.contains("8.8.8.8"))
        XCTAssertTrue(app.buttons["tv-network-report-share"].isEnabled)
        app.buttons["tv-network-report-back"].tap()
        XCTAssertEqual(field.value as? String, "TV IP address")
        XCTAssertFalse(app.buttons["tv-network-review"].exists)
        XCTAssertEqual(app.staticTexts["tv-network-result"].label, "Ready to check the address you enter.")
        app.buttons["tv-network-back"].tap()
    }
    func testSimplifiedSetupWithLargestTextAndReducedMotion() { checkSimplifiedSetup(large: true) }
    func testLargeTextSetupHelpScrollsWithoutOpeningAShortcut() {
        let app = XCUIApplication()
        app.launchArguments = ["-aqssGuideDismissedV1", "NO", "-aqssSetupProgressV1", "{}", "-UIPreferredContentSizeCategoryName", "UICTContentSizeCategoryAccessibilityXXXL"]
        app.launch(); next(app); chooseTV("Samsung", app)
        tap("Setup help", app)
        let help = app.scrollViews["setup-help-scroll"]
        tap("Home app (optional)", app, scroll: help)
        tap("Google Home", app, scroll: help)
        for _ in 0..<4 {
            help.swipeUp(velocity: .slow)
            guard help.exists else {
                screenshot("Help scrolling unexpectedly changed the page", app)
                XCTFail("Scrolling help must preserve its page: \(app.debugDescription)"); return
            }
            XCTAssertFalse(app.scrollViews["setup-scroll"].exists)
        }
        screenshot("Largest text help scroll keeps shortcuts idle", app)
    }
    private func checkSimplifiedSetup(large: Bool) {
        let app = XCUIApplication()
        app.launchArguments = ["-aqssGuideDismissedV1", "NO", "-aqssSetupProgressV1", "{}"]
        if large { app.launchArguments += ["-UIPreferredContentSizeCategoryName", "UICTContentSizeCategoryAccessibilityXXXL"] }
        continueAfterFailure = false
        app.launch()
        label("Step 1 of 5", app)
        XCTAssertFalse(app.buttons["more-features"].exists)
        XCTAssertTrue(app.buttons["guide-next"].isHittable)
        screenshot("Simplified welcome \(large)", app)
        next(app); label("Step 2 of 5", app)
        XCTAssertLessThan(app.buttons["guide-back"].frame.minX, app.frame.minX + app.frame.width * 0.25,
                          "Back must stay at the leading edge when it is the only footer action")
        XCTAssertFalse(app.buttons["choice-samsung"].exists)
        XCTAssertFalse(app.buttons["guide-next"].exists)
        tap("Identify TV from a photo", app)
        label("No photo selected", app)
        XCTAssertFalse(app.staticTexts["Model: Not identified"].exists)
        screenshot("Simplified photo \(large)", app)
        app.buttons["Close"].firstMatch.tap()
        label("Step 2 of 5", app)
        tap("Choose TV brand", app)
        XCTAssertTrue(app.textFields["brand-search"].waitForExistence(timeout: 5))
        app.textFields["brand-search"].tap(); app.textFields["brand-search"].typeText("Samsung")
        XCTAssertFalse(app.buttons["choice-lg"].exists)
        app.buttons["choice-samsung"].tap()
        label("Step 3 of 5", app)
        XCTAssertFalse(app.staticTexts["Use a home app?"].exists)
        XCTAssertTrue(app.buttons["setup-from-samsung"].isHittable)
        XCTAssertFalse(app.buttons["guide-next"].exists, "The picture action must be the only primary route")
        XCTAssertEqual(app.staticTexts["guide-device-context"].label, "Samsung  ·  iPhone")
        screenshot("Simplified TV plan \(large)", app)
        let exitFrame = app.buttons["exit-tutorial"].frame
        XCTAssertTrue(app.frame.contains(exitFrame), "Exit \(exitFrame) must remain inside \(app.frame)")
        tap("Setup help", app)
        let help = app.scrollViews["setup-help-scroll"]
        XCTAssertTrue(help.waitForExistence(timeout: 5))
        tap("Home app (optional)", app, scroll: help)
        tap("Google Home", app, scroll: help)
        XCTAssertTrue(help.buttons["Jump to Google Home pictures"].exists)
        tap("Jump to phone Wi-Fi pictures", app, scroll: help)
        label("iPhone — connect to your home Wi-Fi", app)
        app.buttons["setup-next"].tap()
        for n in 1...6 {
            label("Step \(n) of 6", app)
            app.buttons["setup-next"].tap()
        }
        label("Step 3 of 5", app)
        XCTAssertTrue(app.buttons["setup-from-samsung"].exists)
        tap("Show Samsung steps", app)
        XCTAssertTrue(app.buttons["setup-next"].waitForExistence(timeout: 5))
        app.buttons["setup-next"].tap(); label("Step 1 of 17", app)
        screenshot("Simplified TV picture \(large)", app)
        tap("? Step help", app)
        XCTAssertTrue(app.buttons["setup-picture-jump"].exists)
        app.buttons["setup-next"].tap(); label("Step 2 of 17", app)
        app.buttons["setup-back"].tap(); label("Step 1 of 17", app)
        app.buttons["setup-close"].tap(); label("Step 3 of 5", app)
        app.buttons["guide-back"].tap(); label("Step 2 of 5", app)
        tap("Choose TV brand", app); app.buttons["choice-samsung"].tap()
        label("Step 3 of 5", app)
        next(app); label("Step 4 of 5", app)
        XCTAssertTrue(app.buttons["Phone pictures"].isHittable)
        XCTAssertFalse(app.buttons["guide-next"].exists)
        next(app); label("Step 5 of 5", app)
        tap("Setup help", app)
        tap("Jump to voice check", app, scroll: app.scrollViews["setup-help-scroll"])
        label("Microphone off", app)
        XCTAssertTrue(app.buttons["voice-start-stop"].isEnabled)
        app.buttons["Close"].firstMatch.tap(); label("Step 5 of 5", app)
        tap("Setup help", app)
        tap("Jump to sound check", app, scroll: app.scrollViews["setup-help-scroll"])
        label("Microphone off", app)
        XCTAssertTrue(app.buttons["sound-check-start-stop"].isEnabled)
        tap("What does this show?", app, scroll: app.scrollViews["sound-check-scroll"])
        XCTAssertTrue(app.alerts["? Sound check help"].waitForExistence(timeout: 5))
        XCTAssertTrue(app.alerts.buttons["Jump to recent sound checks"].exists)
        app.alerts.buttons["Close"].tap()
        app.buttons["Close"].firstMatch.tap(); label("Step 5 of 5", app)
        next(app); label("Connection not verified", app)
        screenshot("Simplified Home \(large)", app)
        if app.buttons["page-picker"].exists { app.buttons["page-picker"].tap(); tap("Devices", app) }
        else { tab("devices", app) }
        XCTAssertFalse(app.buttons["TV photo setup"].exists)
        tap("Device help", app)
        tap("TV photo setup", app)
        label("No photo selected", app)
        app.buttons["Close"].firstMatch.tap()
        if app.buttons["page-picker"].exists { app.buttons["page-picker"].tap(); tap("Insights", app) }
        else { tab("insights", app) }
        XCTAssertFalse(app.buttons["Explore an example"].exists)
        tap("Insights help", app)
        tap("Explore an example", app)
        label("EXAMPLE · synthetic data", app)
        if app.buttons["page-picker"].exists { app.buttons["page-picker"].tap(); tap("Sound", app) }
        else { tab("sound", app) }
        XCTAssertTrue(app.buttons["more-sound-tools"].waitForExistence(timeout: 5))
        XCTAssertFalse(app.buttons["test-setup-open"].exists)
        tap("More sound tools", app)
        XCTAssertTrue(app.buttons["test-setup-open"].exists)
        screenshot("Simplified sound tools \(large)", app)
        if app.buttons["page-picker"].exists { app.buttons["page-picker"].tap(); tap("Settings", app) }
        else { tab("settings", app) }
        XCTAssertTrue(app.buttons["appearance-picker"].waitForExistence(timeout: 5))
        XCTAssertFalse(app.buttons["Advanced Settings"].exists)
        tap("More settings", app)
        tap("Advanced Settings", app)
        XCTAssertTrue(app.switches["setting-background"].waitForExistence(timeout: 5))
        screenshot("Simplified advanced settings \(large)", app)
        app.buttons["page-back"].tap()
        XCTAssertTrue(app.buttons["appearance-picker"].waitForExistence(timeout: 5))
    }

    private let setupAnswers = [
        ("playback_phone", "Android 16 test phone"), ("intended_output", "Phone speaker"),
        ("observer_phone", "iPhone iOS 26"), ("recording_app", "Voice Memos mode unknown"),
        ("placement", "Two phones on table"), ("constraints", "No calibration")
    ]

    private func openTestSetup(_ app: XCUIApplication) throws {
        if app.buttons["page-picker"].exists {
            app.buttons["page-picker"].tap()
            let menu = app.scrollViews["menu-scroll"]
            tap("Sound", app, scroll: menu)
            let closed = XCTNSPredicateExpectation(predicate: NSPredicate(format: "exists == false"), object: menu)
            XCTAssertEqual(XCTWaiter.wait(for: [closed], timeout: 5), .completed)
        } else {
            tab("sound", app)
        }
        if !app.buttons["test-setup-open"].exists { tap("More sound tools", app) }
        let entry = app.buttons["test-setup-open"]
        guard entry.waitForExistence(timeout: 5) else {
            screenshot("Test setup entry missing from Sound", app)
            XCTFail("Sound has no Test setup worksheet entry")
            throw NSError(domain: "AQSSTestSetup", code: 1)
        }
        tap("Test setup", app)
        XCTAssertTrue(app.buttons["test-setup-review"].waitForExistence(timeout: 5))
    }

    private func fillTestSetup(_ app: XCUIApplication) {
        let scroll = app.scrollViews["test-setup-form"]
        for (id, value) in setupAnswers {
            let field = app.textFields["test-setup-" + id]
            for _ in 0..<10 {
                let viewport = scroll.frame.intersection(app.frame).insetBy(dx: 0, dy: 15)
                if field.isHittable && viewport.contains(CGPoint(x: field.frame.midX, y: field.frame.midY)) { break }
                scroll.swipeUp(velocity: .slow)
            }
            XCTAssertTrue(field.isHittable, id); field.tap(); field.typeText(value + "\n")
        }
    }

    private func inspectTestSetupShare(_ app: XCUIApplication, copy: Bool) throws {
        fillTestSetup(app)
        app.buttons["test-setup-review"].tap()
        let preview = app.staticTexts["test-setup-preview"]
        XCTAssertTrue(preview.waitForExistence(timeout: 5))
        let reviewed = preview.label
        XCTAssertTrue(reviewed.hasPrefix("Audio Bodyguard test setup (v1)\n"))
        for (_, value) in setupAnswers { XCTAssertTrue(reviewed.contains("\"\(value)\""), value) }
        XCTAssertTrue(reviewed.contains("Actual playback route: Unknown"))
        XCTAssertTrue(reviewed.contains("Physical output and protection: Not verified"))
        XCTAssertTrue(app.staticTexts["test-setup-notice"].isHittable)
        XCTAssertFalse(app.cells["Copy"].firstMatch.exists)
        let attachment = XCTAttachment(string: reviewed)
        attachment.name = "Test setup reviewed text"; attachment.lifetime = .keepAlways; add(attachment)
        screenshot("Test setup reviewed before sharing", app)
        let share = app.buttons["test-setup-share"]
        XCTAssertTrue(share.isHittable); share.tap()
        let nativeCopy = app.cells["Copy"].firstMatch
        guard nativeCopy.waitForExistence(timeout: 8) else {
            screenshot("Test setup share did not open", app)
            XCTFail("Native Copy is missing; Share enabled=\(share.isEnabled): \(app.debugDescription)")
            throw NSError(domain: "AQSSTestSetup", code: 4)
        }
        screenshot("Test setup native share UI", app)
        XCTAssertFalse(share.isEnabled, "Keep one Share request owned until native dismissal")
        if copy { nativeCopy.tap() }
        else if UIDevice.current.userInterfaceIdiom == .pad {
            let heading = app.staticTexts["test-setup-heading"]
            let point = heading.coordinate(withNormalizedOffset: CGVector(dx: 0.5, dy: 0.5))
            let popover = app.popovers.firstMatch
            guard heading.exists, popover.exists, app.frame.contains(point.screenPoint), !popover.frame.contains(point.screenPoint) else {
                XCTFail("Require an observed heading point outside the native share popover")
                throw NSError(domain: "AQSSTestSetup", code: 2)
            }
            point.tap()
        } else {
            let close = app.navigationBars["UIActivityContentView"].buttons["Close"].firstMatch
            XCTAssertTrue(close.waitForExistence(timeout: 5)); close.tap()
        }
        let returned = XCTNSPredicateExpectation(predicate: NSPredicate(format: "enabled == true AND hittable == true"), object: share)
        XCTAssertEqual(XCTWaiter.wait(for: [returned], timeout: 8), .completed)
        XCTAssertFalse(nativeCopy.exists); XCTAssertEqual(preview.label, reviewed)
        screenshot("Test setup native sharing returns to frozen preview", app)
        app.buttons["test-setup-back"].tap()
        XCTAssertTrue(app.buttons["test-setup-clear"].isEnabled)
        app.buttons["test-setup-clear"].tap()
        XCTAssertFalse(app.buttons["test-setup-clear"].isEnabled)
        app.buttons["test-setup-review"].tap()
        XCTAssertTrue(preview.waitForExistence(timeout: 5))
        XCTAssertTrue(preview.label.contains("Playback phone: Unknown"))
        XCTAssertFalse(preview.label.contains("Android 16 test phone"))
        app.buttons["test-setup-back"].tap(); app.buttons["test-setup-back"].tap()
        XCTAssertTrue(app.buttons["test-setup-open"].waitForExistence(timeout: 5))
        XCTAssertEqual(app.alerts.count, 0)
    }

    func testTestSetupWorksheetCancelSharePreservesPreview() throws {
        let app = launch(); try openTestSetup(app); try inspectTestSetupShare(app, copy: false)
    }

    func testTestSetupWorksheetCopySharesExactReviewedText() throws {
        let app = launch(); try openTestSetup(app); try inspectTestSetupShare(app, copy: true)
    }

    func testTestSetupShareStartsWhenReviewAppears() throws {
        let app = launch(); try openTestSetup(app)
        for _ in 0..<3 {
            app.buttons["test-setup-review"].tap()
            let share = app.buttons["test-setup-share"]
            XCTAssertTrue(share.waitForExistence(timeout: 5)); share.tap()
            let copy = app.cells["Copy"].firstMatch
            guard copy.waitForExistence(timeout: 8) else {
                screenshot("Share requested as review appeared", app)
                XCTFail("Share must open from the newly attached review: \(app.debugDescription)"); return
            }
            XCTAssertFalse(share.isEnabled, "A visible native share must keep its request owned")
            copy.tap()
            let returned = XCTNSPredicateExpectation(predicate: NSPredicate(format: "enabled == true AND hittable == true"), object: share)
            XCTAssertEqual(XCTWaiter.wait(for: [returned], timeout: 8), .completed)
            XCTAssertTrue(app.staticTexts["test-setup-preview"].exists)
            app.buttons["test-setup-back"].tap()
        }
        screenshot("Three immediate report shares return to their caller", app)
    }

    func testTestSetupShareCancelAndReopenAtLargestText() throws {
        let app = launch(largeText: true)
        try openTestSetup(app)
        app.buttons["test-setup-review"].tap()
        let preview = app.staticTexts["test-setup-preview"]
        XCTAssertTrue(preview.waitForExistence(timeout: 5))
        let reviewed = preview.label
        let share = app.buttons["test-setup-share"]
        for _ in 0..<3 {
            XCTAssertTrue(share.isEnabled); XCTAssertTrue(share.isHittable); share.tap()
            let copy = app.cells["Copy"].firstMatch
            XCTAssertTrue(copy.waitForExistence(timeout: 8))
            XCTAssertFalse(share.isEnabled)
            if UIDevice.current.userInterfaceIdiom == .pad {
                let heading = app.staticTexts["test-setup-heading"]
                let point = heading.coordinate(withNormalizedOffset: CGVector(dx: 0.5, dy: 0.5))
                let popover = app.popovers.firstMatch
                XCTAssertTrue(popover.exists)
                XCTAssertFalse(popover.frame.contains(point.screenPoint))
                point.tap()
            } else {
                let close = app.navigationBars["UIActivityContentView"].buttons["Close"].firstMatch
                XCTAssertTrue(close.waitForExistence(timeout: 5)); close.tap()
            }
            let returned = XCTNSPredicateExpectation(predicate: NSPredicate(format: "enabled == true AND hittable == true"), object: share)
            XCTAssertEqual(XCTWaiter.wait(for: [returned], timeout: 8), .completed)
            XCTAssertFalse(copy.exists); XCTAssertEqual(preview.label, reviewed)
        }
        screenshot("Largest text repeated native Cancel preserves the reviewed report", app)
        XCTAssertEqual(app.alerts.count, 0)
    }

    func testTestSetupWorksheetRotationClearCloseAndRestart() throws {
        let app = launch(); try openTestSetup(app)
        XCTAssertFalse(app.buttons["test-setup-clear"].isEnabled)
        app.buttons["test-setup-review"].tap()
        let preview = app.staticTexts["test-setup-preview"]
        XCTAssertTrue(preview.waitForExistence(timeout: 5)); XCTAssertTrue(preview.label.contains("Playback phone: Unknown"))
        app.buttons["test-setup-back"].tap(); fillTestSetup(app)
        XCUIDevice.shared.orientation = .landscapeLeft
        app.buttons["test-setup-review"].tap()
        XCTAssertTrue(preview.waitForExistence(timeout: 5)); let reviewed = preview.label
        XCTAssertTrue(reviewed.contains("Phone speaker"))
        XCUIDevice.shared.orientation = .portrait
        XCTAssertTrue(preview.waitForExistence(timeout: 5))
        XCTAssertEqual(preview.label, reviewed, "Portrait return must preserve the reviewed copy")
        screenshot("Test setup portrait retains the reviewed copy", app)
        XCUIDevice.shared.press(.home); app.activate()
        guard preview.waitForExistence(timeout: 5) else {
            screenshot("Test setup background preview missing", app)
            XCTFail("Background return must preserve the reviewed copy: \(app.debugDescription)")
            throw NSError(domain: "AQSSTestSetup", code: 3)
        }
        XCTAssertEqual(preview.label, reviewed)
        screenshot("Test setup rotation and background preserve reviewed notes", app)
        app.buttons["test-setup-back"].tap(); app.buttons["test-setup-back"].tap()
        app.buttons["test-setup-open"].tap()
        XCTAssertFalse(app.buttons["test-setup-clear"].isEnabled)
        fillTestSetup(app); app.buttons["test-setup-review"].tap()
        app.terminate(); app.launch(); try openTestSetup(app)
        XCTAssertFalse(app.buttons["test-setup-clear"].isEnabled)
        app.buttons["test-setup-back"].tap(); app.terminate()
        app.launchArguments += ["-UIPreferredContentSizeCategoryName", "UICTContentSizeCategoryAccessibilityXXXL"]
        app.launch(); try openTestSetup(app); app.buttons["test-setup-review"].tap()
        XCTAssertTrue(preview.waitForExistence(timeout: 5))
        XCTAssertTrue(app.buttons["test-setup-share"].isHittable)
        XCTAssertEqual(app.buttons["test-setup-share"].label, "Share setup report")
        XCTAssertTrue(app.buttons["test-setup-back"].isHittable)
        XCTAssertTrue(app.staticTexts["test-setup-notice"].isHittable)
        screenshot("Test setup largest text keeps review navigation and notice reachable", app)
        XCTAssertFalse(app.buttons["sound-check-start-stop"].exists)
        XCTAssertEqual(app.alerts.count, 0)
    }

    func testInsightsRecapReportPreviewReturnsWithoutCapture() throws {
        let app = launch()
        tab("insights", app); try openInsightsRecaps(app)
        try inspectRecapReport(app, completed: false)
        XCTAssertFalse(app.scrollViews["sound-check-scroll"].exists)
        XCTAssertFalse(app.buttons["sound-check-start-stop"].exists)
        XCTAssertEqual(app.alerts.count, 0)
        XCTAssertEqual(XCUIApplication(bundleIdentifier: "com.apple.springboard").alerts.count, 0)
        closeInsightsRecaps(app)
        app.buttons["page-back"].tap(); label("Connection not verified", app)
    }

    private func inspectRecapReport(_ app: XCUIApplication, completed: Bool, copy: Bool = false) throws {
        let environment = ProcessInfo.processInfo.environment
        let version = try XCTUnwrap(environment["AQSS_TEST_APP_VERSION"])
        let build = try XCTUnwrap(environment["AQSS_TEST_APP_BUILD"])
        let metadata = "Audio Bodyguard\nPlatform: iPhone/iPad\nVersion: \(version)\nBuild: \(build)"
        let checks = completed ? "Check 1: Input samples observed\nStopped by you" : "No completed sound checks in this app session."
        let expected = metadata + "\n\nRecent sound checks (this app session)\n" + checks +
            "\n\nInput observations only; not proof of sound safety, protection or TV control."
        let entry = app.buttons["recaps-review-support-report"]
        guard entry.waitForExistence(timeout: 5) else {
            screenshot("Missing support report review from recaps", app)
            XCTFail("Missing support report review from recaps")
            throw NSError(domain: "AQSSRecapReport", code: 1)
        }
        entry.tap()
        let preview = app.staticTexts["support-report-preview"]
        XCTAssertTrue(preview.waitForExistence(timeout: 5))
        XCTAssertEqual(preview.label, expected)
        let choice = app.switches["support-report-include-checks"]
        XCTAssertEqual(choice.value as? String, "1")
        XCTAssertFalse(app.cells["Copy"].firstMatch.exists, "Review must not open native sharing")
        choice.tap(); XCTAssertEqual(preview.label, metadata)
        choice.tap(); XCTAssertEqual(preview.label, expected)
        screenshot("Recap report preview contains only reviewed fields", app)
        if copy {
            tap("Share support report", app, scroll: app.scrollViews["recap-report-scroll"])
            let nativeCopy = app.cells["Copy"].firstMatch
            XCTAssertTrue(nativeCopy.waitForExistence(timeout: 8)); nativeCopy.tap()
            let share = app.buttons["share-support-report"]
            let returned = XCTNSPredicateExpectation(predicate: NSPredicate(format: "enabled == true AND hittable == true"), object: share)
            XCTAssertEqual(XCTWaiter.wait(for: [returned], timeout: 8), .completed)
            XCTAssertEqual(preview.label, expected)
        }
        choice.tap(); XCTAssertEqual(preview.label, metadata)
        app.buttons["recap-report-back"].tap()
        XCTAssertTrue(entry.waitForExistence(timeout: 5)); XCTAssertTrue(entry.isHittable)
        label(completed ? "Stopped by you" : "No completed sound checks in this app session.", app)
        screenshot("Report Back returns to the same recaps", app)
        entry.tap()
        XCTAssertTrue(preview.waitForExistence(timeout: 5))
        XCTAssertEqual(app.switches["support-report-include-checks"].value as? String, "1")
        XCTAssertEqual(preview.label, expected)
        app.buttons["recap-report-back"].tap()
        XCTAssertTrue(entry.isHittable)
    }

    func testInsightsRecapsStartEmptyAndReturnWithoutCapture() throws {
        let app = launch()
        tab("insights", app)
        try openInsightsRecaps(app)
        label("No completed sound checks in this app session.", app)
        label("Kept in memory; cleared when this app process ends.", app)
        XCTAssertFalse(app.buttons["sound-recaps-clear"].exists)
        XCTAssertFalse(app.scrollViews["sound-check-scroll"].exists)
        XCTAssertFalse(app.buttons["sound-check-start-stop"].exists)
        XCTAssertEqual(app.alerts.count, 0)
        XCTAssertEqual(XCUIApplication(bundleIdentifier: "com.apple.springboard").alerts.count, 0)
        screenshot("Insights recaps empty without opening capture", app)
        closeInsightsRecaps(app)
        label("No measurements yet", app)
        screenshot("Insights recap Close returns to Insights", app)
        app.buttons["page-back"].tap()
        label("Connection not verified", app)
    }

    func testInsightsRecapsReviewClearAndRestart() throws {
        guard ProcessInfo.processInfo.environment["AQSS_TEST_MIC_GRANTED"] == "1" else {
            XCTFail("The native workflow must establish microphone consent")
            throw NSError(domain: "AQSSInsightsRecaps", code: 2)
        }
        let app = launch()
        try finishActualSoundCheck(app)
        tab("insights", app); try openInsightsRecaps(app)
        label("Input samples observed", app); label("Stopped by you", app)
        XCTAssertFalse(app.scrollViews["sound-check-scroll"].exists)
        screenshot("Insights recaps show actual completed input", app)
        try inspectRecapReport(app, completed: true, copy: true)
        closeInsightsRecaps(app)
        try openInsightsRecaps(app)
        label("Input samples observed", app); label("Stopped by you", app)
        app.buttons["sound-recaps-clear"].tap()
        label("No completed sound checks in this app session.", app)
        XCTAssertFalse(app.buttons["sound-recaps-clear"].exists)
        screenshot("Insights Clear removes session recaps", app)
        closeInsightsRecaps(app)
        tab("sound", app); tap("Live sound check", app); openSoundRecaps(app)
        label("No completed sound checks in this app session.", app)
        closeSoundRecaps(app); app.buttons["Close"].firstMatch.tap()
        try finishActualSoundCheck(app)
        app.terminate(); app.launch()
        tab("insights", app); try openInsightsRecaps(app)
        label("No completed sound checks in this app session.", app)
        screenshot("Insights recaps are empty in a new process", app)
        closeInsightsRecaps(app)
        tab("home", app); label("Connection not verified", app)
    }

    private func openInsightsRecaps(_ app: XCUIApplication) throws {
        let entry = app.buttons["insights-sound-check-recaps"]
        guard entry.waitForExistence(timeout: 5) else {
            screenshot("Missing recent sound checks in Insights", app)
            XCTFail("Missing recent sound checks in Insights")
            throw NSError(domain: "AQSSInsightsRecaps", code: 1)
        }
        entry.tap()
        XCTAssertTrue(app.scrollViews["sound-recaps-scroll"].waitForExistence(timeout: 5))
        XCTAssertTrue(app.buttons["sound-recaps-close"].isHittable)
    }

    private func closeInsightsRecaps(_ app: XCUIApplication) {
        app.buttons["sound-recaps-close"].tap()
        let closed = XCTNSPredicateExpectation(predicate: NSPredicate(format: "exists == false"), object: app.scrollViews["sound-recaps-scroll"])
        XCTAssertEqual(XCTWaiter.wait(for: [closed], timeout: 5), .completed)
        label("Audio trends", app)
        XCTAssertTrue(app.buttons["insights-sound-check-recaps"].isHittable)
        XCTAssertFalse(app.scrollViews["sound-check-scroll"].exists)
    }

    private func finishActualSoundCheck(_ app: XCUIApplication) throws {
        tab("sound", app); tap("Live sound check", app)
        app.buttons["sound-check-start-stop"].tap()
        let status = app.staticTexts["sound-check-status"]
        let input = XCTNSPredicateExpectation(predicate: NSPredicate(format: "label CONTAINS %@", "Microphone samples received"), object: status)
        guard XCTWaiter.wait(for: [input], timeout: 8) == .completed else {
            screenshot("Support report requires actual native input", app)
            XCTFail("Require actual native samples before reporting observed input")
            throw NSError(domain: "AQSSSupportReport", code: 1)
        }
        app.buttons["sound-check-start-stop"].tap()
        label("No live input", app)
        openSoundRecaps(app); label("Input samples observed", app); label("Stopped by you", app)
        closeSoundRecaps(app); app.buttons["Close"].firstMatch.tap()
    }

    func testPrivateSupportReportIncludesCompletedCheckAndClears() throws {
        try inspectCompletedSupportReport(buildOnly: false)
    }

    func testPrivateSupportReportExcludesCompletedCheckWithoutClearing() throws {
        try inspectCompletedSupportReport(buildOnly: true)
    }

    private func inspectCompletedSupportReport(buildOnly: Bool) throws {
        guard ProcessInfo.processInfo.environment["AQSS_TEST_MIC_GRANTED"] == "1" else {
            throw XCTSkip("The native workflow must establish microphone consent.")
        }
        let environment = ProcessInfo.processInfo.environment
        let version = try XCTUnwrap(environment["AQSS_TEST_APP_VERSION"])
        let build = try XCTUnwrap(environment["AQSS_TEST_APP_BUILD"])
        let metadata = "Audio Bodyguard\nPlatform: iPhone/iPad\nVersion: \(version)\nBuild: \(build)"
        let empty = metadata + "\n\nRecent sound checks (this app session)\nNo completed sound checks in this app session.\n\nInput observations only; not proof of sound safety, protection or TV control."
        let completed = metadata + "\n\nRecent sound checks (this app session)\nCheck 1: Input samples observed\nStopped by you\n\nInput observations only; not proof of sound safety, protection or TV control."
        let app = launch()
        func openReport(_ expected: String) {
            tab("settings", app); tap("Advanced Settings", app); tap("About Private support report", app)
            label(expected, app)
            XCTAssertTrue(app.buttons["share-support-report"].exists)
        }
        func closeReport() {
            app.buttons["setting-help-close"].tap(); label("Advanced Settings", app)
            app.buttons["page-back"].tap(); label("Appearance", app)
        }
        try finishActualSoundCheck(app)
        openReport(completed)
        screenshot("Support report contains only the completed input recap", app)
        if buildOnly {
            let choice = app.switches["support-report-include-checks"]
            XCTAssertTrue(choice.waitForExistence(timeout: 5), "Missing Include recent sound checks choice")
            XCTAssertEqual(choice.value as? String, "1")
            choice.tap()
            XCTAssertEqual(choice.value as? String, "0")
            XCTAssertEqual(app.staticTexts["support-report-preview"].label, metadata)
            screenshot("Completed sound check excluded from build-only report", app)
        }
        tap("Share support report", app)
        let copy = app.cells["Copy"].firstMatch
        XCTAssertTrue(copy.waitForExistence(timeout: 8)); copy.tap()
        let share = app.buttons["share-support-report"]
        let returned = XCTNSPredicateExpectation(predicate: NSPredicate(format: "enabled == true AND hittable == true"), object: share)
        XCTAssertEqual(XCTWaiter.wait(for: [returned], timeout: 8), .completed)
        XCTAssertFalse(copy.exists); label(buildOnly ? metadata : completed, app)
        if buildOnly {
            XCTAssertEqual(app.staticTexts["support-report-preview"].label, metadata)
            XCTAssertEqual(app.switches["support-report-include-checks"].value as? String, "0")
        }
        screenshot("Completed support report native Copy returns to preview", app)
        closeReport()
        tab("sound", app); tap("Live sound check", app); openSoundRecaps(app)
        label("Stopped by you", app)
        app.buttons["sound-recaps-clear"].tap(); label("No completed sound checks in this app session.", app)
        closeSoundRecaps(app); app.buttons["Close"].firstMatch.tap()
        openReport(empty); screenshot("New support report after Clear is empty", app); closeReport()
        try finishActualSoundCheck(app)
        // End a process that really has a completed recap; restart must discard it.
        app.terminate(); app.launch()
        openReport(empty); screenshot("New process support report is empty", app); closeReport()
        tab("home", app); label("Connection not verified", app)
    }

    func testPrivateSupportReportBuildOnlyCancelReturnsWithoutCopy() throws {
        try inspectBuildDetailsShare(copyDetails: false, supportReport: true, buildOnly: true)
    }

    func testPrivateSupportReportBuildOnlyCopySharesOnlyBuildDetails() throws {
        try inspectBuildDetailsShare(copyDetails: true, supportReport: true, buildOnly: true)
    }

    func testPrivateSupportReportCancelReturnsWithoutCopy() throws {
        try inspectBuildDetailsShare(copyDetails: false, supportReport: true)
    }

    func testPrivateSupportReportSharesOnlyPreviewedFieldsAndReturns() throws {
        try inspectBuildDetailsShare(copyDetails: true, supportReport: true)
    }

    func testBuildDetailsShareOnlyInstalledMetadataAndReturn() throws {
        try inspectBuildDetailsShare(copyDetails: true)
    }

    func testBuildDetailsShareCancelReturnsWithoutCopy() throws {
        try inspectBuildDetailsShare(copyDetails: false)
    }

    private func inspectBuildDetailsShare(copyDetails: Bool, supportReport: Bool = false, buildOnly: Bool = false) throws {
        let environment = ProcessInfo.processInfo.environment
        guard let version = environment["AQSS_TEST_APP_VERSION"], !version.isEmpty,
              let build = environment["AQSS_TEST_APP_BUILD"], !build.isEmpty else {
            XCTFail("Require version and build from the compiled app's Info.plist")
            throw NSError(domain: "AQSSBuildShare", code: 1)
        }
        let app = launch()
        tab("settings", app)
        if supportReport { tap("Advanced Settings", app); tap("About Private support report", app) }
        else { tap("Build details", app) }
        let share = app.buttons[supportReport ? "share-support-report" : "share-build-details"]
        guard share.waitForExistence(timeout: 5) else {
            screenshot(supportReport ? "Share support report action missing" : "Share build details action missing", app)
            XCTFail(supportReport ? "Missing Share support report action" : "Missing Share build details action")
            throw NSError(domain: "AQSSBuildShare", code: 2)
        }
        var expected = "Audio Bodyguard\nPlatform: iPhone/iPad\nVersion: \(version)\nBuild: \(build)"
        if supportReport {
            expected += "\n\nRecent sound checks (this app session)\nNo completed sound checks in this app session.\n\nInput observations only; not proof of sound safety, protection or TV control."
            label("Review before sharing", app)
            label("No audio, recognized words, photos, TV or network details are included.", app)
        }
        if buildOnly {
            let choice = app.switches["support-report-include-checks"]
            guard choice.waitForExistence(timeout: 5) else {
                screenshot("Missing Include recent sound checks choice", app)
                XCTFail("Missing Include recent sound checks choice")
                throw NSError(domain: "AQSSSupportReportChoice", code: 1)
            }
            let full = expected
            let metadata = "Audio Bodyguard\nPlatform: iPhone/iPad\nVersion: \(version)\nBuild: \(build)"
            XCTAssertEqual(choice.value as? String, "1")
            choice.tap()
            XCTAssertEqual(choice.value as? String, "0")
            XCTAssertEqual(app.staticTexts["support-report-preview"].label, metadata)
            choice.tap()
            XCTAssertEqual(choice.value as? String, "1")
            XCTAssertEqual(app.staticTexts["support-report-preview"].label, full)
            choice.tap()
            expected = metadata
            XCTAssertEqual(app.staticTexts["support-report-preview"].label, expected)
            screenshot("Build-only report selected before explicit Share", app)
        }
        label(expected, app)
        let copy = app.cells["Copy"].firstMatch
        XCTAssertFalse(copy.exists, "Build details must preview without opening the share sheet")
        screenshot("Build details preview before explicit Share", app)
        if supportReport { tap("Share support report", app) } else { share.tap() }
        guard copy.waitForExistence(timeout: 8) else {
            screenshot("Native share sheet unavailable", app)
            XCTFail("Require the native share sheet's Copy action: \(app.debugDescription)")
            throw NSError(domain: "AQSSBuildShare", code: 3)
        }
        screenshot("Native build details share sheet", app)
        if UIDevice.current.userInterfaceIdiom == .pad {
            // Tap an observed point inside this app but outside its share popover.
            // The app-window edge can lie outside the inset iPad presentation.
            let preview = app.scrollViews["setting-help-scroll"].staticTexts
                .matching(NSPredicate(format: "label BEGINSWITH %@", expected)).firstMatch
            let cancelPoint = preview.coordinate(withNormalizedOffset: CGVector(dx: supportReport ? 0.1 : 0.5, dy: supportReport ? 0.1 : 0.5))
            let popover = app.popovers.firstMatch
            guard preview.exists, popover.exists,
                  app.scrollViews["setting-help-scroll"].frame.contains(cancelPoint.screenPoint),
                  !popover.frame.contains(cancelPoint.screenPoint) else {
                XCTFail("Require an observed preview point outside the native share popover")
                throw NSError(domain: "AQSSBuildShare", code: 5)
            }
            cancelPoint.tap()
        } else {
            let close = app.navigationBars["UIActivityContentView"].buttons["Close"].firstMatch
            guard close.waitForExistence(timeout: 5) else {
                screenshot("Native share-sheet close control unavailable", app)
                XCTFail("Require the observed native share-sheet Close control: \(app.debugDescription)")
                throw NSError(domain: "AQSSBuildShare", code: 4)
            }
            close.tap()
        }
        let closed = XCTNSPredicateExpectation(predicate: NSPredicate(format: "exists == false"), object: copy)
        guard XCTWaiter.wait(for: [closed], timeout: 5) == .completed else {
            screenshot("Native share cancellation failed", app)
            XCTFail("Cancel must close the native share sheet: \(app.debugDescription)")
            throw NSError(domain: "AQSSBuildShare", code: 6)
        }
        XCTAssertTrue(share.isHittable)
        XCTAssertTrue(share.isEnabled)
        if buildOnly {
            XCTAssertEqual(app.switches["support-report-include-checks"].value as? String, "0")
            XCTAssertEqual(app.staticTexts["support-report-preview"].label, expected)
        }
        label(expected, app)
        screenshot("Cancel share returns to Build details", app)
        print("AQSS_BUILD_SHARE_UI: native cancel returned to the preview")
        if copyDetails {
            if supportReport { tap("Share support report", app) } else { share.tap() }
            XCTAssertTrue(copy.waitForExistence(timeout: 8))
            copy.tap()
            print("AQSS_BUILD_SHARE_UI: native Copy selected")
            let returned = XCTNSPredicateExpectation(
                predicate: NSPredicate(format: "enabled == true AND hittable == true"), object: share)
            guard XCTWaiter.wait(for: [returned], timeout: 8) == .completed else {
                screenshot("Native Copy did not return to Build details", app)
                XCTFail("Copy must return to an enabled Share control: \(app.debugDescription)")
                throw NSError(domain: "AQSSBuildShare", code: 7)
            }
            XCTAssertFalse(app.cells["Copy"].firstMatch.exists)
            label(expected, app)
            print("AQSS_BUILD_SHARE_UI: Copy returned to the preview; host verifies actual clipboard bytes")
            screenshot("System Copy returns to Build details", app)
        }
        XCTAssertFalse(XCUIApplication(bundleIdentifier: "com.apple.springboard").alerts.firstMatch.exists)
        app.buttons["setting-help-close"].tap()
        if supportReport {
            label("Advanced Settings", app)
            XCTAssertTrue(app.buttons["help-support"].exists)
            app.buttons["page-back"].tap()
        }
        label("Appearance", app)
        XCTAssertTrue(app.buttons["more-settings"].exists)
        XCTAssertFalse(app.scrollViews["setting-help-scroll"].exists)
        tab("home", app); label("Connection not verified", app)
    }

    func testBuildDetailsMatchInstalledMetadataAndReturnToSettings() throws {
        let environment = ProcessInfo.processInfo.environment
        guard let version = environment["AQSS_TEST_APP_VERSION"], !version.isEmpty,
              let build = environment["AQSS_TEST_APP_BUILD"], !build.isEmpty else {
            XCTFail("Require version and build from the compiled app's Info.plist")
            throw NSError(domain: "AQSSBuildDetails", code: 1)
        }
        let app = launch()
        tab("settings", app)
        label("Appearance", app)
        tap("More settings", app)
        guard app.buttons["Build details"].firstMatch.waitForExistence(timeout: 5) else {
            screenshot("Build details action missing in Settings", app)
            XCTFail("Missing Build details action")
            throw NSError(domain: "AQSSBuildDetails", code: 2)
        }
        tap("Build details", app)
        label("Version: \(version)\nBuild: \(build)", app)
        XCTAssertTrue(app.buttons["share-build-details"].exists)
        XCTAssertFalse(XCUIApplication(bundleIdentifier: "com.apple.springboard").alerts.firstMatch.exists)
        screenshot("Installed version and build from app metadata", app)
        app.buttons["setting-help-close"].tap()
        label("Appearance", app)
        XCTAssertTrue(app.buttons["more-settings"].exists)
        XCTAssertFalse(app.scrollViews["setting-help-scroll"].exists)
        tab("home", app)
        label("Connection not verified", app)
    }

    func testVoiceCheckStartsIdleAndClosingItLeavesMeterUsable() {
        let app = launch()
        tab("sound", app); tap("Voice check", app)
        label("Microphone off", app); label("No words recognized yet", app)
        XCTAssertEqual(app.buttons["voice-start-stop"].label, "Start voice check")
        XCTAssertFalse(app.buttons["voice-open-settings"].exists)
        XCTAssertFalse(app.alerts.firstMatch.exists)
        screenshot("Voice check idle with no microphone capture", app)
        app.buttons["Close"].firstMatch.tap()
        tap("Live sound check", app)
        label("Microphone off", app)
        XCTAssertTrue(app.buttons["sound-check-start-stop"].isEnabled)
        app.buttons["Close"].firstMatch.tap()
        tap("Voice check", app)
        label("Microphone off", app); label("No words recognized yet", app)
    }

    func testVoiceCheckDeniedMicrophoneCannotRequestSpeechOrCapture() throws {
        guard ProcessInfo.processInfo.environment["AQSS_TEST_MIC_DENIED"] == "1" else {
            throw XCTSkip("The focused workflow must establish denied microphone permission first.")
        }
        let app = launch()
        tab("sound", app); tap("Voice check", app)
        app.buttons["voice-start-stop"].tap()
        label("Microphone permission denied", app)
        label("No live microphone samples", app); label("No words recognized yet", app)
        XCTAssertEqual(app.buttons["voice-start-stop"].label, "Start voice check")
        XCTAssertFalse(app.alerts.firstMatch.exists)
        screenshot("Voice microphone denial keeps capture off", app)
        XCUIDevice.shared.press(.home); app.activate()
        XCTAssertEqual(app.buttons["voice-start-stop"].label, "Start voice check")
        label("No words recognized yet", app)
    }

    func testVoiceSpeechPermissionGrantDoesNotStartDeferredCapture() throws {
        guard ProcessInfo.processInfo.environment["AQSS_TEST_MIC_GRANTED"] == "1" else {
            throw XCTSkip("The focused workflow must grant microphone on a fresh Simulator without prior speech consent.")
        }
        let app = launch()
        tab("sound", app); tap("Voice check", app)
        app.buttons["voice-start-stop"].tap()
        let springboard = XCUIApplication(bundleIdentifier: "com.apple.springboard")
        let permission = springboard.alerts.firstMatch
        XCTAssertTrue(permission.waitForExistence(timeout: 8), "Speech consent must be requested before creating a recognizer")
        let allow = permission.buttons.matching(NSPredicate(format: "label IN %@", ["Allow", "OK"])).firstMatch
        XCTAssertTrue(allow.exists); allow.tap()
        let gone = XCTNSPredicateExpectation(predicate: NSPredicate(format: "exists == false"), object: permission)
        XCTAssertEqual(XCTWaiter.wait(for: [gone], timeout: 5), .completed)
        XCTAssertEqual(app.buttons["voice-start-stop"].label, "Start voice check")
        label("No live microphone samples", app); label("No words recognized yet", app)
        screenshot("Speech permission grant waits for a fresh Start", app)
        XCUIDevice.shared.press(.home); app.activate()
        XCTAssertEqual(app.buttons["voice-start-stop"].label, "Start voice check")
        app.buttons["Close"].firstMatch.tap()
        tap("Live sound check", app)
        app.buttons["sound-check-start-stop"].tap()
        let status = app.staticTexts["sound-check-status"]
        let observed = XCTNSPredicateExpectation(predicate: NSPredicate(format: "label CONTAINS %@", "Microphone samples received"), object: status)
        guard XCTWaiter.wait(for: [observed], timeout: 8) == .completed else {
            XCTAssertEqual(app.buttons["sound-check-start-stop"].label, "Start sound check")
            label("No live input", app)
            throw XCTSkip("This Simulator supplied no meter input after voice permission: \(status.label)")
        }
        screenshot("Meter remains usable after closing voice permission flow", app)
        app.buttons["sound-check-start-stop"].tap()
        label("No live input", app)
    }

    func testLiveSoundCheckStartsOffAndHelpReturnsWithoutCapture() {
        let app = launch()
        tab("sound", app); tap("Live sound check", app)
        label("Microphone off", app); label("No live input", app)
        XCTAssertEqual(app.buttons["sound-check-start-stop"].label, "Start sound check")
        XCTAssertFalse(app.buttons["sound-check-open-settings"].exists)
        XCTAssertFalse(app.alerts.firstMatch.exists)
        screenshot("Live sound check starts idle", app)
        app.buttons["sound-check-help"].tap()
        XCTAssertTrue(app.alerts["? Sound check help"].waitForExistence(timeout: 5))
        app.alerts.buttons["Close"].tap()
        let helpClosed = XCTNSPredicateExpectation(predicate: NSPredicate(format: "exists == false"), object: app.alerts.firstMatch)
        XCTAssertEqual(XCTWaiter.wait(for: [helpClosed], timeout: 5), .completed)
        label("Microphone stopped while help is open.", app)
        XCTAssertEqual(app.buttons["sound-check-start-stop"].label, "Start sound check")
        app.buttons["Close"].firstMatch.tap()
        label("SOUND", app)
        screenshot("Sound check close returns to Sound", app)
    }

    /// Run in the focused workflow after simctl has denied microphone permission.
    func testLiveSoundCheckDeniedPermissionNeverStartsCapture() throws {
        guard ProcessInfo.processInfo.environment["AQSS_TEST_MIC_DENIED"] == "1" else {
            throw XCTSkip("The focused workflow must establish denied microphone permission first.")
        }
        let app = launch()
        tab("sound", app); tap("Live sound check", app)
        app.buttons["sound-check-start-stop"].tap()
        label("Microphone permission denied", app)
        XCTAssertEqual(app.buttons["sound-check-start-stop"].label, "Start sound check")
        label("No live input", app)
        screenshot("Permission denial keeps microphone off", app)
        let settings = XCUIApplication(bundleIdentifier: "com.apple.Preferences")
        func openAppSettings() throws {
            let button = app.buttons["sound-check-open-settings"]
            guard button.waitForExistence(timeout: 5) else {
                XCTFail("Missing sound-check permission Settings shortcut")
                throw NSError(domain: "AQSSPermissionSettings", code: 1)
            }
            button.tap()
            XCTAssertTrue(settings.wait(for: .runningForeground, timeout: 8))
            // Cold Settings startup can outlast its foreground transition.
            guard settings.navigationBars["Audio Bodyguard"].waitForExistence(timeout: 20) else {
                screenshot("Settings destination unavailable", settings)
                XCTFail("Require this app's Settings page")
                throw NSError(domain: "AQSSPermissionSettings", code: 2)
            }
        }
        func returnToSoundCheckAfterPermissionChange() {
            app.activate()
            if !app.buttons["sound-check-start-stop"].waitForExistence(timeout: 3) {
                // iOS can terminate the app after a Settings permission change.
                // That OS launch has no UI-test arguments, so the first-visit
                // guide can appear. Use its actual Exit Home navigation.
                if app.buttons["exit-tutorial"].waitForExistence(timeout: 3) {
                    screenshot("Settings permission return shows first-visit guide", app)
                    exit(app)
                }
                XCTAssertTrue(app.buttons["tab-sound"].waitForExistence(timeout: 5))
                tab("sound", app); tap("Live sound check", app)
            }
        }
        try openAppSettings()
        app.activate()
        label("Microphone permission denied", app); label("No live input", app)
        XCTAssertEqual(app.buttons["sound-check-start-stop"].label, "Start sound check")
        screenshot("Settings return with permission denied stays off", app)
        try openAppSettings()
        let microphoneControls = settings.switches.matching(NSPredicate(format: "label CONTAINS %@", "Microphone"))
        let microphone = microphoneControls.firstMatch
        XCTAssertTrue(microphone.waitForExistence(timeout: 5), "Require the app's real microphone permission control")
        XCTAssertEqual(microphoneControls.count, 1, "Require one unambiguous microphone switch")
        XCTAssertEqual(microphone.value as? String, "0")
        screenshot("App Settings microphone denied", settings)
        // Settings exposes a full-width labeled switch row plus the smaller
        // toggle at its trailing edge. The row's center only taps its label.
        microphone.coordinate(withNormalizedOffset: CGVector(dx: 0.88, dy: 0.5)).tap()
        let allowed = XCTNSPredicateExpectation(predicate: NSPredicate(format: "value == %@", "1"), object: microphone)
        guard XCTWaiter.wait(for: [allowed], timeout: 8) == .completed else {
            screenshot("Settings microphone grant failed", settings)
            XCTFail("The real microphone switch must become enabled")
            throw NSError(domain: "AQSSPermissionSettings", code: 3)
        }
        screenshot("App Settings microphone granted", settings)
        returnToSoundCheckAfterPermissionChange()
        // The OS may relaunch the app after a permission change. Both paths
        // must stay off and wait for another deliberate Start.
        label("No live input", app)
        XCTAssertEqual(app.buttons["sound-check-start-stop"].label, "Start sound check")
        XCTAssertFalse(app.buttons["sound-check-open-settings"].exists)
        XCTAssertFalse(app.staticTexts.matching(NSPredicate(format: "label CONTAINS %@", "Microphone permission denied")).firstMatch.exists)
        screenshot("Settings permission grant waits for Start", app)
        // The focused workflow runs this after the denied-permission suite,
        // before the granted-input suite. No later test inherits its consent.
        openSoundRecaps(app)
        label("No completed sound checks in this app session.", app)
        screenshot("Settings permission grant creates no sound recap", app)
        closeSoundRecaps(app)

    }

    private func openVoicePermissionSettings(_ app: XCUIApplication, _ settings: XCUIApplication) throws {
        let button = app.buttons["voice-open-settings"]
        guard button.waitForExistence(timeout: 5) else {
            XCTFail("Missing voice permission Settings shortcut")
            throw NSError(domain: "AQSSVoicePermissionSettings", code: 1)
        }
        button.tap()
        XCTAssertTrue(settings.wait(for: .runningForeground, timeout: 8))
        guard settings.navigationBars["Audio Bodyguard"].waitForExistence(timeout: 20) else {
            screenshot("Voice Settings destination unavailable", settings)
            XCTFail("Require this app's actual Settings page")
            throw NSError(domain: "AQSSVoicePermissionSettings", code: 2)
        }
    }

    private func returnToVoiceAfterPermissionChange(_ app: XCUIApplication) {
        app.activate()
        if !app.buttons["voice-start-stop"].waitForExistence(timeout: 3) {
            if app.buttons["exit-tutorial"].waitForExistence(timeout: 3) { exit(app) }
            XCTAssertTrue(app.buttons["tab-sound"].waitForExistence(timeout: 5))
            tab("sound", app); tap("Voice check", app)
        }
    }

    private func assertVoicePermissionReturnIdle(_ app: XCUIApplication) {
        label("No live microphone samples", app); label("No words recognized yet", app)
        XCTAssertEqual(app.buttons["voice-start-stop"].label, "Start voice check")
        XCTAssertFalse(XCUIApplication(bundleIdentifier: "com.apple.springboard").alerts.firstMatch.exists)
    }

    /// Isolated after other denied tests; leaves real microphone access granted.
    func testVoiceMicrophoneSettingsReturnStaysOff() throws {
        guard ProcessInfo.processInfo.environment["AQSS_TEST_MIC_DENIED"] == "1" else {
            throw XCTSkip("The focused workflow must establish denied microphone permission.")
        }
        let app = launch()
        tab("sound", app); tap("Voice check", app)
        app.buttons["voice-start-stop"].tap()
        label("Microphone permission denied", app)
        assertVoicePermissionReturnIdle(app)
        let settings = XCUIApplication(bundleIdentifier: "com.apple.Preferences")
        try openVoicePermissionSettings(app, settings)
        app.activate()
        label("Microphone permission denied", app); assertVoicePermissionReturnIdle(app)
        screenshot("Voice Settings microphone denied return stays off", app)
        try openVoicePermissionSettings(app, settings)
        let controls = settings.switches.matching(NSPredicate(format: "label CONTAINS %@", "Microphone"))
        let microphone = controls.firstMatch
        XCTAssertTrue(microphone.waitForExistence(timeout: 5)); XCTAssertEqual(controls.count, 1)
        XCTAssertEqual(microphone.value as? String, "0")
        screenshot("Voice app Settings microphone denied", settings)
        microphone.coordinate(withNormalizedOffset: CGVector(dx: 0.88, dy: 0.5)).tap()
        let enabled = XCTNSPredicateExpectation(predicate: NSPredicate(format: "value == %@", "1"), object: microphone)
        XCTAssertEqual(XCTWaiter.wait(for: [enabled], timeout: 8), .completed)
        screenshot("Voice app Settings microphone granted", settings)
        returnToVoiceAfterPermissionChange(app)
        assertVoicePermissionReturnIdle(app)
        XCTAssertFalse(app.buttons["voice-open-settings"].exists)
        XCTAssertFalse(app.staticTexts.matching(NSPredicate(format: "label CONTAINS %@", "Microphone permission denied")).firstMatch.exists)
        screenshot("Voice Settings microphone grant waits for Start", app)
    }

    /// Runs alone on a fresh Simulator so speech consent has not been requested.
    func testVoiceSpeechSettingsReturnStaysOff() throws {
        guard ProcessInfo.processInfo.environment["AQSS_TEST_SPEECH_DENIED"] == "1" else {
            throw XCTSkip("The isolated workflow must grant microphone on a fresh Simulator.")
        }
        let app = launch()
        tab("sound", app); tap("Voice check", app)
        app.buttons["voice-start-stop"].tap()
        let consent = XCUIApplication(bundleIdentifier: "com.apple.springboard").alerts.firstMatch
        XCTAssertTrue(consent.waitForExistence(timeout: 8), "Require the real first speech consent prompt")
        let deny = consent.buttons.matching(NSPredicate(format: "label IN %@", ["Don’t Allow", "Don't Allow"])).firstMatch
        XCTAssertTrue(deny.exists); deny.tap()
        let gone = XCTNSPredicateExpectation(predicate: NSPredicate(format: "exists == false"), object: consent)
        XCTAssertEqual(XCTWaiter.wait(for: [gone], timeout: 5), .completed)
        assertVoicePermissionReturnIdle(app)
        let settings = XCUIApplication(bundleIdentifier: "com.apple.Preferences")
        try openVoicePermissionSettings(app, settings)
        let controls = settings.switches.matching(NSPredicate(format: "label CONTAINS %@", "Speech Recognition"))
        let speech = controls.firstMatch
        XCTAssertTrue(speech.waitForExistence(timeout: 5)); XCTAssertEqual(controls.count, 1)
        XCTAssertEqual(speech.value as? String, "0")
        screenshot("Voice app Settings speech denied", settings)
        app.activate()
        label("Speech permission denied", app); assertVoicePermissionReturnIdle(app)
        screenshot("Voice Settings speech denied return stays off", app)
        try openVoicePermissionSettings(app, settings)
        XCTAssertEqual(speech.value as? String, "0")
        speech.coordinate(withNormalizedOffset: CGVector(dx: 0.88, dy: 0.5)).tap()
        let enabled = XCTNSPredicateExpectation(predicate: NSPredicate(format: "value == %@", "1"), object: speech)
        XCTAssertEqual(XCTWaiter.wait(for: [enabled], timeout: 8), .completed)
        screenshot("Voice app Settings speech granted", settings)
        returnToVoiceAfterPermissionChange(app)
        assertVoicePermissionReturnIdle(app)
        XCTAssertFalse(app.buttons["voice-open-settings"].exists)
        XCTAssertFalse(app.staticTexts.matching(NSPredicate(format: "label CONTAINS %@", "Speech permission denied")).firstMatch.exists)
        screenshot("Voice Settings speech grant waits for Start", app)
    }

    /// A Simulator input attempt is explicitly not physical microphone qualification.
    func testLiveSoundCheckStopsOnHomeAndRequiresAnotherStart() throws {
        guard ProcessInfo.processInfo.environment["AQSS_TEST_MIC_GRANTED"] == "1" else {
            throw XCTSkip("The focused workflow must establish microphone permission first.")
        }
        let app = launch()
        tab("sound", app); tap("Live sound check", app)
        app.buttons["sound-check-start-stop"].tap()
        let status = app.staticTexts["sound-check-status"]
        let started = XCTNSPredicateExpectation(predicate: NSPredicate(format: "label CONTAINS %@", "Microphone samples received"), object: status)
        guard XCTWaiter.wait(for: [started], timeout: 8) == .completed else {
            screenshot("Simulator microphone unavailable", app)
            // Missing input must end capture and clear the display, never simulate bars.
            XCTAssertEqual(app.buttons["sound-check-start-stop"].label, "Start sound check")
            label("No live input", app)
            throw XCTSkip("This Simulator supplied no microphone samples: \(status.label)")
        }
        screenshot("Simulator input received", app)
        XCUIDevice.shared.press(.home)
        app.activate()
        label("No live input", app)
        XCTAssertEqual(app.buttons["sound-check-start-stop"].label, "Start sound check")
        screenshot("Home stops input without automatic restart", app)
        app.buttons["sound-check-start-stop"].tap()
        let resumed = XCTNSPredicateExpectation(predicate: NSPredicate(format: "label CONTAINS %@", "Microphone samples received"), object: status)
        XCTAssertEqual(XCTWaiter.wait(for: [resumed], timeout: 8), .completed)
        app.buttons["sound-check-start-stop"].tap()
        label("No live input", app)
        XCTAssertEqual(app.buttons["sound-check-start-stop"].label, "Start sound check")
        app.buttons["sound-check-start-stop"].tap()
        let expired = XCTNSPredicateExpectation(predicate: NSPredicate(format: "label CONTAINS %@", "30-second check finished"), object: status)
        XCTAssertEqual(XCTWaiter.wait(for: [expired], timeout: 34), .completed)
        label("No live input", app)
        XCTAssertEqual(app.buttons["sound-check-start-stop"].label, "Start sound check")
        screenshot("Thirty-second cap clears input", app)
        openSoundRecaps(app)
        label("Input samples observed", app)
        label("30-second limit reached", app)
        label("Stopped when the app lost focus", app)
        label("Stopped by you", app)
        screenshot("Recaps show input and actual stop reasons", app)
        closeSoundRecaps(app)
        app.buttons["Close"].firstMatch.tap()
        tap("Live sound check", app)
        openSoundRecaps(app)
        label("30-second limit reached", app)
        screenshot("Recaps survive closing and reopening meter", app)
        app.buttons["sound-recaps-clear"].tap()
        label("No completed sound checks in this app session.", app)
        screenshot("Clear removes input recaps", app)
        app.terminate(); app.launch()
        tab("sound", app); tap("Live sound check", app)
        openSoundRecaps(app)
        label("No completed sound checks in this app session.", app)
        screenshot("New process starts with no input recaps", app)

    }

    func testTVChoiceOffersPhotoAndKeepsOtherBrandsOnDemand() {
        let app = launch(true)
        next(app); label("Step 2 of 5", app)
        XCTAssertTrue(app.buttons["identify-tv-photo"].exists)
        XCTAssertFalse(app.buttons["choice-philips"].exists)
        tap("Identify TV from a photo", app); label("Find your TV details", app)
        app.buttons["Close"].firstMatch.tap(); label("Step 2 of 5", app)
        chooseTV("Philips", app)
        XCTAssertTrue(app.buttons["setup-from-philips"].exists)
        app.buttons["guide-back"].tap(); label("Step 2 of 5", app)
        chooseTV("Philips", app)
        XCTAssertTrue(app.buttons["setup-from-philips"].exists)
        screenshot("Searchable brands and photo cancellation return to TV selection", app)
    }

    func testConnectedDemoAppearanceKeepsPhysicalReadinessUnverified() throws {
        #if AQSS_CONNECTED_DEMO
        let app = launch(true)
        label("HOME", app)
        XCTAssertEqual(app.staticTexts["connection-status"].label, "Connected")
        XCTAssertEqual(app.staticTexts["connection-demo-notice"].label, "Appetize demo")
        XCTAssertEqual(app.images["connection-head"].label, "AI head. Connected appearance demonstration.")
        screenshot("Connected demo colored head and original white rose", app)
        tap("Status help", app)
        label("Unknown physical state", app); label("No output observation", app)
        label("No physical TV connection or audio protection is verified.", app)
        screenshot("Connected appearance keeps physical status unverified", app)
        tap("Hide status help", app)
        tab("devices", app)
        app.buttons["page-back"].tap()
        XCTAssertEqual(app.staticTexts["connection-status"].label, "Connected")
        tab("settings", app); tap("Advanced Settings", app)
        app.switches["setting-captions"].tap()
        let attempt = app.staticTexts["not-connected-captions"]
        XCTAssertTrue(attempt.waitForExistence(timeout: 1))
        let reset = XCTNSPredicateExpectation(predicate: NSPredicate(format: "exists == false"), object: attempt)
        XCTAssertEqual(XCTWaiter.wait(for: [reset], timeout: 3.5), .completed)
        XCTAssertTrue(["Off", "0"].contains(app.switches["setting-captions"].value as? String ?? ""), "Demo artwork must not authorize a setting")
        tab("home", app)
        tap("TV & smart-home guide", app); label("Step 1 of 5", app)
        next(app); label("Step 2 of 5", app)
        exit(app); label("HOME", app)
        XCTAssertEqual(app.staticTexts["connection-status"].label, "Connected")
        tap("Back to Tutorial", app); label("Step 2 of 5", app)
        screenshot("Connected demo exact tutorial resume", app)
        #else
        throw XCTSkip("Connected appearance is tested only in the separate Simulator demo build.")
        #endif
    }

    func testRoseExitResumesTheExactTutorialAndHeadStaysDisconnected() {
        let app = launch(true)
        next(app); chooseTV("LG", app); chooseHome("Google Home", app)
        tap("Setup help", app)
        tap("Jump to Google Home pictures", app, scroll: app.scrollViews["setup-help-scroll"])
        label("LG ThinQ → Google Home", app)
        XCTAssertTrue(app.buttons["setup-next"].exists)
        XCTAssertFalse(app.buttons["setup-route-google_samsung"].exists)
        XCTAssertEqual(app.buttons["setup-close"].label, "Back to Tutorial")
        app.buttons["setup-close"].tap(); label("Step 3 of 5", app)
        exit(app); label("HOME", app); label("Connection not verified", app)
        XCTAssertTrue(app.images["connection-head"].label.contains("Black and white"))
        tap("Back to Tutorial", app); label("Step 3 of 5", app)
        app.buttons["guide-back"].tap(); label("Step 2 of 5", app)
        chooseTV("LG", app)
        tap("Setup help", app)
        XCTAssertTrue(app.buttons["Jump to Google Home pictures"].waitForExistence(timeout: 5))
        screenshot("Rose navigation resumes the selected TV and optional home app", app)
    }

    private func openSoundRecaps(_ app: XCUIApplication) {
        tap("What does this show?", app, scroll: app.scrollViews["sound-check-scroll"])
        let help = app.alerts["? Sound check help"]
        XCTAssertTrue(help.waitForExistence(timeout: 5))
        help.buttons["Jump to recent sound checks"].tap()
        XCTAssertTrue(app.scrollViews["sound-recaps-scroll"].waitForExistence(timeout: 5))
    }

    private func closeSoundRecaps(_ app: XCUIApplication) {
        app.buttons["sound-recaps-close"].tap()
        let closed = XCTNSPredicateExpectation(predicate: NSPredicate(format: "exists == false"), object: app.scrollViews["sound-recaps-scroll"])
        XCTAssertEqual(XCTWaiter.wait(for: [closed], timeout: 5), .completed)
        // The meter header is fixed above its scroll view. Pulling down here
        // can dismiss the meter sheet instead of merely returning from recaps.
        XCTAssertTrue(app.scrollViews["sound-check-scroll"].waitForExistence(timeout: 5))
        XCTAssertTrue(app.buttons["Close"].firstMatch.waitForExistence(timeout: 5))
        XCTAssertTrue(app.buttons["Close"].firstMatch.isHittable)
    }
    private func label(_ text: String, _ app: XCUIApplication, timeout: TimeInterval = 10) {
        XCTAssertTrue(app.staticTexts.containing(NSPredicate(format: "label CONTAINS %@", text)).firstMatch.waitForExistence(timeout: timeout), "Missing: \(text)")
    }
    private func tap(_ title: String, _ app: XCUIApplication, scroll explicitScroll: XCUIElement? = nil) {
        // Connection picture actions are pinned below the guide's scroll view.
        // Keep testing their real hit targets instead of searching the content
        // viewport for a control that intentionally lives outside it.
        let isPictureAction = title == "Phone pictures" || title == "Help identify my TV"
            || (title.hasPrefix("Show ") && title.hasSuffix(" steps"))
        if isPictureAction, explicitScroll == nil, app.scrollViews["guide-scroll"].exists,
           !app.scrollViews["setup-scroll"].exists, !app.scrollViews["setup-help-scroll"].exists {
            let pinned = app.buttons.matching(NSPredicate(format: "identifier BEGINSWITH %@ AND label CONTAINS %@", "setup-from-", title)).firstMatch
            let phone = app.buttons.matching(NSPredicate(format: "label == %@", "Phone pictures")).firstMatch
            let action = title == "Phone pictures" ? phone : pinned
            if action.exists {
                XCTAssertTrue(action.isHittable, "Pinned picture action must be reachable: \(title)")
                XCTAssertTrue(app.frame.contains(action.frame), "Pinned picture action must stay on screen: \(title)")
                action.tap(); return
            }
        }
        if !app.buttons.matching(NSPredicate(format: "label CONTAINS %@", title)).firstMatch.exists {
            if ["Advanced Settings", "Build details"].contains(title), app.buttons["more-settings"].exists {
                tap("More settings", app)
            } else if ["TV photo setup", "Illustrated setup guides"].contains(title), app.buttons.matching(NSPredicate(format: "label CONTAINS %@", "Device help")).firstMatch.exists {
                tap("Device help", app)
            } else if title == "Explore an example", app.buttons["insights-help"].exists {
                tap("Insights help", app)
            }
        }
        // Match within the active surface. A sheet can coexist with an
        // identically named button on the page underneath it.
        let scroll = explicitScroll ?? (app.scrollViews["setup-help-scroll"].exists ? app.scrollViews["setup-help-scroll"] : app.scrollViews["photo-review-scroll"].exists ? app.scrollViews["photo-review-scroll"] : app.scrollViews["setup-scroll"].exists ? app.scrollViews["setup-scroll"] : app.scrollViews["setting-help-scroll"].exists ? app.scrollViews["setting-help-scroll"] : app.scrollViews["menu-scroll"].exists ? app.scrollViews["menu-scroll"] : app.scrollViews["guide-scroll"].exists ? app.scrollViews["guide-scroll"] : app.scrollViews["sound-check-scroll"].exists ? app.scrollViews["sound-check-scroll"] : app.scrollViews["home-scroll"])
        let button = scroll.buttons.matching(NSPredicate(format: "label CONTAINS %@", title)).firstMatch
        // Recent SwiftUI versions can omit offscreen rows from an AX snapshot.
        // Search the scroll surface before deciding that a control is missing.
        _ = button.waitForExistence(timeout: 3)
        // isHittable alone can describe a sliver under a fixed bar. Require a
        // usable visible target inside the content viewport, then tap its
        // intersection center below. Requiring the original row's center can
        // oscillate past tall accessibility rows even when a safe target exists.
        func insideViewport(_ frame: CGRect) -> Bool {
            let viewport = scroll.frame.intersection(app.frame).insetBy(dx: 0, dy: 24)
            let visible = frame.intersection(viewport)
            return !visible.isNull && visible.height >= min(44, frame.height)
                && visible.width >= min(44, frame.width)
        }
        var below = true
        for _ in 0..<16 {
            guard scroll.exists else {
                screenshot("Changed scroll surface while seeking \(title)", app)
                XCTFail("Scroll surface changed while seeking \(title): \(app.debugDescription)"); return
            }
            if button.exists {
                let frame = button.frame
                if frame.width > 0 && frame.height > 0 {
                    if button.isHittable && insideViewport(frame) { break }
                    below = frame.midY >= scroll.frame.intersection(app.frame).midY
                }
            }
            // Use XCTest's native scrolling gesture. A synthesized press/drag
            // can become a button activation when SwiftUI relayouts a sheet.
            print("AQSS_UI_SCROLL target=\(title) scroll=\(scroll.frame) forward=\(below)")
            if below { scroll.swipeUp(velocity: .slow) }
            else { scroll.swipeDown(velocity: .slow) }
        }
        guard button.exists && button.isHittable && insideViewport(button.frame) else {
            screenshot("Unreachable \(title)", app)
            XCTFail("Unreachable button within content viewport: \(title)"); return
        }
        let appFrame = app.frame
        let visible = button.frame.intersection(scroll.frame.intersection(appFrame).insetBy(dx: 0, dy: 24))
        app.coordinate(withNormalizedOffset: .zero).withOffset(CGVector(dx: visible.midX - appFrame.minX, dy: visible.midY - appFrame.minY)).tap()
    }
    private func launch(_ firstVisit: Bool = false, largeText: Bool = false) -> XCUIApplication {
        let app = XCUIApplication()
        app.launchArguments = ["-aqssGuideDismissedV1", firstVisit ? "NO" : "YES"]
        if largeText { app.launchArguments += ["-UIPreferredContentSizeCategoryName", "UICTContentSizeCategoryAccessibilityXXXL"] }
        app.launch(); return app
    }
    private func next(_ app: XCUIApplication) {
        if app.buttons["guide-next"].exists { app.buttons["guide-next"].tap(); return }
        // Tests that deliberately omit pictures must take the same explicit Help path as a user.
        tap("Setup help", app)
        tap("Continue without pictures", app, scroll: app.scrollViews["setup-help-scroll"])
    }
    private func exit(_ app: XCUIApplication) { app.buttons["exit-tutorial"].tap() }
    private func assertOnlyGuide(_ app: XCUIApplication) {
        XCTAssertFalse(app.buttons["tab-home"].exists)
        XCTAssertFalse(app.buttons["Help & tutorials"].exists)
        XCTAssertFalse(app.buttons["Jump to"].exists)
        XCTAssertFalse(app.scrollViews["home-scroll"].exists)
        XCTAssertTrue(app.buttons["exit-tutorial"].isHittable)
    }
    private func tab(_ id: String, _ app: XCUIApplication) {
        if app.buttons["page-picker"].exists {
            let titles = ["home": "Home", "sound": "Sound", "devices": "Devices", "insights": "Insights", "settings": "Settings"]
            app.buttons["page-picker"].tap()
            tap(titles[id]!, app, scroll: app.scrollViews["menu-scroll"])
            let dismissed = XCTNSPredicateExpectation(predicate: NSPredicate(format: "exists == false"), object: app.scrollViews["menu-scroll"])
            XCTAssertEqual(XCTWaiter.wait(for: [dismissed], timeout: 5), .completed)
        } else { app.buttons["tab-\(id)"].tap() }
    }

    private func chooseTV(_ title: String, _ app: XCUIApplication) {
        tap("Choose TV brand", app)
        let search = app.textFields["brand-search"]
        XCTAssertTrue(search.waitForExistence(timeout: 5))
        search.tap(); search.typeText(title)
        let choice = app.buttons.matching(NSPredicate(format: "label BEGINSWITH[cd] %@", title)).firstMatch
        XCTAssertTrue(choice.waitForExistence(timeout: 5)); choice.tap()
        label("Step 3 of 5", app)
    }
    private func chooseHome(_ title: String, _ app: XCUIApplication) {
        tap("Setup help", app)
        let help = app.scrollViews["setup-help-scroll"]
        let optional = app.buttons["optional-home-app"]
        XCTAssertTrue(optional.waitForExistence(timeout: 5))
        if optional.value as? String != "Expanded" { tap("Home app (optional)", app, scroll: help) }
        tap(title, app, scroll: help)
        app.buttons["Close"].firstMatch.tap()
        let closed = XCTNSPredicateExpectation(predicate: NSPredicate(format: "exists == false"), object: help)
        XCTAssertEqual(XCTWaiter.wait(for: [closed], timeout: 5), .completed)
    }
    private func showStepHelp(_ app: XCUIApplication) {
        let toggle = ["setup-step-details", "setup-details", "setup-platform-help", "setup-mismatch-details"]
            .map { app.buttons[$0] }.first { $0.exists }
        XCTAssertNotNil(toggle)
        if toggle?.value as? String != "Expanded" { tap("? Step help", app) }
    }
    private func hideStepHelp(_ app: XCUIApplication) {
        let toggle = ["setup-step-details", "setup-details", "setup-platform-help", "setup-mismatch-details"]
            .map { app.buttons[$0] }.first { $0.exists }
        if toggle?.value as? String == "Expanded" { tap("? Hide step help", app) }
    }
    private func assertNoPhotoBrand(_ app: XCUIApplication) {
        XCTAssertFalse(app.staticTexts.matching(NSPredicate(format: "label BEGINSWITH %@", "Brand:")).firstMatch.exists)
    }
    private func openTutorial(_ title: String, _ app: XCUIApplication) {
        app.buttons["Help & tutorials"].tap()
        let more = app.buttons["more-tutorials"]
        XCTAssertTrue(more.waitForExistence(timeout: 5))
        if more.value as? String != "Expanded" { tap("More tutorials", app) }
        tap(title, app, scroll: app.scrollViews["menu-scroll"])
    }
    private func chooseAppearance(_ title: String, _ app: XCUIApplication) {
        tap("Appearance:", app)
        let option = app.buttons[title].firstMatch
        XCTAssertTrue(option.waitForExistence(timeout: 5)); option.tap()
        XCTAssertTrue(app.buttons["appearance-picker"].waitForExistence(timeout: 5))
        XCTAssertEqual(app.buttons["appearance-picker"].label, "Appearance: " + title)
    }

    private func jump(_ title: String, _ app: XCUIApplication) {
        app.buttons["Jump to"].tap(); tap(title, app)
        // Wait for the native sheet animation before choosing the next scroll
        // surface. Its outgoing menu otherwise captures the next lookup.
        let dismissed = XCTNSPredicateExpectation(predicate: NSPredicate(format: "exists == false"), object: app.scrollViews["menu-scroll"])
        XCTAssertEqual(XCTWaiter.wait(for: [dismissed], timeout: 5), .completed, "Jump menu did not dismiss")
    }
    private func dismissSettingHelp(_ app: XCUIApplication) {
        let close = app.buttons["setting-help-close"]
        XCTAssertTrue(close.isHittable)
        close.tap()
        let dismissed = XCTNSPredicateExpectation(predicate: NSPredicate(format: "exists == false"), object: app.scrollViews["setting-help-scroll"])
        XCTAssertEqual(XCTWaiter.wait(for: [dismissed], timeout: 5), .completed)
    }
    private func screenshot(_ name: String, _ app: XCUIApplication) {
        let shot = XCTAttachment(screenshot: app.screenshot()); shot.name = name; shot.lifetime = .keepAlways; add(shot)
    }

    func testPhotoReviewGuidanceAndReplacement() throws {
        guard ProcessInfo.processInfo.environment["AQSS_TEST_PHOTO"] == "1" else {
            throw XCTSkip("The focused workflow must import the dated synthetic photo fixtures into Photos first.")
        }
        let app = launch()
        tab("devices", app); tap("TV photo setup", app)
        tap("Photo help", app, scroll: app.scrollViews["photo-review-scroll"])
        tap("Show photo details", app, scroll: app.scrollViews["photo-review-scroll"])
        let identified = ["Brand: VIZIO", "Model: V505M-K09", "TV IP hint: 10.20.30.40", "Nothing is connected."]
        func selectFixture(_ key: String = "AQSS_TEST_PHOTO_MODIFIED_AT", expected: [String] = []) throws {
            let modified = try XCTUnwrap(ProcessInfo.processInfo.environment[key].flatMap(TimeInterval.init))
            let date = DateFormatter(); date.locale = Locale(identifier: "en_US_POSIX"); date.dateFormat = "MMMM dd"
            let prefix = "Photo, " + date.string(from: Date(timeIntervalSince1970: modified)) + ", "
            tap("Choose a photo", app, scroll: app.scrollViews["photo-review-scroll"])
            // Match each fixture's capture date, never an assumed grid position.
            let images = app.images.matching(NSPredicate(format: "label BEGINSWITH %@", prefix))
            _ = images.firstMatch.waitForExistence(timeout: 10)
            let candidates = images.allElementsBoundByIndex.filter {
                // Current-year assets omit the year; an older same-day photo
                // has another comma after its year and is not our fresh fixture.
                !$0.label.dropFirst(prefix.count).contains(",")
            }
            let inventory = XCTAttachment(string: app.debugDescription)
            inventory.name = "System photo picker inventory"; inventory.lifetime = .keepAlways; add(inventory)
            if candidates.count != 1 {
                print("PHOTO_PICKER_INVENTORY " + app.debugDescription)
                screenshot("Missing or ambiguous dated photo fixture", app)
            }
            let image = try XCTUnwrap(candidates.count == 1 ? candidates.first : nil,
                                     "Require exactly one imported-date fixture; never guess among Photos assets")
            // A remote Photos thumbnail can reject XCTest's AX scrolling even
            // at the screen edge. Permit only half a point of horizontal frame
            // rounding, and clamp the actual touch to the strict viewport.
            // Offscreen images retain the native scroll-and-tap path.
            let frame = image.frame
            let appFrame = app.frame
            let viewport = appFrame.insetBy(dx: 0, dy: 24)
            let visible = frame.intersection(viewport)
            print("PHOTO_PICKER_GEOMETRY image=\(frame) viewport=\(viewport) visible=\(visible)")
            if frame.width >= 44, frame.height >= 44,
               visible.width >= 44, visible.height >= 44,
               viewport.insetBy(dx: -0.5, dy: 0).contains(frame) {
                screenshot("Dated photo fixture ready", app)
                let offset = CGVector(dx: visible.midX - appFrame.minX, dy: visible.midY - appFrame.minY)
                app.coordinate(withNormalizedOffset: CGVector(dx: 0, dy: 0)).withOffset(offset).tap()
            } else { image.tap() }
            // Import and OCR have the existing 30-second app result window.
            // Allow that window plus presentation before the first result;
            // every expected value still has to match, without another read.
            for (index, text) in expected.enumerated() {
                if text == "Brand: Not identified" { assertNoPhotoBrand(app) }
                else { label(text, app, timeout: index == 0 ? 35 : 10) }
            }
        }
        try selectFixture(expected: identified)
        screenshot("Native photo review before replacement", app)
        tap("Choose a photo", app, scroll: app.scrollViews["photo-review-scroll"])
        let cancel = app.buttons["Cancel"].firstMatch
        XCTAssertTrue(cancel.waitForExistence(timeout: 10)); cancel.tap()
        label("No photo selected", app); assertNoPhotoBrand(app)
        label("Model: Not identified", app); label("TV IP hint: Not identified", app)
        screenshot("Replacement cancellation discards the old review", app)
        try selectFixture(expected: identified)
        for name in ["EMPTY", "UNRELATED"] {
            try selectFixture("AQSS_TEST_PHOTO_" + name + "_MODIFIED_AT", expected: [
                "No TV details found. Try a closer photo of the model label or IP address row.",
                "Brand: Not identified", "Model: Not identified", "TV IP hint: Not identified"
            ])
            screenshot("Photo retry guidance " + name.lowercased(), app)
            XCTAssertFalse(app.buttons["photo-use-brand"].exists)
        }
        try selectFixture("AQSS_TEST_PHOTO_BRAND_ONLY_MODIFIED_AT", expected: [
            "Brand: SAMSUNG", "Model: Not identified", "TV IP hint: Not identified", "Nothing is connected."
        ])
        screenshot("Partial photo details remain available", app)
        try selectFixture(expected: identified)
        tap("Clear photo details", app, scroll: app.scrollViews["photo-review-scroll"])
        label("No photo selected", app); assertNoPhotoBrand(app)
        app.buttons["Close"].firstMatch.tap()
        tab("home", app); label("Connection not verified", app)
    }

    func testInputToolsStartIdleAndNeverClaimAConnection() {
        let app = launch()
        tab("sound", app); tap("Voice check", app)
        label("Microphone off", app); label("No words recognized yet", app)
        XCTAssertTrue(app.buttons["voice-start-stop"].exists)
        XCTAssertFalse(app.alerts.firstMatch.exists)
        screenshot("Voice check idle", app)
        app.buttons["Close"].firstMatch.tap()
        tab("devices", app); tap("TV photo setup", app)
        label("No photo selected", app); assertNoPhotoBrand(app)
        XCTAssertFalse(app.alerts.firstMatch.exists)
        screenshot("TV photo setup idle", app)
        app.buttons["Close"].firstMatch.tap()
        tab("home", app); label("Connection not verified", app)
    }

    func testAllFivePagesKeepHelpAndTruthfulEmptyStates() {
        let app = launch()
        XCTAssertTrue(app.buttons["start-beginner-tour"].isHittable)
        tap("Status help", app); label("No output observation", app)
        for (id, title) in [("sound", "SOUND"), ("devices", "DEVICES"), ("insights", "INSIGHTS"), ("settings", "SETTINGS")] {
            tab(id, app); label(title, app)
            XCTAssertTrue(app.buttons["Help & tutorials"].isHittable)
            screenshot("Page \(id)", app)
        }
        XCTAssertFalse(app.buttons["Advanced Settings"].exists)
        tap("More settings", app); tap("Advanced Settings", app)
        tap("About Move this session", app); label("No authorized endpoint or verified transfer path", app)
        dismissSettingHelp(app)
        tab("devices", app); tap("Device help", app)
        label("Six setup checks unknown", app)
        tab("home", app); label("Connection not verified", app)
    }

    func testFirstVisitHasOnePathChoiceGatesTailoredPlanAndReplay() {
        let app = launch(true)
        label("Step 1 of 5", app); assertOnlyGuide(app)
        label("1. Your TV", app)
        XCTAssertFalse(app.buttons["more-features"].exists)
        XCTAssertTrue(app.buttons["guide-next"].isHittable)
        next(app); label("Step 2 of 5", app)
        XCTAssertFalse(app.buttons["guide-next"].exists)
        XCTAssertFalse(app.buttons["choice-samsung"].exists)
        chooseTV("Samsung", app)
        XCTAssertFalse(app.buttons["choice-alexa"].exists)
        XCTAssertTrue(app.buttons["setup-from-samsung"].exists)
        chooseHome("Amazon Alexa", app)
        tap("Setup help", app)
        XCTAssertTrue(app.buttons["Jump to Amazon Alexa pictures"].waitForExistence(timeout: 5))
        app.buttons["Close"].firstMatch.tap()
        app.buttons["guide-back"].tap(); label("Step 2 of 5", app)
        chooseTV("Samsung", app)
        next(app); label("Step 4 of 5", app)
        XCTAssertTrue(app.buttons["Phone pictures"].exists)
        XCTAssertFalse(app.buttons["setup-from-samsung"].exists)
        next(app); label("Step 5 of 5", app)
        next(app); label("Connection not verified", app)
        app.buttons["start-beginner-tour"].tap(); label("Step 1 of 5", app)
        next(app); XCTAssertFalse(app.buttons["guide-next"].exists)
        exit(app); tab("sound", app)
        XCTAssertFalse(app.staticTexts["Dialogue preset"].exists)
        tap("Sound options", app); label("Dialogue preset", app)
        tab("devices", app)
        XCTAssertFalse(app.staticTexts["Six setup checks unknown"].exists)
        tap("Device help", app); label("Six setup checks unknown", app)
        app.terminate(); app.launchArguments = []; app.launch()
        XCTAssertFalse(app.buttons["exit-tutorial"].exists)
        XCTAssertTrue(app.buttons["tab-home"].isHittable)
    }

    func testOptionsAndAdvancedRemainUnavailable() {
        let app = launch(); tab("sound", app)
        XCTAssertFalse(app.staticTexts["Dialogue preset"].exists)
        tap("Sound options", app); tap("About Volume", app)
        label("No qualified device volume control", app)
        dismissSettingHelp(app)
        label("Dialogue preset", app); label("Night preset", app)
        label("Custom Equalizer", app); label("Defaults and Undo", app)
        tab("settings", app); jump("Advanced Settings", app)
        XCTAssertFalse(app.staticTexts.containing(NSPredicate(format: "label CONTAINS %@", "No independent observation is available")).firstMatch.exists)
        tap("About Physical output", app)
        label("No independent observation is available", app)
        dismissSettingHelp(app)
        jump("Privacy and storage", app)
        tap("About Privacy and storage", app)
        label("No audio files saved by this app", app)
        label("Appearance and guide progress stay on this phone", app)
        screenshot("Advanced privacy", app)
        dismissSettingHelp(app)
    }

    func testAdvancedSwitchAttemptResetsAfterTwoSecondsAndHelpReturnsToCaller() {
        let app = launch(); tab("settings", app)
        XCTAssertFalse(app.switches["setting-captions"].exists)
        tap("Advanced Settings", app)
        let captions = app.switches["setting-captions"]
        XCTAssertTrue(captions.isHittable)
        XCTAssertFalse(app.staticTexts.containing(NSPredicate(format: "label CONTAINS %@", "Show a supported caption track")).firstMatch.exists)
        screenshot("Advanced Settings concise white switch rows", app)
        captions.tap()
        let prompt = app.staticTexts["not-connected-captions"]
        XCTAssertTrue(prompt.waitForExistence(timeout: 1))
        screenshot("Cyan disconnected attempt with two-second prompt", app)
        let reset = XCTNSPredicateExpectation(predicate: NSPredicate(format: "exists == false"), object: prompt)
        XCTAssertEqual(XCTWaiter.wait(for: [reset], timeout: 3.5), .completed)
        XCTAssertTrue(["Off", "0"].contains(captions.value as? String ?? ""), "Attempt must end off")
        tap("About Captions", app); label("verified connection", app)
        screenshot("Caption explanation hidden behind question button", app)
        dismissSettingHelp(app)
        XCTAssertTrue(captions.isHittable)
        XCTAssertFalse(prompt.exists)
        app.buttons["page-back"].tap(); label("SETTINGS", app)
        XCTAssertTrue(app.buttons["appearance-picker"].exists)
        XCTAssertFalse(captions.exists)
        app.buttons["page-back"].tap(); label("Connection not verified", app)
    }

    func testAdvancedSwitchResetSurvivesNavigationBackgroundAndLargestText() {
        let app = launch(); tab("settings", app); tap("Advanced Settings", app)
        app.switches["setting-captions"].tap()
        tab("devices", app)
        app.buttons["page-back"].tap()
        let prompt = app.staticTexts["not-connected-captions"]
        let reset = XCTNSPredicateExpectation(predicate: NSPredicate(format: "exists == false"), object: prompt)
        XCTAssertEqual(XCTWaiter.wait(for: [reset], timeout: 3.5), .completed)
        XCTAssertTrue(["Off", "0"].contains(app.switches["setting-captions"].value as? String ?? ""))
        app.switches["setting-captions"].tap()
        XCUIDevice.shared.press(.home); app.activate()
        XCTAssertFalse(prompt.exists)
        XCTAssertTrue(["Off", "0"].contains(app.switches["setting-captions"].value as? String ?? ""))
        app.terminate()
        app.launchArguments = ["-aqssGuideDismissedV1", "YES", "-UIPreferredContentSizeCategoryName", "UICTContentSizeCategoryAccessibilityXXXL"]
        app.launch()
        app.buttons["page-picker"].tap(); tap("Settings", app)
        let dismissed = XCTNSPredicateExpectation(predicate: NSPredicate(format: "exists == false"), object: app.scrollViews["menu-scroll"])
        XCTAssertEqual(XCTWaiter.wait(for: [dismissed], timeout: 5), .completed)
        tap("Advanced Settings", app)
        XCTAssertTrue(app.switches["setting-captions"].isHittable)
        screenshot("Largest text Advanced Settings opens at the first switch", app)
        tap("About Captions", app); label("verified connection", app)
        screenshot("Largest text setting help stays readable", app)
        dismissSettingHelp(app)
        screenshot("Largest text switch controls remain reachable", app)
    }

    func testExitAtWelcomeAndContextualGuideRestoreFullApp() {
        let app = launch(true); exit(app)
        XCTAssertTrue(app.buttons["tab-home"].isHittable)
        tab("settings", app)
        openTutorial("Home and coverage", app)
        label("Step 1 of 4", app); assertOnlyGuide(app)
        next(app); label("Step 2 of 4", app)
        next(app); label("Step 3 of 4", app)
        app.buttons["Back"].tap(); label("Step 2 of 4", app)
        XCUIDevice.shared.press(.home); app.activate(); label("Step 2 of 4", app)
        exit(app); label("HOME", app)
        app.buttons["page-back"].tap(); label("SETTINGS", app)
        tab("settings", app); jump("Privacy and storage", app); tap("About Privacy and storage", app); label("No audio files saved by this app", app); dismissSettingHelp(app)
        openTutorial("Sound options", app)
        next(app); label("Step 2 of 4", app); screenshot("Contextual Sound guide", app)
        exit(app); XCTAssertTrue(app.buttons["Help & tutorials"].isHittable)
    }

    func testExampleAppearanceAndFutureFeatureDoNotClaimAudio() {
        let app = launch(); tab("insights", app)
        label("No measurements yet", app); tap("Explore an example", app)
        label("EXAMPLE · synthetic data", app); label("Relative level (0–100)", app)
        screenshot("Example chart clearly labeled", app)
        tap("Read chart values", app); label("Sample 4: 64 relative units", app)
        tap("Close example", app); label("No measurements yet", app)
        tab("settings", app); chooseAppearance("Daylight", app)
        XCTAssertEqual(app.buttons["appearance-picker"].label, "Appearance: Daylight")
        XCTAssertFalse(app.staticTexts["Explore the direction. These features are not active."].exists)
        screenshot("Daylight Settings", app)
        tab("home", app); screenshot("Daylight Home", app); label("Connection not verified", app)
        tab("settings", app); chooseAppearance("Midnight", app); tap("Advanced Settings", app)
        tap("About Voice requests", app); label("Voice control requires device authority and checked output", app); dismissSettingHelp(app)
        tab("home", app); label("Connection not verified", app)
    }

    func testRokuPicturesResumeAndFinishWithoutClaimingConnection() {
        let app = launch()
        tab("devices", app); tap("Illustrated setup guides", app)
        tap("TCL", app); tap("Roku TV", app)
        showStepHelp(app)
        tap("I’m already in Settings", app); label("Step 3 of 5", app)
        app.buttons["setup-back"].tap()
        XCTAssertFalse(app.staticTexts["setup-progress"].exists)
        XCTAssertTrue(app.buttons["setup-next"].exists)
        tap("I’m already in Settings", app); label("Step 3 of 5", app)
        XCTAssertTrue(app.otherElements["setup-illustration"].exists)
        screenshot("Roku matching Settings Network picture", app)
        let started = Date()
        app.buttons["setup-next"].tap()
        XCTAssertTrue(app.staticTexts["setup-progress"].waitForExistence(timeout: 2))
        XCTAssertEqual(app.staticTexts["setup-progress"].label, "Step 4 of 5")
        print("SIMULATOR_GUIDE_DRIVER_SECONDS=\(Date().timeIntervalSince(started)) includes XCTest tap overhead")
        app.buttons["setup-close"].tap()
        tap("Illustrated setup guides", app); tap("TCL", app); tap("Roku TV", app)
        XCTAssertEqual(app.buttons["setup-next"].label, "Resume guide")
        app.buttons["setup-next"].tap(); label("Step 4 of 5", app)
        screenshot("Roku About selection and resumed step", app)
        app.buttons["setup-next"].tap(); label("Step 5 of 5", app)
        screenshot("Roku IP address information diagram", app)
        XCTAssertEqual(app.buttons["setup-next"].label, "Finish part one")
        app.buttons["setup-next"].tap()
        label("2. Connect to your phone (Roku)", app)
        app.buttons["setup-back"].tap(); label("Step 5 of 5", app)
        app.buttons["setup-next"].tap(); label("2. Connect to your phone (Roku)", app)
        XCTAssertTrue(["Start part two", "Resume guide"].contains(app.buttons["setup-next"].label))
        app.buttons["setup-next"].tap(); label("Step 1 of 5", app)
        screenshot("Roku phone app setup begins", app)
        app.buttons["setup-close"].tap()
        tab("home", app); label("Connection not verified", app)
    }

    func testSimpleDefaultsAndBackRestoreTheActualPreviousPage() {
        let app = launch()
        XCTAssertFalse(app.staticTexts["No output observation"].exists)
        tap("Status help", app); label("No output observation", app)
        tab("devices", app)
        XCTAssertFalse(app.staticTexts["Six setup checks unknown"].exists)
        tap("Illustrated setup guides", app); tap("TCL", app); tap("Roku TV", app)
        XCTAssertTrue(app.buttons["setup-next"].exists)
        XCTAssertFalse(app.buttons["setup-route-roku_network"].exists)
        XCTAssertFalse(app.buttons["setup-route-roku_model"].exists)
        XCTAssertFalse(app.buttons["setup-route-roku_alexa"].exists)
        XCTAssertFalse(app.links.firstMatch.exists)
        screenshot("Roku opens its primary guide directly", app)
        showStepHelp(app)
        tap("Other setup options", app)
        tap("Find my exact model", app)
        XCTAssertFalse(app.buttons["setup-references"].exists)
        screenshot("Simple model guide introduction", app)
        for number in 1...3 {
            app.buttons["setup-next"].tap(); label("Step \(number) of 5", app)
        }
        screenshot("Roku model picture highlights System", app)
        for _ in 1...3 { app.buttons["setup-back"].tap() }
        showStepHelp(app)
        XCTAssertTrue(app.buttons["setup-references"].exists)
        XCTAssertFalse(app.links.firstMatch.exists)
        app.buttons["setup-back"].tap()
        XCTAssertTrue(app.buttons["setup-route-roku_model"].exists)
        app.buttons["setup-back"].tap()
        XCTAssertTrue(app.buttons["setup-next"].exists)
        XCTAssertTrue(app.buttons["setup-intro-options"].exists)
        app.buttons["setup-back"].tap()
        XCTAssertTrue(app.buttons["setup-platform-tcl_roku"].exists)
        app.buttons["setup-back"].tap()
        XCTAssertTrue(app.buttons["setup-group-tcl"].exists)
        app.buttons["setup-close"].tap(); label("DEVICES", app)
        tab("sound", app)
        XCTAssertFalse(app.buttons["Help with options"].exists)
        XCTAssertFalse(app.staticTexts.containing(NSPredicate(format: "label CONTAINS %@", "A qualified device and observed result")).firstMatch.exists)
        let pageLabel = app.staticTexts["SOUND"]
        XCTAssertTrue(pageLabel.waitForExistence(timeout: 5))
        XCTAssertGreaterThanOrEqual(pageLabel.frame.minY, app.scrollViews["home-scroll"].frame.minY + 8)
        tap("Sound options", app)
        tab("settings", app)
        XCTAssertFalse(app.staticTexts["Device and route"].exists)
        app.buttons["page-back"].tap(); label("SOUND", app)
        label("Dialogue preset", app)
        app.buttons["page-back"].tap(); label("DEVICES", app)
        app.buttons["page-back"].tap(); label("Connection not verified", app)
        label("No output observation", app)
        screenshot("Back restores previous page and details", app)
        tab("devices", app); tab("home", app)
        XCTAssertFalse(app.staticTexts["No output observation"].exists)
    }

    func testNewVizioTVShowsAccountThenPhonePicturesInOrder() {
        let app = launch()
        tab("devices", app); tap("Illustrated setup guides", app); tap("Vizio", app)
        tap("VIZIO newer TV", app)
        label("VIZIO newer TV — My Hub account, then phone", app)
        for number in 1...14 {
            app.buttons["setup-next"].tap(); label("Step \(number) of 14", app)
            if [2, 3, 4, 7, 9, 13, 14].contains(number) {
                screenshot("VIZIO newer TV picture \(number)", app)
            }
        }
        XCTAssertEqual(app.buttons["setup-next"].label, "Finish guide")
        app.buttons["setup-close"].tap(); label("DEVICES", app)
    }

    func testRokuPartOneImmediatelyOpensPhonePicturesInFirstVisit() {
        let app = launch(true)
        next(app); chooseTV("TCL", app)
        tap("Show TCL steps", app); tap("Roku TV", app)
        showStepHelp(app)
        tap("I’m already in Settings", app)
        for _ in 0..<2 { app.buttons["setup-next"].tap() }
        label("Step 5 of 5", app)
        XCTAssertEqual(app.buttons["setup-next"].label, "Finish part one")
        app.buttons["setup-next"].tap()
        label("2. Connect to your phone (Roku)", app)
        XCTAssertEqual(app.buttons["setup-next"].label, "Start part two")
        app.buttons["setup-next"].tap(); label("Step 1 of 5", app)
        screenshot("First visit Roku phone guide", app)
        app.buttons["setup-close"].tap()
        label("Step 4 of 5", app)
        label("2. Connect to your phone", app)
        XCTAssertFalse(app.buttons["setup-from-tcl"].exists)
        tap("Phone pictures", app)
        label("2. Connect to your phone (Roku)", app)
        XCTAssertTrue(["Start part two", "Resume guide"].contains(app.buttons["setup-next"].label))
        app.buttons["setup-next"].tap(); label("Step 1 of 5", app)
        XCTAssertFalse(app.staticTexts["iPhone — connect to your home Wi-Fi"].exists)
        screenshot("Roku phone pictures resume from the main phone action", app)
        app.buttons["setup-close"].tap(); label("Step 4 of 5", app)
        app.buttons["guide-back"].tap(); label("Step 3 of 5", app)
        tap("Show TCL steps", app)
        XCTAssertTrue(app.buttons["setup-next"].exists)
        XCTAssertFalse(app.buttons["setup-platform-tcl_roku"].exists)
        app.buttons["setup-back"].tap()
        label("Step 3 of 5", app)
    }

    func testIllustratedGuideFromTCLPlanAndVoiceHelp() {
        let app = launch(true)
        next(app); chooseTV("TCL", app); chooseHome("Google Home", app)
        tap("Show TCL steps", app)
        showStepHelp(app); label("Match the name on your TV’s Home screen", app)
        tap("Help identify my TV", app)
        XCTAssertTrue(app.buttons["setup-next"].exists)
        app.buttons["setup-back"].tap()
        XCTAssertTrue(app.buttons["setup-platform-tcl_google"].exists)
        hideStepHelp(app)
        tap("Google TV / Android TV", app); showStepHelp(app); tap("Other setup options", app); tap("TCL QM851G", app)
        showStepHelp(app); label("85QM851G", app)
        app.buttons["setup-next"].tap(); label("Step 1 of 13", app)
        screenshot("TCL illustrated TV first setup", app)
        app.buttons["setup-next"].tap(); app.buttons["setup-next"].tap()
        label("Step 3 of 13", app)
        XCTAssertTrue(app.otherElements["setup-illustration"].exists)
        showStepHelp(app); tap("My screen looks different", app)
        label("Find the right screen", app)
        app.buttons["setup-back"].tap(); label("Step 3 of 13", app)
        app.buttons["setup-close"].tap(); label("Step 3 of 5", app)
        tap("Setup help", app)
        tap("Jump to Google Home pictures", app, scroll: app.scrollViews["setup-help-scroll"])
        XCTAssertFalse(app.buttons["setup-route-google_samsung"].exists)
        label("first setup with Google Home", app)
        XCTAssertTrue(app.buttons["setup-next"].exists)
        restartPictureGuide(app)
        for _ in 0..<4 { app.buttons["setup-next"].tap() }
        label("Open Devices", app)
        let progress = app.staticTexts["setup-progress"]
        XCTAssertEqual(progress.label, "Step 5 of 13")
        XCTAssertGreaterThanOrEqual(progress.frame.minX, app.frame.minX, "Step counter must stay inside the screen")
        XCTAssertLessThanOrEqual(progress.frame.maxX, app.buttons["setup-close"].frame.minX, "Step counter must not overlap Back to Tutorial")
        app.buttons["setup-next"].tap(); label("Open Add", app)
        app.buttons["setup-next"].tap(); label("Google Nest or partner device", app)
        screenshot("Google Home setup matches the selected TCL system", app)
        app.buttons["setup-close"].tap(); exit(app)
        tab("settings", app); tap("Advanced Settings", app); tap("About Voice requests", app)
        tap("Show voice steps", app)
        label("Step 1 of 9", app)
        for _ in 0..<4 { app.buttons["setup-next"].tap() }
        label("Speak and watch the meter", app)
        XCTAssertFalse(app.alerts.firstMatch.exists)
        screenshot("Voice help illustrated steps", app)
        for _ in 0..<4 { app.buttons["setup-next"].tap() }
        app.buttons["setup-next"].tap()
        label("Microphone off", app); label("No words recognized yet", app)
        app.buttons["Close"].firstMatch.tap()
        tab("home", app); label("Connection not verified", app)
    }

    func testSamsungPinChoiceBackAndResumeStayAtTheApproval() {
        let app = launch()
        tab("devices", app); tap("Illustrated setup guides", app); tap("Samsung", app)
        label("Samsung — connect with SmartThings", app)
        XCTAssertFalse(app.buttons["setup-samsung-pin"].exists)
        if app.buttons["setup-next"].label == "Resume guide" {
            showStepHelp(app); tap("Start from the beginning", app)
        } else { app.buttons["setup-next"].tap() }
        for _ in 0..<14 { app.buttons["setup-next"].tap() }
        label("Approve on the television", app)
        tap("TV shows a PIN", app); label("Step 15 of 18", app)
        label("Read the TV PIN", app); screenshot("Samsung PIN shown on TV", app)
        app.buttons["setup-back"].tap()
        label("Step 15 of 17", app); label("Approve on the television", app)
        tap("TV shows a PIN", app); app.buttons["setup-next"].tap()
        label("Step 16 of 18", app); label("Enter the TV PIN", app)
        screenshot("Samsung PIN entered on phone", app)
        app.buttons["setup-close"].tap()
        tap("Illustrated setup guides", app); tap("Samsung", app)
        label("Continue at picture 16.", app)
        XCTAssertEqual(app.buttons["setup-next"].label, "Resume guide")
        app.buttons["setup-next"].tap(); label("Enter the TV PIN", app)
        app.buttons["setup-next"].tap(); app.buttons["setup-next"].tap()
        label("Check the actual result", app); app.buttons["setup-next"].tap()
        label("Connection not verified", app)
        tap("Illustrated setup guides", app); tap("Samsung", app)
        label("Samsung — connect with SmartThings", app)
        XCTAssertEqual(app.buttons["setup-next"].label, "Start guide")
        app.buttons["setup-close"].tap(); tab("home", app)
        label("Connection not verified", app)
    }

    func testIllustratedApprovalFinishesWithoutClaimingConnection() {
        let app = launch()
        tab("devices", app); tap("Illustrated setup guides", app); tap("Samsung", app)
        label("Samsung — connect with SmartThings", app); app.buttons["setup-next"].tap()
        XCTAssertFalse(app.staticTexts["Use your real device. This picture is an illustration."].exists)
        XCTAssertFalse(app.staticTexts.containing(NSPredicate(format: "label CONTAINS %@", "Illustrations may differ from your screen")).firstMatch.exists)
        for _ in 0..<14 { app.buttons["setup-next"].tap() }
        label("Approve on the television", app)
        screenshot("Samsung illustrated TV approval", app)
        app.buttons["setup-next"].tap(); app.buttons["setup-next"].tap()
        label("Check the actual result", app)
        app.buttons["setup-next"].tap()
        label("Connection not verified", app)
        tap("Illustrated setup guides", app); tap("Roku-branded TV", app)
        showStepHelp(app); tap("Other setup options", app); tap("Roku TV → Alexa", app)
        app.buttons["setup-next"].tap()
        for _ in 0..<6 { app.buttons["setup-next"].tap() }
        label("Review Roku approval", app)
        screenshot("Alexa illustrated account approval", app)
        app.buttons["setup-close"].tap()
        tab("home", app); label("Connection not verified", app)
    }

    func testFinishedPairingPicturesAdvanceLocallyAndCloseKeepsThePhoneStep() {
        let app = launch(true)
        next(app); chooseTV("Samsung", app)
        tap("Show Samsung steps", app); label("Samsung — connect with SmartThings", app)
        app.buttons["setup-close"].tap(); label("Step 3 of 5", app)
        tap("Show Samsung steps", app); restartPictureGuide(app)
        for _ in 0..<16 { app.buttons["setup-next"].tap() }
        label("Check the actual result", app)
        app.buttons["setup-next"].tap(); label("Step 4 of 5", app)
        XCTAssertTrue(app.buttons["Phone pictures"].exists)
        XCTAssertFalse(app.buttons["setup-from-samsung"].exists)
        tap("Setup help", app)
        tap("Jump to phone Wi-Fi pictures", app, scroll: app.scrollViews["setup-help-scroll"])
        label("iPhone — connect to your home Wi-Fi", app)
        app.buttons["setup-next"].tap(); label("Step 1 of 6", app)
        for _ in 0..<5 { app.buttons["setup-next"].tap() }
        label("blue checkmark", app)
        app.buttons["setup-next"].tap(); label("Step 4 of 5", app)
        app.buttons["guide-back"].tap(); label("Step 3 of 5", app)
        tap("Show Samsung steps", app); app.buttons["setup-close"].tap()
        label("Step 3 of 5", app); next(app); label("Step 4 of 5", app)
        tap("Phone pictures", app); label("2. Check Samsung on your phone", app)
        restartPictureGuide(app)
        for _ in 0..<4 { app.buttons["setup-next"].tap() }
        label("Check the phone controls", app)
        app.buttons["setup-next"].tap(); label("Step 5 of 5", app)
        exit(app); label("Connection not verified", app)
    }

    private func restartPictureGuide(_ app: XCUIApplication) {
        if app.buttons["setup-next"].label == "Resume guide" {
            showStepHelp(app); tap("Start from the beginning", app)
        } else { app.buttons["setup-next"].tap() }
    }
    private func pictureDescription(_ app: XCUIApplication) -> String {
        let picture = app.descendants(matching: .any).matching(identifier: "setup-illustration").firstMatch
        XCTAssertTrue(picture.waitForExistence(timeout: 5))
        return picture.label
    }

    func testTVCodePicturesSeparateTheTVFromPhoneAndKeepOptionalLinksNeutral() {
        let app = launch()
        tab("devices", app); tap("Illustrated setup guides", app); tap("Sony", app)
        restartPictureGuide(app)
        for _ in 0..<3 { app.buttons["setup-next"].tap() }
        label("Step 4 of 9", app)
        XCTAssertTrue(pictureDescription(app).contains("bottom right"))
        screenshot("Google TV nearby control at bottom right", app)
        for _ in 0..<2 { app.buttons["setup-next"].tap() }
        label("Step 6 of 9", app); label("Read your TV code", app)
        XCTAssertTrue(pictureDescription(app).contains("TV screen"))
        screenshot("Google TV code is read on the television", app)
        app.buttons["setup-next"].tap(); label("Step 7 of 9", app)
        XCTAssertTrue(pictureDescription(app).contains("Phone screen"))
        screenshot("Google TV code is entered on the phone", app)
        app.buttons["setup-back"].tap(); label("Step 6 of 9", app)
        app.buttons["setup-close"].tap()
        tap("Illustrated setup guides", app); tap("Sony", app)
        label("Continue at picture 6.", app); app.buttons["setup-next"].tap()
        label("Read your TV code", app); app.buttons["setup-close"].tap()

        tap("Illustrated setup guides", app); tap("LG", app); restartPictureGuide(app)
        for _ in 0..<10 { app.buttons["setup-next"].tap() }
        label("Step 11 of 13", app); label("Decide whether to link accounts", app)
        let choice = pictureDescription(app)
        XCTAssertTrue(choice.contains("neither is selected"))
        XCTAssertTrue(choice.contains("Link or Skip"))
        screenshot("LG account linking and Skip are equal choices", app)
        app.buttons["setup-back"].tap(); label("Step 10 of 13", app)
        app.buttons["setup-close"].tap()

        tap("Illustrated setup guides", app); tap("Vizio", app); tap("Other setup options", app)
        tap("Vizio — link the TV account", app); restartPictureGuide(app)
        for number in 2...11 {
            app.buttons["setup-next"].tap(); label("Step \(number) of 11", app)
            if [5, 6, 7, 8, 9, 10].contains(number) { screenshot("VIZIO legacy account picture \(number)", app) }
            if number == 9 { XCTAssertTrue(pictureDescription(app).contains("TV screen")) }
            if number == 10 { XCTAssertTrue(pictureDescription(app).contains("Phone screen")) }
        }
        app.buttons["setup-close"].tap(); tab("home", app); label("Connection not verified", app)
    }

    func testBrandPlatformsKeepRokuMenusSeparateAndOfferManualGoogleTVSetup() {
        let app = launch(); tab("devices", app)
        for (brand, platform, heading, highlight) in [
            ("TCL", "Roku TV", "Find my IP address", "Network"),
            ("Sharp", "", "Find my exact model", "System"),
            ("Roku-branded TV", "", "Find my IP address", "Network"),
            ("Philips", "Roku TV", "Find my IP address", "Network")
        ] {
            tap("Illustrated setup guides", app); tap(brand, app)
            if !platform.isEmpty { tap(platform, app) }
            label(heading, app); restartPictureGuide(app)
            app.buttons["setup-next"].tap(); app.buttons["setup-next"].tap()
            label("Step 3 of 5", app)
            XCTAssertTrue(pictureDescription(app).contains(highlight))
            screenshot("\(brand) \(platform) uses \(highlight)", app)
            app.buttons["setup-close"].tap()
        }
        tap("Illustrated setup guides", app); tap("Hisense", app); tap("VIDAA", app)
        label("43A6GV / VIDAA U5", app); screenshot("Hisense asks for the matching VIDAA menu", app)
        app.buttons["setup-close"].tap()

        tap("Illustrated setup guides", app); tap("Insignia", app); tap("Fire TV", app)
        restartPictureGuide(app)
        for _ in 0..<4 { app.buttons["setup-next"].tap() }
        XCTAssertTrue(pictureDescription(app).contains("neither is selected"))
        screenshot("Fire TV phone or remote Wi-Fi choice", app)
        app.buttons["setup-next"].tap(); label("Step 6 of 8", app)
        XCTAssertTrue(pictureDescription(app).contains("TV screen"))
        tap("Account sign-in finished", app); label("Step 8 of 8", app)
        app.buttons["setup-back"].tap(); label("Step 6 of 8", app)
        screenshot("Fire TV account completion can skip manual code entry", app)
        app.buttons["setup-close"].tap()

        tap("Illustrated setup guides", app); tap("TCL", app); tap("Google TV / Android TV", app)
        showStepHelp(app); tap("Other setup options", app)
        tap("Google TV — first setup with Google Home", app)
        restartPictureGuide(app)
        for _ in 0..<8 { app.buttons["setup-next"].tap() }
        label("Step 9 of 13", app); XCTAssertTrue(pictureDescription(app).contains("Phone screen"))
        screenshot("Google Home opens the scanner on the phone", app)
        app.buttons["setup-next"].tap(); label("Step 10 of 13", app)
        XCTAssertTrue(pictureDescription(app).contains("TV screen"))
        screenshot("Google Home scanner points to the television QR code", app)
        showStepHelp(app); tap("Use the TV remote instead", app)
        label("Google TV — finish setup with the TV remote", app)
        restartPictureGuide(app); app.buttons["setup-next"].tap()
        label("Step 2 of 7", app); XCTAssertTrue(pictureDescription(app).contains("TV remote"))
        screenshot("Google TV manual setup uses the physical Down button", app)
        app.buttons["setup-back"].tap(); label("Step 1 of 7", app)
        app.buttons["setup-close"].tap(); tab("home", app); label("Connection not verified", app)
    }

    func testLGVizioAndGoogleTVContinueIntoTheirOwnPhoneAppPictures() {
        continueAfterFailure = false
        for (brand, pairingChoice, count, phoneTitle) in [
            ("LG", "", 13, "2. Check LG ThinQ on your phone"),
            ("Vizio", "Vizio — pair the phone", 9, "2. Check VIZIO Mobile on your phone"),
            ("Sony", "", 9, "2. Check Google TV on your phone")
        ] {
            let app = launch(true)
            next(app)
            chooseTV(brand, app)
            tap("Show \(brand) steps", app)
            if !pairingChoice.isEmpty { tap(pairingChoice, app) }
            restartPictureGuide(app)
            for _ in 1..<count { app.buttons["setup-next"].tap() }
            app.buttons["setup-next"].tap(); label("Step 4 of 5", app)
            tap("Phone pictures", app); label(phoneTitle, app)
            XCTAssertFalse(app.buttons["setup-pairing-help"].exists)
            showStepHelp(app)
            XCTAssertTrue(app.buttons["setup-pairing-help"].exists)
            screenshot("\(brand) continues to its matching phone app", app)
            restartPictureGuide(app)
            for _ in 0..<4 { app.buttons["setup-next"].tap() }
            XCTAssertEqual(app.buttons["setup-next"].label, "Finish part two")
            app.buttons["setup-next"].tap(); label("Step 5 of 5", app)
            exit(app); label("Connection not verified", app); app.terminate()
        }
    }

    func testPhilipsAlreadyConnectedSkipsPairingAndBackRestoresTheChoice() {
        let app = launch()
        tab("devices", app); tap("Illustrated setup guides", app)
        tap("Philips", app); tap("Google TV / Android TV", app)
        showStepHelp(app); tap("Other setup options", app)
        tap("Philips Google TV — pair the voice remote", app)
        if app.buttons["setup-next"].label == "Resume guide" {
            showStepHelp(app); tap("Start from the beginning", app)
        } else { app.buttons["setup-next"].tap() }
        for _ in 0..<4 { app.buttons["setup-next"].tap() }
        label("Step 5 of 10", app)
        tap("Remote already connected", app)
        label("Step 10 of 10", app); label("Check the real status", app)
        screenshot("Philips already connected skips pairing", app)
        app.buttons["setup-back"].tap(); label("Step 5 of 10", app)
        app.buttons["setup-next"].tap(); label("Step 6 of 10", app)
        XCTAssertTrue(pictureDescription(app).contains("TV remote"))
        screenshot("Philips remote button combination", app)
        app.buttons["setup-next"].tap(); label("Step 8 of 10", app)
        app.buttons["setup-back"].tap(); label("Step 6 of 10", app)
        tap("Light is not blinking", app); label("Step 7 of 10", app)
        screenshot("Philips reset only when pairing light fails", app)
    }

    func testNewBrandPicturesAreReachable() {
        let app = launch()
        tab("devices", app); tap("Illustrated setup guides", app); tap("Philips", app); tap("Google TV / Android TV", app); showStepHelp(app); tap("Other setup options", app)
        tap("Philips Google TV — pair the voice remote", app)
        app.buttons["setup-next"].tap()
        label("Start with your TV home screen", app)
        app.buttons["setup-next"].tap()
        label("Open the profile menu", app)
        screenshot("Philips illustrated profile choice", app)
        app.buttons["setup-close"].tap()
        tab("home", app); label("Connection not verified", app)
    }

    func testIllustratedGuideKeepsScrollContainerAndResetsPosition() {
        let app = XCUIApplication()
        app.launchArguments = ["-aqssGuideDismissedV1", "YES", "--aqss-trace-navigation"]
        app.launch(); tab("devices", app); tap("Illustrated setup guides", app)
        let scroll = app.scrollViews["setup-scroll"]
        let instance = scroll.value as? String
        XCTAssertNotNil(UUID(uuidString: instance ?? ""))
        tap("TCL", app); tap("Roku TV", app)
        showStepHelp(app)
        tap("I’m already in Settings", app); label("Step 3 of 5", app)
        XCTAssertEqual(scroll.value as? String, instance)
        scroll.swipeUp()
        app.buttons["setup-next"].tap(); label("Step 4 of 5", app)
        XCTAssertEqual(scroll.value as? String, instance)
        // A new step must start at its heading, even after scrolling the old one.
        let heading = app.staticTexts["Open About"]
        XCTAssertTrue(heading.waitForExistence(timeout: 5))
        XCTAssertTrue(heading.isHittable)
        XCTAssertLessThan(heading.frame.minY, scroll.frame.minY + 100)
        app.buttons["setup-back"].tap(); label("Step 3 of 5", app)
        XCTAssertEqual(scroll.value as? String, instance)
        showStepHelp(app); tap("My screen looks different", app); label("Find the right screen", app)
        app.buttons["setup-back"].tap(); label("Step 3 of 5", app)
        XCTAssertEqual(scroll.value as? String, instance)
        screenshot("Stable scrolling container after Next Back and help", app)
    }

    func testSelectingATVAdvancesAndBackKeepsTheScrollAndHomePreference() {
        let app = XCUIApplication()
        app.launchArguments = ["-aqssGuideDismissedV1", "NO", "--aqss-trace-navigation"]
        app.launch(); next(app); label("Step 2 of 5", app)
        let scroll = app.scrollViews["guide-scroll"]
        let instance = scroll.value as? String
        XCTAssertFalse(instance?.isEmpty ?? true)
        XCTAssertFalse(app.buttons["guide-next"].exists)
        chooseTV("Samsung", app)
        XCTAssertEqual(scroll.value as? String, instance)
        XCTAssertTrue(app.buttons["setup-from-samsung"].exists)
        chooseHome("Google Home", app)
        app.buttons["guide-back"].tap(); label("Step 2 of 5", app)
        XCTAssertEqual(scroll.value as? String, instance)
        chooseTV("Samsung", app)
        tap("Setup help", app)
        XCTAssertTrue(app.buttons["Jump to Google Home pictures"].waitForExistence(timeout: 5))
        XCTAssertEqual(scroll.value as? String, instance)
    }

    func testLargestTextKeepsExitAndNextReachable() {
        let app = XCUIApplication()
        app.launchArguments = ["-aqssGuideDismissedV1", "NO", "-UIPreferredContentSizeCategoryName", "UICTContentSizeCategoryAccessibilityXXXL"]
        app.launch(); label("Step 1 of 5", app); assertOnlyGuide(app)
        XCTAssertTrue(app.buttons["guide-next"].isHittable)
        XCTAssertGreaterThanOrEqual(app.buttons["exit-tutorial"].frame.height, 44)
        screenshot("Largest text single-step guide", app)
        next(app); chooseTV("Samsung", app)
        XCTAssertTrue(app.buttons["setup-from-samsung"].isHittable)
        XCTAssertFalse(app.buttons["guide-next"].exists)
        exit(app)
        app.buttons["page-picker"].tap(); tap("Devices", app)
        // A page sheet can still be dismissing after the navigation tap.
        // Assert reachability after the transition, not during its animation.
        let helpReady = XCTNSPredicateExpectation(predicate: NSPredicate(format: "hittable == true"), object: app.buttons["Help & tutorials"])
        XCTAssertEqual(XCTWaiter.wait(for: [helpReady], timeout: 5), .completed)
        XCTAssertTrue(app.buttons["Help & tutorials"].isHittable)
        openTutorial("Readiness checklist", app)
        label("Step 1 of 6", app); assertOnlyGuide(app)
        screenshot("Largest text contextual guide", app)
        exit(app); XCTAssertTrue(app.buttons["page-picker"].isHittable)
        app.buttons["page-back"].tap(); label("DEVICES", app)
        tap("Illustrated setup guides", app)
        let choices = app.scrollViews["setup-scroll"]
        XCTAssertTrue(choices.waitForExistence(timeout: 5))
        XCTAssertGreaterThan(choices.frame.height, app.frame.height / 2,
                             "The largest-text header must leave room for the setup choices")
        tap("Samsung", app)
        label("Samsung — connect with SmartThings", app); app.buttons["setup-next"].tap()
        label("Step 1 of 17", app)
        XCTAssertTrue(app.buttons["setup-close"].isHittable)
        XCTAssertTrue(app.buttons["setup-next"].isHittable)
        XCTAssertGreaterThanOrEqual(app.buttons["setup-next"].frame.height, 44)
        screenshot("Largest text illustrated setup", app)
        app.buttons["setup-close"].tap()
    }
}
