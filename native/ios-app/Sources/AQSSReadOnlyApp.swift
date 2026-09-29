import AVFAudio
import SwiftUI

@main
struct AQSSReadOnlyApp: App {
    var body: some Scene { WindowGroup { ReadOnlyHomeView() } }
}

private struct AppTheme {
    let dark: Bool
    private var tokens: [String: UInt32] { AQSSInterfaceContent.palettes[dark ? "midnight" : "daylight"]! }
    func color(_ key: String) -> Color {
        let hex = tokens[key]!
        return Color(red: Double((hex >> 16) & 255) / 255, green: Double((hex >> 8) & 255) / 255, blue: Double(hex & 255) / 255)
    }
    var background: Color { color("background") }
    var surface: Color { color("surface") }
    var raised: Color { color("raised") }
    var text: Color { color("text") }
    var muted: Color { color("muted") }
    var accent: Color { color("accent") }
    var violet: Color { color("violet") }
    var warning: Color { color("warning") }
    var outline: Color { color("outline") }
}

private struct AppButtonStyle: ButtonStyle {
    let theme: AppTheme
    var primary = false
    func makeBody(configuration: Configuration) -> some View {
        configuration.label.font(.body.weight(.semibold))
            .padding(.horizontal, 14).padding(.vertical, 8)
            .frame(minHeight: 44)
            .foregroundColor(primary ? theme.background : theme.accent)
            .background(primary ? theme.accent : theme.raised)
            .clipShape(RoundedRectangle(cornerRadius: 14))
            .opacity(configuration.isPressed ? 0.75 : 1)
    }
}

private struct ReadOnlyHomeView: View {
    @Environment(\.scenePhase) private var scenePhase
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @Environment(\.dynamicTypeSize) private var textSize
    @Environment(\.colorScheme) private var systemScheme
    @AppStorage("aqssAppearance") private var appearance = "midnight"
    @StateObject private var audioHints = ForegroundAudioHints()
    @State private var page = "home"
    @State private var pagesVisible = false
    @State private var optionsExpanded = true
    @State private var advancedExpanded = true
    @State private var checklistExpanded = false
    @State private var navigationVisible = false
    @State private var navigationTarget = "coverage"
    @State private var navigationRequest = 0
    @State private var helpVisible = false
    @State private var showingExample = false
    @State private var chartValuesVisible = false
    @State private var futureTitle = ""
    @State private var futureExplanation = ""
    @State private var futureVisible = false
    @State private var tutorialTopicID: String?
    @State private var tutorialIndex = 0
    @State private var beginnerTourFinished = false
    @State private var previousPage = "home"
    @State private var previousOptions = true
    @State private var previousAdvanced = true
    @State private var previousChecklist = false
    private enum Focus: Hashable { case help, tutorial(String), destination(String) }
    @AccessibilityFocusState private var focusedElement: Focus?

    private var theme: AppTheme { AppTheme(dark: appearance == "daylight" ? false : appearance == "system" ? systemScheme == .dark : true) }
    private var currentPage: AQSSInterfacePage { AQSSInterfaceContent.pages.first { $0.id == page }! }
    private var tutorialTopic: AQSSTutorialTopic? { AQSSTutorialContent.topics.first { $0.id == tutorialTopicID } }
    private var tutorialStep: AQSSTutorialStep? {
        guard let topic = tutorialTopic, topic.steps.indices.contains(tutorialIndex) else { return nil }
        return topic.steps[tutorialIndex]
    }
    private var tutorialStepKey: String { "\(tutorialTopicID ?? "")-\(tutorialIndex)" }
    private var beginnerTour: AQSSTutorialTopic { AQSSTutorialContent.topics.first { $0.id == "getting_started" }! }
    private let destinations: [(String, String)] = [
        ("Start here", "welcome"), ("Coverage", "coverage"), ("Readiness checklist", "capability"), ("Sound options", "options"),
        ("Advanced options", "advanced"), ("Captions", "captions"), ("Session history", "history"),
        ("Foreground OS hint", "hint"), ("Privacy and storage", "privacy"), ("Session transfer", "handoff")
    ]
    // This presentation layer receives no observation and cannot grant actuation.
    private let coverage = AQSSSessionEvidenceView.coverage(nil, runtimeId: "prototype", clockDomainId: "prototype", nowMonotonic: 0)
    private let capability = AQSSSessionEvidenceView.capability(AQSSCapabilityFacts(hardware: nil, qualification: nil, permission: nil, route: nil, runtime: nil, evidence: nil, observedMonotonic: 0, expiresMonotonic: 0, clockDomainId: "prototype"), clockDomainId: "prototype", nowMonotonic: 0)
    private var coverageTitle: String { coverage.state == .unknownPhysicalState && coverage.reason == "NO_OBSERVATION" ? "Unknown physical state" : "Unknown physical state — status unavailable" }
    private var capabilityTitle: String { capability.label == "UNKNOWN" && !capability.canActuate && capability.reasons.count == 6 ? "Six setup checks unknown" : "Unavailable — checklist unconfirmed" }

    var body: some View {
        ScrollViewReader { proxy in
            VStack(spacing: 0) {
                header
                ScrollView {
                    VStack(alignment: .leading, spacing: 22) {
                        pageHeading
                        pageContent
                        Text("SIMULATION · No audio path connected")
                            .font(.caption).foregroundColor(theme.muted)
                            .padding(.top, 4)
                    }
                    .frame(maxWidth: 680, alignment: .leading)
                    .padding(20).frame(maxWidth: .infinity)
                }
                .clipped().id(page).accessibilityIdentifier("home-scroll")
                if let topic = tutorialTopic, let step = tutorialStep { tutorialPanel(topic: topic, step: step) }
                navigationBar
            }
            .background(theme.background.ignoresSafeArea())
            .foregroundColor(theme.text).accentColor(theme.accent)
            .onChange(of: tutorialStepKey) { key in
                guard let target = tutorialStep?.target else { return }
                DispatchQueue.main.async {
                    guard key == tutorialStepKey, scenePhase == .active else { return }
                    if reduceMotion { proxy.scrollTo(target, anchor: .top) }
                    else { withAnimation(.easeInOut(duration: 0.18)) { proxy.scrollTo(target, anchor: .top) } }
                    focusedElement = .tutorial(key)
                }
            }
            .onChange(of: navigationRequest) { request in
                DispatchQueue.main.async {
                    guard request == navigationRequest, scenePhase == .active else { return }
                    proxy.scrollTo(navigationTarget, anchor: .top)
                    focusedElement = .destination(navigationTarget)
                }
            }
            .confirmationDialog("Jump to a section", isPresented: $navigationVisible, titleVisibility: .visible) {
                ForEach(destinations, id: \.1) { title, target in Button(title) { jump(target) } }
                Button("Cancel", role: .cancel) {}
            }
            .confirmationDialog("Choose a page", isPresented: $pagesVisible, titleVisibility: .visible) {
                ForEach(AQSSInterfaceContent.pages, id: \.id) { item in Button(item.title) { openPage(item.id) } }
                Button("Cancel", role: .cancel) {}
            }
            .confirmationDialog("Choose a tutorial", isPresented: $helpVisible, titleVisibility: .visible) {
                ForEach(AQSSTutorialContent.topics, id: \.id) { topic in Button(topic.title) { startTutorial(topic.id) } }
                Button("Cancel", role: .cancel) {}
            }
            .alert(futureTitle, isPresented: $futureVisible) { Button("Got it", role: .cancel) {} } message: { Text(futureExplanation) }
        }
        .preferredColorScheme(appearance == "system" ? nil : appearance == "daylight" ? .light : .dark)
        .onAppear { if scenePhase == .active { audioHints.start() } }
        .onDisappear { audioHints.stop() }
        .onChange(of: scenePhase) { phase in if phase == .active { audioHints.start() } else { audioHints.stop() } }
    }

    private var header: some View {
        HStack(spacing: 10) {
            Image(systemName: "waveform.path").font(.title2).foregroundColor(theme.accent).accessibilityHidden(true)
            if !textSize.isAccessibilitySize { Text("BODYGUARD").font(.caption.weight(.bold)).tracking(2) }
            Spacer(minLength: 0)
            Button { navigationVisible = true } label: { Image(systemName: "square.grid.2x2").frame(width: 44, height: 44).contentShape(Rectangle()) }
                .accessibilityLabel("Jump to").accessibilityIdentifier("section-navigation")
            Button { helpVisible = true } label: { Label("Help", systemImage: "questionmark.circle").font(.subheadline.weight(.semibold)).frame(minWidth: 44, minHeight: 44).contentShape(Rectangle()) }
                .accessibilityLabel("Help & tutorials").accessibilityIdentifier("tutorial-help").accessibilityFocused($focusedElement, equals: .help)
        }.padding(.horizontal, 20).padding(.vertical, 4).foregroundColor(theme.accent).background(theme.background)
    }

    private var pageHeading: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack { Text(currentPage.title.uppercased()).tracking(2).font(.caption.weight(.bold)).foregroundColor(theme.accent); Spacer(); badge("PREVIEW", color: theme.violet) }
            Text(currentPage.headline).font(.largeTitle.bold()).fixedSize(horizontal: false, vertical: true).accessibilityAddTraits(.isHeader)
            Text(currentPage.subtitle).font(.body).foregroundColor(theme.muted)
        }.accessibilityIdentifier("page-\(page)")
    }

    @ViewBuilder private var pageContent: some View {
        switch page {
        case "sound": soundPage
        case "devices": devicesPage
        case "insights": insightsPage
        case "settings": settingsPage
        default: homePage
        }
    }

    private var homePage: some View {
        VStack(spacing: 20) {
            card(target: "welcome") {
                badge(beginnerTourFinished ? "TOUR FINISHED" : "START HERE · 5 STEPS", color: theme.violet)
                Text(beginnerTourFinished ? "Explore at your pace." : "Meet Audio Bodyguard.").font(.title2.bold()).accessibilityAddTraits(.isHeader)
                Text("This is a read-only preview. It does not monitor or change audio.").foregroundColor(theme.muted)
                action(beginnerTourFinished ? "Replay 5-step tour" : "Start 5-step tour", icon: "arrow.right.circle", primary: true) { startTutorial("getting_started") }
                    .accessibilityIdentifier("start-beginner-tour")
                Text("No setup needed to explore. Help is always at the top.").font(.subheadline).foregroundColor(theme.muted)
            }
            card {
                Text("What can I do here?").font(.title3.bold()).accessibilityAddTraits(.isHeader)
                featureSummary("Available now", detail: "Explore pages, example graphs, themes and tutorials.", color: theme.accent)
                featureSummary("Preview only", detail: "Sound controls and device checks are explanations. Audio protection is not active.", color: theme.warning)
                featureSummary("Planned", detail: "Voice requests, personal profiles and background protection. Read more in Settings.", color: theme.violet)
            }
            card {
                Text("Your route through the app").font(.title3.bold()).accessibilityAddTraits(.isHeader)
                Text("Follow 1–5, or revisit any step.").foregroundColor(theme.muted)
                ForEach(Array(beginnerTour.steps.enumerated()), id: \.offset) { index, step in
                    let item = AQSSInterfaceContent.pages.first { $0.id == AQSSInterfaceContent.targetPages[step.target] }!
                    Button { startTutorial("getting_started", at: index) } label: {
                        HStack(spacing: 12) {
                            Text("\(index + 1)").font(.headline).frame(width: 30, height: 30).background(theme.surface).clipShape(Circle()).accessibilityHidden(true)
                            Text(step.title).fixedSize(horizontal: false, vertical: true)
                            Spacer(minLength: 0)
                            Image(systemName: item.icon).accessibilityHidden(true)
                        }.frame(maxWidth: .infinity, alignment: .leading)
                    }.buttonStyle(AppButtonStyle(theme: theme)).accessibilityLabel("Step \(index + 1). \(step.title)")
                }
            }
            card(target: "coverage") {
                HStack(alignment: .top) {
                    VStack(alignment: .leading, spacing: 12) {
                        Text("COVERAGE").font(.caption.weight(.bold)).tracking(2).foregroundColor(theme.muted)
                        Text(coverageTitle).font(.title2.bold()).foregroundColor(theme.warning).accessibilityAddTraits(.isHeader)
                        Text("No output observation").font(.subheadline.weight(.semibold))
                    }
                    Spacer(minLength: 4)
                    if !textSize.isAccessibilitySize { OrbitMark(theme: theme).frame(width: 96, height: 96).accessibilityHidden(true) }
                }
                Text("This preview does not monitor or protect audio. Start by exploring what a supported path needs.").foregroundColor(theme.muted)
                action("Review readiness", icon: "checklist", primary: true) { jump("capability"); checklistExpanded = true }
            }
            VStack(alignment: .leading, spacing: 12) {
                Text("Explore your space").font(.title3.bold()).accessibilityAddTraits(.isHeader)
                destinationCard("Sound controls", subtitle: "Presets, captions & equalizer", icon: "slider.horizontal.3") { openPage("sound") }
                destinationCard("Insights", subtitle: "Trends, evidence & examples", icon: "chart.xyaxis.line") { openPage("insights") }
            }
        }
    }

    private func featureSummary(_ title: String, detail: String, color: Color) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(title).font(.headline).foregroundColor(color)
            Text(detail).font(.subheadline).foregroundColor(theme.muted)
        }
    }

    private var soundPage: some View {
        VStack(alignment: .leading, spacing: 18) {
            card(target: "options") {
                Text("Sound options").font(.title2.bold()).accessibilityAddTraits(.isHeader)
                Text("Explore each control. A qualified device and observed result are needed before audio can change.").foregroundColor(theme.muted)
                action(optionsExpanded ? "Hide options" : "Options", icon: "slider.horizontal.3") { closeTutorial(restore: false); optionsExpanded.toggle() }
                    .accessibilityValue(optionsExpanded ? "Expanded" : "Collapsed")
                helpButton("Help with options", topic: "sound")
            }
            if optionsExpanded {
                section("Volume", detail: "Unavailable", explanation: "No qualified device volume control is connected.", target: "volume", icon: "speaker.wave.2")
                card(target: "sound") {
                    badge("UNAVAILABLE", color: theme.warning)
                    Text("Sound presets").font(.title2.bold()).accessibilityAddTraits(.isHeader)
                    Text("Device support determines which presets can be proposed.").foregroundColor(theme.muted)
                    preset("Dialogue", detail: "A proposed speech-focused setting", icon: "bubble.left.and.bubble.right")
                    preset("Night", detail: "A proposed quieter listening setting", icon: "moon")
                }
                section("Custom Equalizer", detail: "Unavailable", explanation: "Frequency-band adjustments need a qualified device capability. No bands are being changed.", target: "equalizer", icon: "slider.vertical.3")
                section("Captions option", detail: "Unavailable", explanation: "No authored caption track or selectable caption mode is connected.", target: "captionOption", icon: "captions.bubble")
                section("Defaults and Undo", detail: "Unavailable", explanation: "No confirmed device settings or verified change are available to save, restore, or undo.", target: "defaults", icon: "arrow.uturn.backward")
            }
            section("Captions", detail: "Not observed", explanation: "No authored caption track has been discovered or selected.", target: "captions", icon: "text.bubble")
            destinationCard("Advanced options", subtitle: "Device, privacy & background details", icon: "gearshape.2") { jump("advanced") }
        }
    }

    private var devicesPage: some View {
        VStack(alignment: .leading, spacing: 18) {
            card {
                badge("PATH NOT QUALIFIED", color: theme.warning)
                HStack { pathNode("iphone", title: "This app"); Image(systemName: "ellipsis").foregroundColor(theme.muted); pathNode("hifispeaker", title: "Output needed") }.accessibilityElement(children: .combine)
                Text("No qualified device connected").font(.title3.bold())
                Text("Connection, permission and physical observation must all be established. This diagram shows the requirements.").foregroundColor(theme.muted)
            }
            card(target: "capability") {
                Text("Readiness checklist").font(.title2.bold()).accessibilityAddTraits(.isHeader)
                Text(capabilityTitle).foregroundColor(theme.warning)
                Text("Hardware, qualification, permission, route, runtime and independent observation.").foregroundColor(theme.muted)
                action(checklistExpanded ? "Hide readiness checklist" : "Show readiness checklist", icon: "checklist", primary: true) { closeTutorial(restore: false); checklistExpanded.toggle() }
                    .accessibilityValue(checklistExpanded ? "Expanded" : "Collapsed")
                helpButton("Help with readiness", topic: "readiness")
            }
            if checklistExpanded {
                ForEach(AQSSTutorialContent.topics.first { $0.id == "readiness" }?.steps ?? [], id: \.target) { step in
                    section(step.title, detail: "Unknown", explanation: step.explanation, target: step.target, icon: "questionmark.circle")
                }
            }
            section("Foreground OS hint", detail: audioHints.lastHint, explanation: "Only this app's notifications while active. These cannot verify playback, another app's route, or physical output.", target: "hint", icon: "info.circle")
            section("Move this session", detail: "Unavailable", explanation: "No supported endpoint or verified transfer path is connected. Moving between iPhone and Android needs qualification in both directions.", target: "handoff", icon: "arrow.left.arrow.right")
            helpButton("Help with session transfer", topic: "handoff")
        }
    }

    private var insightsPage: some View {
        VStack(alignment: .leading, spacing: 18) {
            card(target: "trends") {
                HStack { Text("Audio trends").font(.title2.bold()); Spacer(); Image(systemName: "chart.xyaxis.line").foregroundColor(theme.violet).accessibilityHidden(true) }
                if showingExample {
                    badge(AQSSInterfaceContent.exampleLabel, color: theme.warning)
                    Text(AQSSInterfaceContent.exampleTitle).font(.headline)
                    Text("Invented values for learning this graph. They are not microphone readings, dB measurements or proof of protection.").foregroundColor(theme.muted)
                    ExampleChart(theme: theme).frame(height: 180)
                    Text(AQSSInterfaceContent.exampleUnit).font(.caption).foregroundColor(theme.muted)
                    action(chartValuesVisible ? "Hide chart values" : "Read chart values", icon: "list.bullet") { chartValuesVisible.toggle() }
                        .accessibilityValue(chartValuesVisible ? "Expanded" : "Collapsed")
                    if chartValuesVisible {
                        ForEach(Array(AQSSInterfaceContent.exampleValues.enumerated()), id: \.offset) { index, value in
                            Text("Sample \(index + 1): \(Int(value)) relative units").frame(maxWidth: .infinity, alignment: .leading).padding(.vertical, 3)
                        }
                    }
                    action("Close example", icon: "xmark") { showingExample = false; chartValuesVisible = false }
                } else {
                    Image(systemName: "waveform.path").font(.system(size: 42, weight: .light)).foregroundColor(theme.violet).padding(.vertical, 18).frame(maxWidth: .infinity).accessibilityHidden(true)
                    Text("No measurements yet").font(.title3.bold())
                    Text("A qualified observation source is needed before a real trend can appear. Missing measurements cannot establish safe audio.").foregroundColor(theme.muted)
                    action("Explore an example", icon: "chart.xyaxis.line", primary: true) { chartValuesVisible = false; showingExample = true }
                }
            }
            section("Session history", detail: "No observed events", explanation: "A missing history cannot establish continuous coverage. Requests and verified results will need distinct records.", target: "history", icon: "clock")
            card {
                Text("Read the whole picture").font(.title3.bold())
                Text("Future insights need source, time and verification context. Unknown intervals must remain visible.").foregroundColor(theme.muted)
                action("Review requirements", icon: "checklist") { jump("capability") }
            }
        }
    }

    private var settingsPage: some View {
        VStack(alignment: .leading, spacing: 18) {
            card(target: "appearance") {
                Text("Appearance").font(.title2.bold()).accessibilityAddTraits(.isHeader)
                Text("One visual language, in the light that suits you.").foregroundColor(theme.muted)
                ForEach(["midnight", "daylight", "system"], id: \.self) { value in
                    Button { appearance = value } label: {
                        HStack { Image(systemName: value == "midnight" ? "moon.stars" : value == "daylight" ? "sun.max" : "circle.lefthalf.filled"); Text(value.capitalized); Spacer(); if appearance == value { Image(systemName: "checkmark") } }.frame(maxWidth: .infinity, minHeight: 44)
                    }.buttonStyle(AppButtonStyle(theme: theme)).accessibilityLabel(value.capitalized).accessibilityValue(appearance == value ? "Selected" : "Not selected")
                }
            }
            card(target: "advanced") {
                Text("Advanced options").font(.title2.bold()).accessibilityAddTraits(.isHeader)
                action(advancedExpanded ? "Hide advanced options" : "Advanced options", icon: "gearshape.2") { closeTutorial(restore: false); advancedExpanded.toggle() }
                    .accessibilityValue(advancedExpanded ? "Expanded" : "Collapsed")
                helpButton("Help with advanced options", topic: "advanced")
            }
            if advancedExpanded {
                section("Device and route", detail: "Unknown", explanation: "No qualified output hardware or route has been identified.", target: "route", icon: "hifispeaker")
                section("Physical output", detail: "Unknown physical state", explanation: "No independent observation is available. Options cannot verify audible output.", target: "physical", icon: "waveform.path")
                section("Background monitoring", detail: "Unavailable", explanation: "Only foreground hints are received; changes while away are unknown.", target: "background", icon: "moon")
                section("Privacy and storage", detail: "No audio recorded by this app", explanation: "Only your appearance choice is saved locally. Tutorial and example progress are temporary. No tutorial analytics or audio uploads.", target: "privacy", icon: "lock.shield")
                section("Move this session option", detail: "Unavailable", explanation: "No authorized endpoint or verified transfer path is connected.", target: "handoffOption", icon: "arrow.left.arrow.right")
            }
            Text("On the horizon").font(.title2.bold()).accessibilityAddTraits(.isHeader)
            Text("Explore the direction. These features are not active.").foregroundColor(theme.muted)
            ForEach(AQSSInterfaceContent.future, id: \.id) { feature in
                destinationCard(feature.title, subtitle: feature.detail, icon: feature.id == "voice" ? "mic" : feature.id == "profiles" ? "person.crop.circle" : feature.id == "supervisor" ? "moon" : "doc.text") {
                    futureTitle = feature.title; futureExplanation = feature.explanation; futureVisible = true
                }
            }
            Button("Browse all tutorials") { helpVisible = true }.buttonStyle(AppButtonStyle(theme: theme))
        }
    }

    private var navigationBar: some View {
        Group {
            if textSize.isAccessibilitySize {
                Button { pagesVisible = true } label: { Label("Pages · \(currentPage.title)", systemImage: currentPage.icon).frame(maxWidth: .infinity, minHeight: 44) }
                    .buttonStyle(AppButtonStyle(theme: theme)).padding(12).accessibilityIdentifier("page-picker")
            } else {
                HStack(spacing: 0) {
                    ForEach(AQSSInterfaceContent.pages, id: \.id) { item in
                        Button { openPage(item.id) } label: {
                            VStack(spacing: 5) { Image(systemName: item.icon).font(.system(size: 20)); Text(item.title).font(.caption.weight(.semibold)) }
                                .frame(maxWidth: .infinity, minHeight: 56).contentShape(Rectangle())
                                .foregroundColor(page == item.id ? theme.accent : theme.muted)
                                .background(page == item.id ? theme.raised : Color.clear).clipShape(RoundedRectangle(cornerRadius: 14))
                        }.accessibilityIdentifier("tab-\(item.id)").accessibilityLabel(item.title).accessibilityValue(page == item.id ? "Selected" : "Not selected")
                    }
                }.padding(.horizontal, 10).padding(.vertical, 8)
            }
        }.background(theme.surface).overlay(Rectangle().fill(theme.outline.opacity(0.5)).frame(height: 1), alignment: .top)
    }

    private func card<Content: View>(target: String = "", @ViewBuilder content: () -> Content) -> some View {
        VStack(alignment: .leading, spacing: 14, content: content)
            .frame(maxWidth: .infinity, alignment: .leading).padding(20)
            .background(LinearGradient(colors: [theme.raised, theme.surface], startPoint: .topLeading, endPoint: .bottomTrailing))
            .clipShape(RoundedRectangle(cornerRadius: 22))
            .overlay(RoundedRectangle(cornerRadius: 22).stroke(tutorialStep?.target == target ? theme.accent : theme.outline.opacity(0.55), lineWidth: tutorialStep?.target == target ? 3 : 1))
            .accessibilityFocused($focusedElement, equals: .destination(target))
            .modifier(SectionAnchor(target: target))
    }
    private func badge(_ label: String, color: Color) -> some View {
        Text(label).font(.caption.weight(.bold)).foregroundColor(color).padding(.horizontal, 10).padding(.vertical, 6).background(color.opacity(0.10)).clipShape(Capsule())
    }
    private func action(_ title: String, icon: String, primary: Bool = false, perform: @escaping () -> Void) -> some View {
        Button(action: perform) { HStack { Text(title).fixedSize(horizontal: false, vertical: true); Spacer(minLength: 8); Image(systemName: icon).accessibilityHidden(true) }.frame(maxWidth: .infinity) }.buttonStyle(AppButtonStyle(theme: theme, primary: primary))
    }
    private func helpButton(_ title: String, topic: String) -> some View { action(title, icon: "questionmark.circle") { startTutorial(topic) } }
    private func section(_ title: String, detail: String, explanation: String, target: String, icon: String) -> some View {
        card(target: target) {
            HStack(alignment: .top) { Image(systemName: icon).foregroundColor(theme.violet).font(.title3).accessibilityHidden(true); Text(title).font(.title3.bold()).accessibilityAddTraits(.isHeader) }
            Text(detail).font(.headline).foregroundColor(detail.contains("Unknown") || detail == "Unavailable" ? theme.warning : theme.text)
            Text(explanation).foregroundColor(theme.muted)
        }
    }
    private func preset(_ title: String, detail: String, icon: String) -> some View {
        HStack(alignment: .top, spacing: 14) { Image(systemName: icon).foregroundColor(theme.violet).font(.title2).frame(width: 32).accessibilityHidden(true); VStack(alignment: .leading, spacing: 4) { Text(title + " preset").font(.headline); Text(detail).font(.subheadline).foregroundColor(theme.muted) } }.padding(14).frame(maxWidth: .infinity, alignment: .leading).background(theme.surface).clipShape(RoundedRectangle(cornerRadius: 14))
    }
    private func pathNode(_ icon: String, title: String) -> some View {
        VStack(spacing: 10) { Image(systemName: icon).font(.system(size: 34, weight: .light)).foregroundColor(theme.accent).accessibilityHidden(true); Text(title).font(.subheadline.weight(.semibold)) }.frame(maxWidth: .infinity).padding(.vertical, 12)
    }
    private func destinationCard(_ title: String, subtitle: String, icon: String, perform: @escaping () -> Void) -> some View {
        Button(action: perform) {
            HStack(alignment: .center, spacing: 14) {
                Image(systemName: icon).font(.title2).foregroundColor(theme.violet).frame(width: 32).accessibilityHidden(true)
                VStack(alignment: .leading, spacing: 5) { Text(title).font(.headline).foregroundColor(theme.text); Text(subtitle).font(.subheadline).foregroundColor(theme.muted) }
                Spacer(minLength: 0); Image(systemName: "chevron.right").font(.caption.bold()).foregroundColor(theme.accent).accessibilityHidden(true)
            }.frame(maxWidth: .infinity, minHeight: 52, alignment: .leading).padding(18).background(theme.surface).clipShape(RoundedRectangle(cornerRadius: 18)).overlay(RoundedRectangle(cornerRadius: 18).stroke(theme.outline.opacity(0.5), lineWidth: 1))
        }.buttonStyle(.plain)
    }

    private func openPage(_ id: String) {
        closeTutorial(restore: false); showingExample = false; page = id
        if id == "sound" { optionsExpanded = true }
        if id == "settings" { advancedExpanded = true }
    }
    private func reveal(_ target: String, area: String? = nil) {
        page = AQSSInterfaceContent.targetPages[target] ?? "home"
        if page == "sound" { optionsExpanded = true }
        if page == "settings" { advancedExpanded = true }
        if area == "checklist" { checklistExpanded = true }
    }
    private func jump(_ target: String) {
        closeTutorial(restore: false); showingExample = false; reveal(target)
        navigationTarget = target; navigationRequest += 1
    }
    private func startTutorial(_ id: String, at index: Int = 0) {
        guard let topic = AQSSTutorialContent.topics.first(where: { $0.id == id }), topic.steps.indices.contains(index) else { return }
        if tutorialTopicID == nil { previousPage = page; previousOptions = optionsExpanded; previousAdvanced = advancedExpanded; previousChecklist = checklistExpanded }
        showingExample = false; chartValuesVisible = false; tutorialTopicID = id; tutorialIndex = index; revealTutorialArea()
    }
    private func revealTutorialArea() { showingExample = false; chartValuesVisible = false; if let step = tutorialStep { reveal(step.target, area: step.area) } }
    private func closeTutorial(restore: Bool = true) {
        guard tutorialTopicID != nil else { return }
        tutorialTopicID = nil; tutorialIndex = 0
        if restore { page = previousPage; optionsExpanded = previousOptions; advancedExpanded = previousAdvanced; checklistExpanded = previousChecklist; focusedElement = .help }
    }
    private func tutorialPanel(topic: AQSSTutorialTopic, step: AQSSTutorialStep) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            if topic.id == "getting_started" && !textSize.isAccessibilitySize {
                HStack(spacing: 8) {
                    ForEach(topic.steps.indices, id: \.self) { index in
                        Text("\(index + 1)").font(.caption.bold()).frame(width: 26, height: 26)
                            .foregroundColor(index == tutorialIndex ? theme.background : theme.muted)
                            .background(index == tutorialIndex ? theme.accent : theme.raised).clipShape(Circle())
                    }
                    Spacer()
                    Image(systemName: currentPage.icon).foregroundColor(theme.violet)
                }.accessibilityHidden(true)
            }
            ScrollView {
                VStack(alignment: .leading, spacing: 8) {
                    Text("Tutorial — \(topic.title)").font(.headline).foregroundColor(theme.accent).accessibilityAddTraits(.isHeader).accessibilityFocused($focusedElement, equals: .tutorial(tutorialStepKey))
                    Text("Step \(tutorialIndex + 1) of \(topic.steps.count) • Highlighted: \(step.title)").font(.subheadline.bold())
                    Text(step.explanation)
                    Text(step.example).font(.callout).foregroundColor(theme.muted)
                }.frame(maxWidth: .infinity, alignment: .leading)
            }.id(tutorialStepKey).frame(height: textSize.isAccessibilitySize ? 150 : 140).clipped()
            Text("Scroll for details.").font(.caption).foregroundColor(theme.muted)
            HStack {
                Button { tutorialIndex -= 1; revealTutorialArea() } label: { Text("Back").frame(maxWidth: .infinity, minHeight: 44) }.disabled(tutorialIndex == 0)
                Button { if tutorialIndex == topic.steps.count - 1 { if topic.id == "getting_started" { beginnerTourFinished = true }; closeTutorial() } else { tutorialIndex += 1; revealTutorialArea() } } label: { Text(tutorialIndex == topic.steps.count - 1 ? "Done" : "Next").frame(maxWidth: .infinity, minHeight: 44) }
                if !textSize.isAccessibilitySize { closeTutorialButton }
            }
            if textSize.isAccessibilitySize { closeTutorialButton }
        }.padding(16).background(theme.surface).overlay(Rectangle().fill(theme.accent).frame(height: 2), alignment: .top).accessibilityIdentifier("tutorial-panel")
    }
    private var closeTutorialButton: some View {
        Button { closeTutorial() } label: { Text(textSize.isAccessibilitySize ? "Close" : "Close tutorial").fixedSize(horizontal: false, vertical: true).frame(maxWidth: .infinity, minHeight: 44).contentShape(Rectangle()) }.accessibilityLabel("Close tutorial")
    }
}

private struct SectionAnchor: ViewModifier {
    let target: String
    @ViewBuilder func body(content: Content) -> some View {
        if target.isEmpty { content } else { content.id(target) }
    }
}

private struct OrbitMark: View {
    let theme: AppTheme
    var body: some View {
        ZStack {
            ForEach(0..<3) { n in Circle().stroke(n == 1 ? theme.violet.opacity(0.4) : theme.accent.opacity(0.3), lineWidth: 1).padding(CGFloat(n * 10)) }
            Image(systemName: "waveform.path").font(.system(size: 34, weight: .light)).foregroundColor(theme.accent)
        }
    }
}

private struct ExampleChart: View {
    let theme: AppTheme
    var body: some View {
        VStack(spacing: 8) {
            HStack(spacing: 8) {
                VStack { Text("100"); Spacer(); Text("50"); Spacer(); Text("0") }.font(.caption2).foregroundColor(theme.muted)
                GeometryReader { geo in
                    ZStack {
                        Path { p in for n in 0...2 { let y = geo.size.height * CGFloat(n) / 2; p.move(to: CGPoint(x: 0, y: y)); p.addLine(to: CGPoint(x: geo.size.width, y: y)) } }.stroke(theme.outline, style: StrokeStyle(lineWidth: 1, dash: [4, 5]))
                        Path { p in
                            for (i, value) in AQSSInterfaceContent.exampleValues.enumerated() {
                                let point = CGPoint(x: CGFloat(i) / CGFloat(AQSSInterfaceContent.exampleValues.count - 1) * geo.size.width, y: CGFloat(1 - value / 100) * geo.size.height)
                                if i == 0 { p.move(to: point) } else { p.addLine(to: point) }
                            }
                        }.stroke(theme.accent, style: StrokeStyle(lineWidth: 3, lineCap: .round, lineJoin: .round))
                    }
                }
            }
            HStack { Text("Sample 1"); Spacer(); Text("Sample 8") }.font(.caption2).foregroundColor(theme.muted)
        }.accessibilityElement(children: .ignore).accessibilityLabel("Example chart. Synthetic relative levels: 18, 24, 21, 64, 40, 30, 45, 25. No measured audio.")
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
