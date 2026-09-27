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
    @State private var optionsExpanded = false
    @State private var advancedExpanded = false

    // No observation is supplied until a native source and output path qualify.
    private let coverage = AQSSSessionEvidenceView.coverage(
        nil, runtimeId: "prototype", clockDomainId: "prototype", nowMonotonic: 0
    )
    private let capability = AQSSSessionEvidenceView.capability(
        AQSSCapabilityFacts(
            hardware: nil, qualification: nil, permission: nil,
            route: nil, runtime: nil, evidence: nil,
            observedMonotonic: 0, expiresMonotonic: 0, clockDomainId: "prototype"
        ), clockDomainId: "prototype", nowMonotonic: 0
    )

    private var coverageTitle: String {
        guard coverage.state == .unknownPhysicalState, coverage.reason == "NO_OBSERVATION" else {
            return "Unknown physical state — app status unavailable"
        }
        return "Unknown physical state"
    }

    private var capabilityTitle: String {
        guard capability.label == "UNKNOWN", !capability.canActuate,
              capability.reasons.count == 6 else { return "Unavailable — checklist unconfirmed" }
        return "Six setup checks unknown"
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 18) {
                Text("SIMULATION — no audio path connected")
                    .font(.headline)
                optionsMenu
                section("Coverage", detail: coverageTitle, explanation:
                    "No output observation. This screen does not monitor or protect audio.")
                section("Supported controls", detail: capabilityTitle, explanation:
                    "Output hardware, qualification, permission, route, runtime, and independent observation are unconfirmed. This simulation cannot offer a control.")
                section("Captions", detail: "Not observed", explanation:
                    "No authored caption track has been discovered or selected.")
                section("Session history", detail: "No observed events", explanation:
                    "A missing history cannot establish continuous coverage.")
                section("Foreground OS hint", detail: audioHints.lastHint, explanation:
                    "Only this app's audio-session notifications while this screen is active. A notification cannot verify playback, another app's route, or physical output.")
                section("Move this session", detail: "Unavailable", explanation:
                    "No supported endpoint or verified transfer path is connected. Moving a session between phones is not available here.")
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

    private var optionsMenu: some View {
        VStack(alignment: .leading, spacing: 14) {
            Button(optionsExpanded ? "Hide options" : "Options") {
                optionsExpanded.toggle()
                if !optionsExpanded { advancedExpanded = false }
            }
            .font(.title2.bold())
            .frame(maxWidth: .infinity, minHeight: 44, alignment: .leading)

            if optionsExpanded {
                Text("Options preview — controls are unavailable until a supported output and observation path qualifies.")
                    .font(.body)
                section("Volume", detail: "Unavailable", explanation:
                    "No qualified device volume control is connected.")
                section("Captions option", detail: "Unavailable", explanation:
                    "No authored caption track or selectable caption mode is connected.")
                section("Sound preset", detail: "Unavailable", explanation:
                    "A supported sound preset has not been confirmed for this device.")
                section("Dialogue preset", detail: "Unavailable", explanation:
                    "Dialogue requires a device capability for semantic sound presets.")
                section("Night preset", detail: "Unavailable", explanation:
                    "Night requires a device capability for semantic sound presets.")
                section("Custom Equalizer", detail: "Unavailable", explanation:
                    "Frequency bands require a qualified device capability.")
                section("Defaults and Undo", detail: "Unavailable", explanation:
                    "No confirmed device settings or verified change are available to save, restore, or undo.")

                Button(advancedExpanded ? "Hide advanced options" : "Advanced options") {
                    advancedExpanded.toggle()
                }
                .font(.title2.bold())
                .frame(maxWidth: .infinity, minHeight: 44, alignment: .leading)

                if advancedExpanded {
                    section("Device and route", detail: "Unknown", explanation:
                        "No qualified output hardware or route has been identified.")
                    section("Physical output", detail: "Unknown physical state", explanation:
                        "No independent observation is available. Options cannot verify audible output.")
                    section("Background monitoring", detail: "Unavailable", explanation:
                        "This screen receives only foreground hints; changes while away are unknown.")
                    section("Privacy and storage", detail: "No audio recorded by this app", explanation:
                        "This simulation menu stores no audio or personal settings.")
                    section("Move this session option", detail: "Unavailable", explanation:
                        "No authorized endpoint or verified transfer path is connected.")
                }
            }
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
