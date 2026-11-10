import XCTest
@testable import AQSSNativeFeedback

final class OwnedVoiceSkipGateTests: XCTestCase {
    private func sample(intro: Bool = true, recap: Bool = true, generation: Int = 7,
                        content: String = "episode-1") -> OwnedSkipSnapshot {
        OwnedSkipSnapshot(playerID: "owned", playbackSessionID: "session-1", contentID: content,
                          generation: generation, introVisible: intro, introEnabled: intro,
                          recapVisible: recap, recapEnabled: recap)
    }

    func testExactFinalPhrasesAndNegativeGrammar() async {
        await MainActor.run {
            XCTAssertEqual(OwnedVoiceSkipGate.parse("Audio Bodyguard, skip intro", final: true), .intro)
            XCTAssertEqual(OwnedVoiceSkipGate.parse(" AUDIO BODYGUARD SKIP RECAP. ", final: true), .recap)
            XCTAssertNil(OwnedVoiceSkipGate.parse("Audio Bodyguard skip recap", final: false))
            for text in ["skip intro", "Audio Bodyguard don't skip intro", "Audio Bodyguard skip next",
                         "Audio Bodyguard skip intro please",\n                         "Audio Bodyguard\\nskip intro", "Audio Bodyguard\\tskip recap",\n                         "\\nAudio Bodyguard skip intro\\n", "Audio Bodyguard skip intro\\r", "Audio Bodyguard skip intro and recap",
                         "Audio Bodyguard skip intro \u{0000}",
                         "\u{00A0}Audio Bodyguard skip intro", "Audio Bodyguard skip recap\u{00A0}"] {
                XCTAssertNil(OwnedVoiceSkipGate.parse(text, final: true))
            }
        }
    }

    func testEachActionCallsOnlyMatchingOwnedButtonOnce() async {
        await MainActor.run {
            for (phrase, expected) in [("Audio Bodyguard skip intro", OwnedSkipAction.intro),
                                       ("Audio Bodyguard skip recap", .recap)] {
                let gate = OwnedVoiceSkipGate(), state = sample()
                var calls: [OwnedSkipAction] = []
                XCTAssertTrue(gate.start(runID: "listen-1", player: state))
                let proposal = gate.propose(phrase, final: true, runID: "listen-1", observed: state)
                XCTAssertEqual(proposal?.action, expected)
                let action: (OwnedSkipAction) -> Bool = { calls.append($0); return true }
                XCTAssertEqual(gate.request(proposal, runID: "listen-1", observed: state,
                                            permitted: true, foreground: true, pressOwnedButton: action), .requested)
                XCTAssertEqual(gate.request(proposal, runID: "listen-1", observed: state,
                                            permitted: true, foreground: true, pressOwnedButton: action), .unavailable)
                XCTAssertEqual(calls, [expected])
            }
        }
    }

    func testStaleManualChangeBackgroundStopAndDenialNeverPress() async {
        await MainActor.run {
            let gate = OwnedVoiceSkipGate(), state = sample()
            var calls = 0
            XCTAssertTrue(gate.start(runID: "listen-1", player: state))
            XCTAssertNil(gate.propose("Audio Bodyguard skip intro", final: false,
                                      runID: "listen-1", observed: state))
            let proposal = gate.propose("Audio Bodyguard skip intro", final: true,
                                        runID: "listen-1", observed: state)
            for changed in [sample(intro: false), sample(generation: 8), sample(content: "episode-2")] {
                XCTAssertEqual(gate.request(proposal, runID: "listen-1", observed: changed,
                                            permitted: true, foreground: true, pressOwnedButton: { _ in calls += 1; return true }), .unavailable)
            }
            XCTAssertEqual(gate.request(proposal, runID: "listen-1", observed: state,
                                        permitted: false, foreground: true, pressOwnedButton: { _ in calls += 1; return true }), .unavailable)
            XCTAssertEqual(gate.request(proposal, runID: "listen-1", observed: state,
                                        permitted: true, foreground: false, pressOwnedButton: { _ in calls += 1; return true }), .unavailable)
            gate.stop()
            XCTAssertEqual(gate.request(proposal, runID: "listen-1", observed: state,
                                        permitted: true, foreground: true, pressOwnedButton: { _ in calls += 1; return true }), .unavailable)
            XCTAssertFalse(gate.start(runID: "listen-1", player: state))
            XCTAssertTrue(gate.start(runID: "listen-2", player: state))
            XCTAssertNil(gate.propose("Audio Bodyguard skip recap", final: true, runID: "listen-1", observed: state))
            XCTAssertEqual(calls, 0)
        }
    }

    func testAbsentControlAndFailureNeverBecomeVerified() async {
        await MainActor.run {
            let gate = OwnedVoiceSkipGate(), state = sample(intro: false)
            XCTAssertTrue(gate.start(runID: "listen-1", player: state))
            XCTAssertNil(gate.propose("Audio Bodyguard skip intro", final: true, runID: "listen-1", observed: state))
            let proposal = gate.propose("Audio Bodyguard skip recap", final: true, runID: "listen-1", observed: state)
            var calls = 0
            let action: (OwnedSkipAction) -> Bool = { _ in calls += 1; return false }
            XCTAssertEqual(gate.request(proposal, runID: "listen-1", observed: state,
                                        permitted: true, foreground: true, pressOwnedButton: action), .callFailed)
            XCTAssertEqual(gate.request(proposal, runID: "listen-1", observed: state,
                                        permitted: true, foreground: true, pressOwnedButton: action), .unavailable)
            XCTAssertEqual(calls, 1)
        }
    }

    func testLostPermissionOrForegroundInvalidatesPendingFinalResult() async {
        await MainActor.run {
            for (permitted, foreground) in [(false, true), (true, false)] {
                let gate = OwnedVoiceSkipGate(), state = sample()
                var calls = 0
                XCTAssertTrue(gate.start(runID: "listen-1", player: state))
                let proposal = gate.propose("Audio Bodyguard skip intro", final: true,
                                            runID: "listen-1", observed: state)
                let action: (OwnedSkipAction) -> Bool = { _ in calls += 1; return true }
                XCTAssertEqual(gate.request(proposal, runID: "listen-1", observed: state,
                                            permitted: permitted, foreground: foreground,
                                            pressOwnedButton: action), .unavailable)
                XCTAssertEqual(gate.request(proposal, runID: "listen-1", observed: state,
                                            permitted: true, foreground: true,
                                            pressOwnedButton: action), .unavailable)
                XCTAssertNil(gate.propose("Audio Bodyguard skip recap", final: true,
                                          runID: "listen-1", observed: state))
                XCTAssertFalse(gate.start(runID: "listen-1", player: state))
                XCTAssertTrue(gate.start(runID: "listen-2", player: state))
                XCTAssertEqual(calls, 0)
            }
        }
    }
    func testNativeFinalResultEntryPointMatchesOnceAndRejectsConsentLoss() async {
        await MainActor.run {
            for (text, expected) in [("Audio Bodyguard skip intro", OwnedSkipAction.intro),
                                     ("Audio Bodyguard skip recap", .recap)] {
                let gate = OwnedVoiceSkipGate(), state = sample()
                var calls: [OwnedSkipAction] = []
                let press: (OwnedSkipAction) -> Bool = { calls.append($0); return true }
                XCTAssertTrue(gate.start(runID: "voice-1", player: state))
                XCTAssertEqual(gate.requestFinal(text, runID: "voice-1", observed: state,
                                                 permitted: true, foreground: true,
                                                 pressOwnedButton: press), .requested)
                XCTAssertEqual(gate.requestFinal(text, runID: "voice-1", observed: state,
                                                 permitted: true, foreground: true,
                                                 pressOwnedButton: press), .unavailable)
                XCTAssertEqual(calls, [expected])
            }
            for (permission, foreground) in [(false, true), (true, false)] {
                let gate = OwnedVoiceSkipGate(), state = sample()
                var calls = 0
                let press: (OwnedSkipAction) -> Bool = { _ in calls += 1; return true }
                XCTAssertTrue(gate.start(runID: "voice-1", player: state))
                XCTAssertEqual(gate.requestFinal("Audio Bodyguard skip intro", runID: "voice-1",
                                                 observed: state, permitted: permission,
                                                 foreground: foreground, pressOwnedButton: press), .unavailable)
                XCTAssertEqual(gate.requestFinal("Audio Bodyguard skip intro", runID: "voice-1",
                                                 observed: state, permitted: true,
                                                 foreground: true, pressOwnedButton: press), .unavailable)
                XCTAssertEqual(calls, 0)
            }
        }
    }

}
