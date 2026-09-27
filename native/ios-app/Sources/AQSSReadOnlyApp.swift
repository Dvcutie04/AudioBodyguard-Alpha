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
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @StateObject private var audioHints = ForegroundAudioHints()
    @State private var optionsExpanded = false
    @State private var advancedExpanded = false
    @State private var helpVisible = false
    @State private var tutorialTopicID: String?
    @State private var tutorialIndex = 0
    @State private var previousOptions = false
    @State private var previousAdvanced = false
    @AccessibilityFocusState private var tutorialHeadingFocused: Bool

    private var tutorialTopic: AQSSTutorialTopic? {
        AQSSTutorialContent.topics.first { $0.id == tutorialTopicID }
    }
    private var tutorialStep: AQSSTutorialStep? {
        guard let topic = tutorialTopic, topic.steps.indices.contains(tutorialIndex) else { return nil }
        return topic.steps[tutorialIndex]
    }

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
        ScrollViewReader { proxy in
            VStack(spacing: 0) {
                ScrollView {
                    VStack(alignment: .leading, spacing: 18) {
                        Text("SIMULATION — no audio path connected")
                            .font(.headline)
                        optionsMenu
                        section("Coverage", detail: coverageTitle, explanation:
                            "No output observation. This screen does not monitor or protect audio.", target: "coverage")
                        section("Supported controls", detail: capabilityTitle, explanation:
                            "Output hardware, qualification, permission, route, runtime, and independent observation are unconfirmed. This simulation cannot offer a control.", target: "capability")
                        section("Captions", detail: "Not observed", explanation:
                            "No authored caption track has been discovered or selected.", target: "captions")
                        section("Session history", detail: "No observed events", explanation:
                            "A missing history cannot establish continuous coverage.", target: "history")
                        section("Foreground OS hint", detail: audioHints.lastHint, explanation:
                            "Only this app's audio-session notifications while this screen is active. A notification cannot verify playback, another app's route, or physical output.", target: "hint")
                        section("Move this session", detail: "Unavailable", explanation:
                            "No supported endpoint or verified transfer path is connected. Moving a session between phones is not available here.", target: "handoff")
                        section("Next step", detail: "Qualify a supported path", explanation:
                            "A supported output and independent observation path must be qualified before this app can report an active listening session.")
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(24)
                }
                .accessibilityIdentifier("home-scroll")
                Divider()
                if let topic = tutorialTopic, let step = tutorialStep {
                    tutorialPanel(topic: topic, step: step)
                }
                Button { helpVisible = true } label: {
                    Label("Help & tutorials", systemImage: "questionmark.circle")
                        .frame(maxWidth: .infinity, minHeight: 44)
                        .contentShape(Rectangle())
                }
                .accessibilityIdentifier("tutorial-help")
                .padding(.horizontal)
            }
            .onChange(of: tutorialStep?.target) { target in
                guard let target = target else { return }
                DispatchQueue.main.async {
                    if reduceMotion {
                        proxy.scrollTo(target, anchor: .top)
                    } else {
                        withAnimation(.easeInOut(duration: 0.18)) { proxy.scrollTo(target, anchor: .top) }
                    }
                    tutorialHeadingFocused = true
                }
            }
            .confirmationDialog("Choose a tutorial", isPresented: $helpVisible, titleVisibility: .visible) {
                ForEach(AQSSTutorialContent.topics, id: \.id) { topic in
                    Button(topic.title) { startTutorial(topic.id) }
                }
                Button("Cancel", role: .cancel) {}
            }
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
                closeTutorial(restore: false)
                optionsExpanded.toggle()
                if !optionsExpanded { advancedExpanded = false }
            }
            .font(.title2.bold())
            .frame(maxWidth: .infinity, minHeight: 44, alignment: .leading)
            .modifier(TutorialHighlight(active: tutorialStep?.target == "options"))
            .id("options")

            if optionsExpanded {
                Text("Options preview — controls are unavailable until a supported output and observation path qualifies.")
                    .font(.body)
                Button("Help with options") { startTutorial("sound") }
                    .frame(minHeight: 44)
                Group {
                    section("Volume", detail: "Unavailable", explanation:
                        "No qualified device volume control is connected.", target: "volume")
                    section("Captions option", detail: "Unavailable", explanation:
                        "No authored caption track or selectable caption mode is connected.", target: "captionOption")
                    section("Sound preset", detail: "Unavailable", explanation:
                        "A supported sound preset has not been confirmed for this device.", target: "sound")
                    section("Dialogue preset", detail: "Unavailable", explanation:
                        "Dialogue requires a device capability for semantic sound presets.")
                    section("Night preset", detail: "Unavailable", explanation:
                        "Night requires a device capability for semantic sound presets.")
                    section("Custom Equalizer", detail: "Unavailable", explanation:
                        "Frequency bands require a qualified device capability.", target: "equalizer")
                    section("Defaults and Undo", detail: "Unavailable", explanation:
                        "No confirmed device settings or verified change are available to save, restore, or undo.", target: "defaults")
                }

                Button(advancedExpanded ? "Hide advanced options" : "Advanced options") {
                    closeTutorial(restore: false)
                    advancedExpanded.toggle()
                }
                .font(.title2.bold())
                .frame(maxWidth: .infinity, minHeight: 44, alignment: .leading)
                .modifier(TutorialHighlight(active: tutorialStep?.target == "advanced"))
                .id("advanced")

                if advancedExpanded {
                    Button("Help with advanced options") { startTutorial("advanced") }
                        .frame(minHeight: 44)
                    section("Device and route", detail: "Unknown", explanation:
                        "No qualified output hardware or route has been identified.", target: "route")
                    section("Physical output", detail: "Unknown physical state", explanation:
                        "No independent observation is available. Options cannot verify audible output.", target: "physical")
                    section("Background monitoring", detail: "Unavailable", explanation:
                        "This screen receives only foreground hints; changes while away are unknown.", target: "background")
                    section("Privacy and storage", detail: "No audio recorded by this app", explanation:
                        "This simulation menu stores no audio or personal settings.", target: "privacy")
                    section("Move this session option", detail: "Unavailable", explanation:
                        "No authorized endpoint or verified transfer path is connected.", target: "handoffOption")
                }
            }
        }
    }

    private func startTutorial(_ id: String) {
        guard AQSSTutorialContent.topics.contains(where: { $0.id == id }) else { return }
        if tutorialTopicID == nil {
            previousOptions = optionsExpanded
            previousAdvanced = advancedExpanded
        }
        tutorialTopicID = id
        tutorialIndex = 0
        revealTutorialArea()
    }

    private func revealTutorialArea() {
        guard let step = tutorialStep else { return }
        optionsExpanded = step.area != "home"
        advancedExpanded = step.area == "advanced"
    }

    private func closeTutorial(restore: Bool = true) {
        guard tutorialTopicID != nil else { return }
        tutorialTopicID = nil
        tutorialIndex = 0
        if restore {
            optionsExpanded = previousOptions
            advancedExpanded = previousAdvanced
        }
    }

    private func tutorialPanel(topic: AQSSTutorialTopic, step: AQSSTutorialStep) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            ScrollView {
                VStack(alignment: .leading, spacing: 6) {
                    Text("Tutorial — \(topic.title)").font(.headline)
                        .accessibilityFocused($tutorialHeadingFocused)
                    Text("Step \(tutorialIndex + 1) of \(topic.steps.count) • Highlighted: \(step.title)")
                        .font(.subheadline.bold())
                    Text(step.explanation)
                    Text(step.example).font(.callout)
                }.frame(maxWidth: .infinity, alignment: .leading)
            }
            .id("\(topic.id)-\(tutorialIndex)")
            .frame(maxHeight: 160)
            Text("Scroll the explanation to read more.").font(.caption)
            HStack {
                Button { tutorialIndex -= 1; revealTutorialArea() } label: {
                    Text("Back").frame(maxWidth: .infinity, minHeight: 44)
                        .contentShape(Rectangle())
                }.disabled(tutorialIndex == 0)
                Button {
                    if tutorialIndex == topic.steps.count - 1 { closeTutorial() }
                    else { tutorialIndex += 1; revealTutorialArea() }
                } label: {
                    Text(tutorialIndex == topic.steps.count - 1 ? "Done" : "Next")
                        .frame(maxWidth: .infinity, minHeight: 44)
                        .contentShape(Rectangle())
                }
                Button { closeTutorial() } label: {
                    Text("Close tutorial").frame(maxWidth: .infinity, minHeight: 44)
                        .contentShape(Rectangle())
                }
            }.frame(minHeight: 44)
        }
        .padding(.horizontal)
        .padding(.top, 8)
        .background(Color(.secondarySystemBackground))
        .accessibilityIdentifier("tutorial-panel")
    }

    private func section(_ title: String, detail: String, explanation: String, target: String = "") -> some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(title).font(.title2.bold())
            Text(detail).font(.headline)
            Text(explanation).font(.body)
        }
        .accessibilityElement(children: .combine)
        .modifier(TutorialHighlight(active: tutorialStep?.target == target))
        .id(target.isEmpty ? title : target)
    }
}

private struct TutorialHighlight: ViewModifier {
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    let active: Bool
    func body(content: Content) -> some View {
        content
            .background(active ? Color.accentColor.opacity(0.10) : Color.clear)
            .overlay(RoundedRectangle(cornerRadius: 6)
                .stroke(active ? Color.accentColor : Color.clear, lineWidth: 3)
                .allowsHitTesting(false))
            .accessibilityValue(active ? "Tutorial focus" : "")
            .animation(reduceMotion ? nil : .easeInOut(duration: 0.18), value: active)
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
