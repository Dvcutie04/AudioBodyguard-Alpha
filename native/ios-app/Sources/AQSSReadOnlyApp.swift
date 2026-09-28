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
    @Environment(\.dynamicTypeSize) private var textSize
    @StateObject private var audioHints = ForegroundAudioHints()
    @State private var optionsExpanded = false
    @State private var advancedExpanded = false
    @State private var checklistExpanded = false
    @State private var navigationVisible = false
    @State private var navigationTarget = "coverage"
    @State private var navigationRequest = 0
    @State private var helpVisible = false
    @State private var tutorialTopicID: String?
    @State private var tutorialIndex = 0
    @State private var previousOptions = false
    @State private var previousAdvanced = false
    @State private var previousChecklist = false
    private enum Focus: Hashable { case help, tutorial(String), destination(String) }
    @AccessibilityFocusState private var focusedElement: Focus?

    private var tutorialTopic: AQSSTutorialTopic? {
        AQSSTutorialContent.topics.first { $0.id == tutorialTopicID }
    }
    private var tutorialStep: AQSSTutorialStep? {
        guard let topic = tutorialTopic, topic.steps.indices.contains(tutorialIndex) else { return nil }
        return topic.steps[tutorialIndex]
    }
    private var tutorialStepKey: String { "\(tutorialTopicID ?? "")-\(tutorialIndex)" }
    private let destinations: [(title: String, target: String, area: String)] = [
        ("Coverage", "coverage", "home"),
        ("Readiness checklist", "capability", "checklist"),
        ("Sound options", "options", "options"),
        ("Advanced options", "advanced", "advanced"),
        ("Captions", "captions", "home"),
        ("Session history", "history", "home"),
        ("Foreground OS hint", "hint", "home"),
        ("Privacy and storage", "privacy", "advanced"),
        ("Session transfer", "handoff", "home"),
    ]

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
                        readinessChecklist
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
                .clipped()
                .accessibilityIdentifier("home-scroll")
                Divider()
                if let topic = tutorialTopic, let step = tutorialStep {
                    tutorialPanel(topic: topic, step: step)
                }
                HStack {
                    Button { navigationVisible = true } label: {
                        Text(textSize.isAccessibilitySize ? "Menu" : "Jump to")
                            .fixedSize(horizontal: false, vertical: true)
                            .frame(maxWidth: .infinity, minHeight: 44)
                            .contentShape(Rectangle())
                    }
                    .accessibilityIdentifier("section-navigation")
                    .accessibilityLabel("Jump to")
                    Button { helpVisible = true } label: {
                        Text(textSize.isAccessibilitySize ? "Help" : "Help & tutorials")
                            .fixedSize(horizontal: false, vertical: true)
                            .frame(maxWidth: .infinity, minHeight: 44)
                            .contentShape(Rectangle())
                    }
                    .accessibilityIdentifier("tutorial-help")
                    .accessibilityLabel("Help & tutorials")
                    .accessibilityFocused($focusedElement, equals: .help)
                }
                .padding(.horizontal)
            }
            .onChange(of: tutorialStepKey) { key in
                guard let target = tutorialStep?.target else { return }
                DispatchQueue.main.async {
                    guard tutorialStepKey == key, scenePhase == .active else { return }
                    if reduceMotion {
                        proxy.scrollTo(target, anchor: .top)
                    } else {
                        withAnimation(.easeInOut(duration: 0.18)) { proxy.scrollTo(target, anchor: .top) }
                    }
                    focusedElement = .tutorial(key)
                }
            }
            .onChange(of: navigationRequest) { request in
                DispatchQueue.main.async {
                    guard navigationRequest == request, scenePhase == .active else { return }
                    // Direct navigation is immediate and also works with Reduce Motion.
                    proxy.scrollTo(navigationTarget, anchor: .top)
                    focusedElement = .destination(navigationTarget)
                }
            }
            .confirmationDialog("Jump to a section", isPresented: $navigationVisible, titleVisibility: .visible) {
                ForEach(destinations, id: \.target) { destination in
                    Button(destination.title) {
                        closeTutorial(restore: false)
                        revealArea(destination.area)
                        navigationTarget = destination.target
                        navigationRequest += 1
                    }
                }
                Button("Cancel", role: .cancel) {}
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
            Button {
                closeTutorial(restore: false)
                optionsExpanded.toggle()
                if !optionsExpanded { advancedExpanded = false }
            } label: {
                Text(optionsExpanded ? "Hide options" : "Options")
                    .frame(maxWidth: .infinity, minHeight: 44, alignment: .leading)
                    .contentShape(Rectangle())
            }
            .font(.title2.bold())
            .modifier(TutorialHighlight(active: tutorialStep?.target == "options"))
            .accessibilityValue(optionsExpanded ? "Expanded" : "Collapsed")
            .accessibilityFocused($focusedElement, equals: .destination("options"))
            .id("options")

            if optionsExpanded {
                Text("Options preview — controls are unavailable until a supported output and observation path qualifies.")
                    .font(.body)
                helpButton("Help with options", topic: "sound")
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

                Button {
                    closeTutorial(restore: false)
                    advancedExpanded.toggle()
                } label: {
                    Text(advancedExpanded ? "Hide advanced options" : "Advanced options")
                        .frame(maxWidth: .infinity, minHeight: 44, alignment: .leading)
                        .contentShape(Rectangle())
                }
                .font(.title2.bold())
                .modifier(TutorialHighlight(active: tutorialStep?.target == "advanced"))
                .accessibilityValue(advancedExpanded ? "Expanded" : "Collapsed")
                .accessibilityFocused($focusedElement, equals: .destination("advanced"))
                .id("advanced")

                if advancedExpanded {
                    helpButton("Help with advanced options", topic: "advanced")
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

    private var readinessChecklist: some View {
        VStack(alignment: .leading, spacing: 14) {
            Button {
                closeTutorial(restore: false)
                checklistExpanded.toggle()
            } label: {
                Text(checklistExpanded ? "Hide readiness checklist" : "Show readiness checklist")
                    .frame(maxWidth: .infinity, minHeight: 44, alignment: .leading)
                    .contentShape(Rectangle())
            }
            .accessibilityValue(checklistExpanded ? "Expanded" : "Collapsed")
            if checklistExpanded {
                Text("These are unconfirmed requirements, not settings you can enable. A tutorial cannot complete them.")
                helpButton("Help with readiness", topic: "readiness")
                ForEach(AQSSTutorialContent.topics.first { $0.id == "readiness" }?.steps ?? [], id: \.target) { step in
                    section(step.title, detail: "Unknown", explanation: step.explanation, target: step.target)
                }
            }
        }
    }

    private func helpButton(_ title: String, topic: String) -> some View {
        Button { startTutorial(topic) } label: {
            Text(title).frame(maxWidth: .infinity, minHeight: 44, alignment: .leading)
                .contentShape(Rectangle())
        }
    }

    private func revealArea(_ area: String) {
        optionsExpanded = area == "options" || area == "advanced"
        advancedExpanded = area == "advanced"
        checklistExpanded = area == "checklist"
    }

    private func startTutorial(_ id: String) {
        guard AQSSTutorialContent.topics.contains(where: { $0.id == id }) else { return }
        if tutorialTopicID == nil {
            previousOptions = optionsExpanded
            previousAdvanced = advancedExpanded
            previousChecklist = checklistExpanded
        }
        tutorialTopicID = id
        tutorialIndex = 0
        revealTutorialArea()
    }

    private func revealTutorialArea() {
        guard let step = tutorialStep else { return }
        revealArea(step.area)
    }

    private func closeTutorial(restore: Bool = true) {
        guard tutorialTopicID != nil else { return }
        tutorialTopicID = nil
        tutorialIndex = 0
        if restore {
            optionsExpanded = previousOptions
            advancedExpanded = previousAdvanced
            checklistExpanded = previousChecklist
            focusedElement = .help
        }
    }

    private func tutorialPanel(topic: AQSSTutorialTopic, step: AQSSTutorialStep) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            ScrollView {
                VStack(alignment: .leading, spacing: 6) {
                    Text("Tutorial — \(topic.title)").font(.headline)
                        .accessibilityAddTraits(.isHeader)
                        .accessibilityFocused($focusedElement, equals: .tutorial(tutorialStepKey))
                    Text("Step \(tutorialIndex + 1) of \(topic.steps.count) • Highlighted: \(step.title)")
                        .font(.subheadline.bold())
                    Text(step.explanation)
                    Text(step.example).font(.callout)
                }.frame(maxWidth: .infinity, alignment: .leading)
            }
            .id("\(topic.id)-\(tutorialIndex)")
            .frame(height: textSize.isAccessibilitySize ? 180 : 160)
            Text("Scroll for details.").font(.caption)
                .fixedSize(horizontal: false, vertical: true)
            HStack {
                Button { tutorialIndex -= 1; revealTutorialArea() } label: {
                    Text("Back").fixedSize(horizontal: false, vertical: true)
                        .frame(maxWidth: .infinity, minHeight: 44)
                        .contentShape(Rectangle())
                }.disabled(tutorialIndex == 0)
                Button {
                    if tutorialIndex == topic.steps.count - 1 { closeTutorial() }
                    else { tutorialIndex += 1; revealTutorialArea() }
                } label: {
                    Text(tutorialIndex == topic.steps.count - 1 ? "Done" : "Next")
                        .fixedSize(horizontal: false, vertical: true)
                        .frame(maxWidth: .infinity, minHeight: 44)
                        .contentShape(Rectangle())
                }
                if !textSize.isAccessibilitySize { closeTutorialButton }
            }.frame(minHeight: 44)
            if textSize.isAccessibilitySize { closeTutorialButton }
        }
        .padding(.horizontal)
        .padding(.top, 8)
        .background(Color(.secondarySystemBackground))
        .accessibilityIdentifier("tutorial-panel")
    }

    private var closeTutorialButton: some View {
        Button { closeTutorial() } label: {
            Text(textSize.isAccessibilitySize ? "Close" : "Close tutorial")
                .fixedSize(horizontal: false, vertical: true)
                .frame(maxWidth: .infinity, minHeight: 44)
                .contentShape(Rectangle())
        }.accessibilityLabel("Close tutorial")
    }

    private func section(_ title: String, detail: String, explanation: String, target: String = "") -> some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(title).font(.title2.bold())
            Text(detail).font(.headline)
            Text(explanation).font(.body)
        }
        .accessibilityElement(children: .combine)
        .accessibilityAddTraits(.isHeader)
        .accessibilityFocused($focusedElement, equals: .destination(target))
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
