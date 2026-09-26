import AVFAudio
import SwiftUI

@main
struct AQSSReadOnlyApp: App {
    var body: some Scene {
        WindowGroup { ReadOnlyHomeView() }
    }
}

private struct ReadOnlyHomeView: View {
    @Environment(\.scenePhase) private var scenePhase
    @StateObject private var audioHints = ForegroundAudioHints()

    // No observation is supplied until a native source and output path qualify.
    private let coverage = AQSSSessionEvidenceView.coverage(
        nil, runtimeId: "prototype", clockDomainId: "prototype", nowMonotonic: 0
    )

    private var coverageTitle: String {
        guard coverage.state == .unknownPhysicalState, coverage.reason == "NO_OBSERVATION" else {
            return "Unknown physical state — app status unavailable"
        }
        return "Unknown physical state"
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 18) {
                Text("SIMULATION — no audio path connected")
                    .font(.headline)
                section("Coverage", detail: coverageTitle, explanation:
                    "No output observation. This screen does not monitor or protect audio.")
                section("Supported controls", detail: "Unknown", explanation:
                    "No player, route, permission, or physical observer is connected.")
                section("Captions", detail: "Not observed", explanation:
                    "No authored caption track has been discovered or selected.")
                section("Session history", detail: "No observed events", explanation:
                    "A missing history cannot establish continuous coverage.")
                section("Foreground OS hint", detail: audioHints.lastHint, explanation:
                    "Only this app's audio-session notifications while this screen is active. A notification cannot verify playback, another app's route, or physical output.")
                section("Next step", detail: "Qualify a supported path", explanation:
                    "A supported output and independent observation path must be qualified before this app can report an active listening session.")
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(24)
        }
        .onAppear {
            if scenePhase == .active { audioHints.start() }
        }
        .onDisappear { audioHints.stop() }
        .onChange(of: scenePhase) { phase in
            if phase == .active { audioHints.start() } else { audioHints.stop() }
        }
    }

    private func section(_ title: String, detail: String, explanation: String) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(title).font(.title2.bold())
            Text(detail).font(.headline)
            Text(explanation).font(.body)
        }
        .accessibilityElement(children: .combine)
    }
}

private final class ForegroundAudioHints: ObservableObject {
    @Published private(set) var lastHint = "No app-session notification observed in this foreground visit."
    private var tokens: [NSObjectProtocol] = []
    private var epoch = 0

    func start() {
        guard tokens.isEmpty else { return }
        epoch &+= 1
        let currentEpoch = epoch
        lastHint = "No app-session notification observed in this foreground visit."
        let center = NotificationCenter.default
        let session = AVAudioSession.sharedInstance()
        for (name, label) in [
            (AVAudioSession.routeChangeNotification, "iOS audio-session route-change notification received."),
            (AVAudioSession.interruptionNotification, "iOS audio-session interruption notification received."),
            (AVAudioSession.mediaServicesWereResetNotification, "iOS media-services reset notification received.")
        ] {
            tokens.append(center.addObserver(forName: name, object: session, queue: .main) { [weak self] _ in
                guard let self = self, self.epoch == currentEpoch, !self.tokens.isEmpty else { return }
                self.lastHint = label
            })
        }
    }

    func stop() {
        guard !tokens.isEmpty else { return }
        epoch &+= 1
        tokens.forEach { NotificationCenter.default.removeObserver($0) }
        tokens.removeAll()
        lastHint = "Foreground observation paused. Changes while inactive or hidden are unknown."
    }

    deinit { tokens.forEach { NotificationCenter.default.removeObserver($0) } }
}
