import XCTest
@testable import AQSSNativeFeedback

final class OwnedVoiceSkipRunOwnershipTests: XCTestCase {
    private func player(generation: Int = 1) -> OwnedSkipSnapshot {
        OwnedSkipSnapshot(playerID: "owned", playbackSessionID: "episode-session", contentID: "episode",
                          generation: generation, introVisible: true, introEnabled: true,
                          recapVisible: true, recapEnabled: true)
    }

    func testOldFinalDenialCannotStopNewListeningRun() async {
        await MainActor.run {
            for (permitted, foreground) in [(false, true), (true, false)] {
                for (phrase, expected) in [("Audio Bodyguard, skip intro", OwnedSkipAction.intro),
                                          ("Audio Bodyguard, skip recap", .recap)] {
                    let gate = OwnedVoiceSkipGate(), state = player()
                    var calls: [OwnedSkipAction] = []
                    let press: (OwnedSkipAction) -> Bool = { calls.append($0); return true }
                    XCTAssertTrue(gate.start(runID: "old", player: state))
                    gate.stop()
                    XCTAssertTrue(gate.start(runID: "new", player: state))
                    XCTAssertEqual(gate.requestFinal(phrase, runID: "old", observed: state,
                        permitted: permitted, foreground: foreground, pressOwnedButton: press), .unavailable)
                    XCTAssertEqual(calls, [])
                    XCTAssertEqual(gate.requestFinal(phrase, runID: "new", observed: state,
                        permitted: true, foreground: true, pressOwnedButton: press), .requested)
                    XCTAssertEqual(calls, [expected])
                    XCTAssertEqual(gate.requestFinal(phrase, runID: "new", observed: state,
                        permitted: true, foreground: true, pressOwnedButton: press), .unavailable)
                    XCTAssertEqual(calls, [expected])
                }
            }
        }
    }

    func testCurrentDenialInvalidatesRunBeforeOtherRejections() async {
        await MainActor.run {
            for (permitted, foreground) in [(false, true), (true, false)] {
                for missing in [true, false] {
                    let gate = OwnedVoiceSkipGate(), state = player()
                    var calls: [OwnedSkipAction] = []
                    let press: (OwnedSkipAction) -> Bool = { calls.append($0); return true }
                    XCTAssertTrue(gate.start(runID: "current", player: state))
                    let proposal = gate.propose("Audio Bodyguard, skip intro", final: true,
                                                runID: "current", observed: state)
                    XCTAssertNotNil(proposal)
                    XCTAssertEqual(gate.request(missing ? nil : proposal, runID: "current",
                        observed: missing ? state : player(generation: 2), permitted: permitted,
                        foreground: foreground, pressOwnedButton: press), .unavailable)
                    XCTAssertEqual(calls, [])
                    // Restored permission and state cannot revive a revoked proposal.
                    XCTAssertEqual(gate.request(proposal, runID: "current", observed: state,
                        permitted: true, foreground: true, pressOwnedButton: press), .unavailable)
                    XCTAssertEqual(calls, [])
                    XCTAssertFalse(gate.start(runID: "current", player: state))
                    XCTAssertTrue(gate.start(runID: "fresh", player: state))
                    XCTAssertEqual(gate.requestFinal("Audio Bodyguard, skip intro", runID: "fresh",
                        observed: state, permitted: true, foreground: true, pressOwnedButton: press), .requested)
                    XCTAssertEqual(calls, [.intro])
                }
            }
        }
    }

    func testOldSplitRequestCannotStopNewPendingProposal() async {
        await MainActor.run {
            for (permitted, foreground) in [(false, true), (true, false)] {
                let gate = OwnedVoiceSkipGate(), state = player()
                var calls: [OwnedSkipAction] = []
                let press: (OwnedSkipAction) -> Bool = { calls.append($0); return true }
                XCTAssertTrue(gate.start(runID: "old", player: state))
                let old = gate.propose("Audio Bodyguard, skip intro", final: true, runID: "old", observed: state)
                gate.stop()
                XCTAssertTrue(gate.start(runID: "new", player: state))
                let new = gate.propose("Audio Bodyguard, skip recap", final: true, runID: "new", observed: state)
                XCTAssertNotNil(old); XCTAssertNotNil(new)
                XCTAssertEqual(gate.request(old, runID: "old", observed: state, permitted: permitted,
                    foreground: foreground, pressOwnedButton: press), .unavailable)
                XCTAssertEqual(calls, [])
                XCTAssertEqual(gate.request(new, runID: "new", observed: state, permitted: true,
                    foreground: true, pressOwnedButton: press), .requested)
                XCTAssertEqual(calls, [.recap])
            }
        }
    }
}
