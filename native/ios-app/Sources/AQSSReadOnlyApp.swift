import AVFAudio
import SwiftUI

@main
struct AQSSReadOnlyApp: App {
    var body: some Scene { WindowGroup { ReadOnlyHomeView() } }
}

/// A separate Simulator presentation build; never evidence or authorization.
private enum AppPreviewMode {
    #if AQSS_CONNECTED_DEMO && targetEnvironment(simulator)
    static let connectedDemo = true
    #else
    static let connectedDemo = false
    #endif
}

struct AppTheme {
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
    var control: Color { color("control") }
    var controlText: Color { color("controlText") }
    var controlBorder: Color { color("controlBorder") }
}

struct AppButtonStyle: ButtonStyle {
    let theme: AppTheme
    var primary = false
    @Environment(\.isEnabled) private var isEnabled
    func makeBody(configuration: Configuration) -> some View {
        configuration.label.font(.body.weight(.semibold))
            .padding(.horizontal, 14).padding(.vertical, 8)
            .frame(minHeight: 44)
            .foregroundColor(primary ? theme.controlText : theme.text)
            .background(primary ? theme.control : theme.raised)
            .clipShape(RoundedRectangle(cornerRadius: 14))
            .overlay(RoundedRectangle(cornerRadius: 14).stroke(primary ? theme.controlBorder : theme.outline, lineWidth: 1))
            .opacity(!isEnabled ? 0.45 : configuration.isPressed ? 0.75 : 1)
    }
}

/// The owner's original photograph, including its white background.
struct RoseButton: View {
    let title: String
    let theme: AppTheme
    var compact = false
    let action: () -> Void
    @Environment(\.dynamicTypeSize) private var textSize
    var body: some View {
        Button(action: action) {
            HStack(spacing: 8) {
                Image("TribalRose").resizable().scaledToFill()
                    .frame(width: 52, height: 68).clipped()
                    .clipShape(RoundedRectangle(cornerRadius: 6)).accessibilityHidden(true)
                if !compact && !textSize.isAccessibilitySize { Text(title).fixedSize(horizontal: title == "Help", vertical: true) }
            }.frame(minWidth: 44, minHeight: 44)
        }.buttonStyle(AppButtonStyle(theme: theme)).accessibilityLabel(title)
    }
}

struct ConnectionHeadView: View {
    let connected: Bool
    var demonstration = false
    @Environment(\.scenePhase) private var scenePhase
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @State private var breathing = false
    private var animate: Bool { connected && scenePhase == .active && !reduceMotion }
    var body: some View {
        Image("ConnectionHead").resizable().scaledToFit().frame(maxWidth: 210)
            .saturation(connected ? 1 : 0)
            .scaleEffect(breathing ? 1.015 : 1)
            .accessibilityLabel(demonstration ? "AI head. Connected appearance demonstration." : connected ? "AI head. Verified connection active." : "AI head. Connection not verified. Black and white.")
            .accessibilityIdentifier("connection-head")
            .onAppear { updateAnimation() }
            .onChange(of: animate) { _ in updateAnimation() }
            .onDisappear { breathing = false }
    }
    private func updateAnimation() {
        withAnimation(nil) { breathing = false }
        if animate { withAnimation(.easeInOut(duration: 1.8).repeatForever(autoreverses: true)) { breathing = true } }
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
    @State private var voiceCheckVisible = false
    @State private var photoCheckVisible = false
    @State private var setupRequest: SetupGuideRequest?
    @State private var selectedSetupSystem: String?
    @State private var pictureTarget: String?
    @State private var completedPictureRoute: String?
    @State private var moreFeatures = false
    @State private var tutorialHelp = false
    @State private var voiceAfterGuide = false
    @State private var pendingSetupGroup: String?
    @State private var pagesVisible = false
    @State private var optionsExpanded = false
    @State private var advancedExpanded = false
    @State private var settingSwitches = AQSSSettingSwitchState()
    @State private var settingResetTask: Task<Void, Never>?
    private struct SettingExplanation: Identifiable {
        let id, title, explanation: String
    }
    @State private var settingHelp: SettingExplanation?
    @State private var deviceDetails = false
    @State private var detailSections: Set<String> = []
    private struct PageLocation {
        let page, target: String
        let options, advanced, checklist, devices: Bool
        let details: Set<String>
        let example, chartValues: Bool
    }
    @State private var pageHistory: [PageLocation] = []
    @State private var checklistExpanded = false
    @State private var navigationVisible = false
    @State private var navigationTarget = "page-heading"
    @State private var navigationRequest = 0
    @State private var helpVisible = false
    @State private var showingExample = false
    @State private var chartValuesVisible = false
    @AppStorage("aqssGuideDismissedV1") private var guideDismissed = false
    @State private var checkedFirstVisit = false
    @State private var guide = AQSSGuideProgress()
    @State private var pausedGuide: AQSSGuideProgress?
    private var tutorialTopicID: String? { guide.topicID }
    private var tutorialIndex: Int { guide.index }
    @State private var beginnerTourFinished = false
    @State private var previousPage = "home"
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
    private var showTourFinished: Bool { beginnerTourFinished && tutorialTopicID != "getting_started" }
    private let destinations: [(String, String)] = [
        ("Start here", "welcome"), ("Coverage", "coverage"), ("Readiness checklist", "capability"), ("Sound options", "options"),
        ("Advanced Settings", "advanced"), ("Captions", "captions"), ("Session history", "history"),
        ("Foreground OS hint", "hint"), ("Privacy and storage", "privacy"), ("Session transfer", "handoff")
    ]
    // This presentation layer receives no observation and cannot grant actuation.
    private let coverage = AQSSSessionEvidenceView.coverage(nil, runtimeId: "prototype", clockDomainId: "prototype", nowMonotonic: 0)
    private let capability = AQSSSessionEvidenceView.capability(AQSSCapabilityFacts(hardware: nil, qualification: nil, permission: nil, route: nil, runtime: nil, evidence: nil, observedMonotonic: 0, expiresMonotonic: 0, clockDomainId: "prototype"), clockDomainId: "prototype", nowMonotonic: 0)
    private var coverageTitle: String { coverage.state == .unknownPhysicalState && coverage.reason == "NO_OBSERVATION" ? "Unknown physical state" : "Unknown physical state — status unavailable" }
    private var capabilityTitle: String { capability.label == "UNKNOWN" && !capability.canActuate && capability.reasons.count == 6 ? "Six setup checks unknown" : "Unavailable — checklist unconfirmed" }
    // Demo artwork and guide completion are never inputs to this gate.
    private var settingsConnectionVerified: Bool { coverage.state == .active && capability.label == "AVAILABLE_FOR_REVIEW" }

    var body: some View {
        ScrollViewReader { proxy in
            VStack(spacing: 0) {
                if let topic = tutorialTopic, let step = tutorialStep {
                    tutorialPanel(topic: topic, step: step)
                } else {
                    header
                    ScrollView {
                        VStack(alignment: .leading, spacing: 22) {
                            pageHeading.id("page-heading")
                            pageContent
                        }.frame(maxWidth: 680, alignment: .leading).padding(20).frame(maxWidth: .infinity)
                    }.clipped().id(page == "settings" && advancedExpanded ? "settings-advanced" : page).accessibilityIdentifier("home-scroll")
                    navigationBar
                }
            }
            .background(theme.background.ignoresSafeArea())
            .foregroundColor(theme.text).accentColor(theme.accent)
            .onChange(of: navigationRequest) { request in
                DispatchQueue.main.async {
                    guard request == navigationRequest, scenePhase == .active else { return }
                    // A new page's ScrollView identity already starts at the top.
                    // Scrolling its heading again can remove the content padding.
                    if navigationTarget != "page-heading" {
                        proxy.scrollTo(navigationTarget, anchor: .top)
                        focusedElement = .destination(navigationTarget)
                    }
                }
            }
            .sheet(isPresented: $voiceCheckVisible) { VoiceCheckView(theme: theme) }
            .sheet(isPresented: $photoCheckVisible) { TVPhotoView(theme: theme) }
            .sheet(item: $settingHelp, onDismiss: {
                if let group = pendingSetupGroup { pendingSetupGroup = nil; showSetup(group) }
            }) { item in
                VStack(spacing: 0) {
                    HStack(alignment: .top, spacing: 12) {
                        Text(item.title).font(.title2.bold()).fixedSize(horizontal: false, vertical: true)
                            .frame(maxWidth: .infinity, alignment: .leading).accessibilityAddTraits(.isHeader)
                        RoseButton(title: "Back", theme: theme, compact: true) { settingHelp = nil }
                            .accessibilityIdentifier("setting-help-close")
                    }.padding(20)
                    ScrollView {
                      VStack(alignment: .leading, spacing: 20) {
                        Text(item.explanation).fixedSize(horizontal: false, vertical: true)
                        if item.id == "voice" {
                            action("Show voice steps", icon: "mic") { pendingSetupGroup = "voice"; settingHelp = nil }
                        }
                      }.frame(maxWidth: .infinity, alignment: .leading).padding(20)
                    }.accessibilityIdentifier("setting-help-scroll")
                }.background(theme.background).foregroundColor(theme.text)
            }
            .sheet(item: $setupRequest, onDismiss: {
                if let target = pictureTarget, let route = completedPictureRoute {
                    _ = guide.completePictures(expectedTarget: target, routeID: route)
                }
                pictureTarget = nil; completedPictureRoute = nil
                if voiceAfterGuide { voiceAfterGuide = false; voiceCheckVisible = true }
            }) { request in SetupGuidesView(theme: theme, initialGroup: request.group, deviceGroup: request.deviceGroup, returningToTutorial: tutorialTopicID != nil, onDeviceGroupSelected: { selectedSetupSystem = $0 }, onVoiceCheck: { voiceAfterGuide = true }, onPartOne: { route in
                if pictureTarget == "connectionPlan" && guide.completePictures(expectedTarget: "connectionPlan", routeID: route) { pictureTarget = "connectionCheck" }
            }, onFinish: { completedPictureRoute = $0 }) }
            .sheet(isPresented: $navigationVisible) {
                menuSheet("Jump to a section") {
                    ForEach(destinations, id: \.1) { title, target in action(title, icon: "arrow.right") { navigationVisible = false; jump(target) } }
                    action("Cancel", icon: "xmark") { navigationVisible = false }
                }
            }
            .sheet(isPresented: $pagesVisible) {
                menuSheet("Choose a page") {
                    ForEach(AQSSInterfaceContent.pages, id: \.id) { item in action(item.title, icon: item.icon) { pagesVisible = false; openPage(item.id) } }
                    action("Cancel", icon: "xmark") { pagesVisible = false }
                }
            }
            .sheet(isPresented: $helpVisible, onDismiss: {
                if let group = pendingSetupGroup { pendingSetupGroup = nil; showSetup(group) }
            }) {
                menuSheet("Choose a tutorial") {
                    Text(currentPage.headline).font(.headline)
                    Text(currentPage.subtitle).foregroundColor(theme.muted)
                    action("Illustrated setup guides", icon: "rectangle.stack") { pendingSetupGroup = ""; helpVisible = false }
                    action("Voice check — step by step", icon: "mic") { pendingSetupGroup = "voice"; helpVisible = false }
                    ForEach(AQSSTutorialContent.topics, id: \.id) { topic in action(topic.title, icon: "questionmark.circle") { helpVisible = false; startTutorial(topic.id) } }
                    action("Cancel", icon: "xmark") { helpVisible = false }
                }
            }
        }
        .preferredColorScheme(appearance == "system" ? nil : appearance == "daylight" ? .light : .dark)
        .onAppear {
            if !checkedFirstVisit { checkedFirstVisit = true; if !guideDismissed && !AppPreviewMode.connectedDemo { startTutorial("getting_started") } }
            if scenePhase == .active { audioHints.start() }
        }
        .onDisappear { audioHints.stop(); resetSettingSwitches() }
        .onChange(of: scenePhase) { phase in
            if phase == .active { audioHints.start() }
            else { audioHints.stop(); resetSettingSwitches() }
        }
        .onChange(of: settingsConnectionVerified) { verified in if !verified { resetSettingSwitches() } }
        .onChange(of: tutorialStepKey) { _ in moreFeatures = false; tutorialHelp = false }
        .onChange(of: guide.selections["chooseTV"]) { brand in
            if let brand = brand, let selected = selectedSetupSystem, selected != brand && !selected.hasPrefix(brand + "_") { selectedSetupSystem = nil }
        }
    }

    private func showSetup(_ group: String = "") {
        completedPictureRoute = nil
        pictureTarget = tutorialTopicID == "getting_started" && ["connectionPlan", "connectionCheck"].contains(tutorialStep?.target ?? "") ? tutorialStep?.target : nil
        let remembered = selectedSetupSystem.flatMap { id in
            AQSSSetupContent.groups.contains(where: { $0.id == id }) && !group.isEmpty && id.hasPrefix(group + "_") ? id : nil
        }
        setupRequest = SetupGuideRequest(group: remembered ?? group, deviceGroup: selectedSetupSystem ?? guide.selected("chooseTV")?.id ?? "")
    }

    private var header: some View {
        HStack(spacing: 10) {
            if !pageHistory.isEmpty {
                Button { backPage() } label: { Image(systemName: "arrow.left").frame(width: 24, height: 24) }.accessibilityLabel("Back").accessibilityIdentifier("page-back")
            }
            Image(systemName: "waveform.path").font(.title2).foregroundColor(theme.accent).accessibilityHidden(true)
            if !textSize.isAccessibilitySize && pageHistory.isEmpty {
                Text("BODYGUARD").font(.caption.weight(.bold)).tracking(2).lineLimit(1).minimumScaleFactor(0.8)
            }
            Spacer(minLength: 0)
            Button { navigationVisible = true } label: { Image(systemName: "square.grid.2x2").frame(width: 24, height: 24).contentShape(Rectangle()) }
                .accessibilityLabel("Jump to").accessibilityIdentifier("section-navigation")
            RoseButton(title: "Help", theme: theme) { helpVisible = true }
                .accessibilityLabel("Help & tutorials").accessibilityIdentifier("tutorial-help").accessibilityFocused($focusedElement, equals: .help)
        }.buttonStyle(AppButtonStyle(theme: theme)).padding(.horizontal, 20).padding(.vertical, 4).foregroundColor(theme.accent).background(theme.background)
    }

    private var pageHeading: some View {
        Text(page == "settings" && advancedExpanded ? "Advanced Settings" : currentPage.title.uppercased()).font(.title.bold())
            .fixedSize(horizontal: false, vertical: true).accessibilityAddTraits(.isHeader)
            .accessibilityIdentifier("page-\(page)")
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
        VStack(spacing: 16) {
            card(target: "welcome") {
                ConnectionHeadView(connected: AppPreviewMode.connectedDemo || coverage.state == .active, demonstration: AppPreviewMode.connectedDemo)
                    .frame(maxWidth: .infinity)
                Text(AppPreviewMode.connectedDemo || coverage.state == .active ? "Connected" : "Connection not verified")
                    .font(.headline).frame(maxWidth: .infinity).accessibilityAddTraits(.isHeader)
                    .accessibilityIdentifier("connection-status")
                if AppPreviewMode.connectedDemo {
                    Text("Appetize demo").font(.caption).foregroundColor(theme.muted)
                        .frame(maxWidth: .infinity).accessibilityIdentifier("connection-demo-notice")
                }
                action(beginnerTourFinished ? "Replay connection guide" : "TV & smart-home guide", icon: "arrow.right.circle", primary: true) { startTutorial("getting_started") }
                    .accessibilityIdentifier("start-beginner-tour")
                if pausedGuide != nil {
                    RoseButton(title: "Back to Tutorial", theme: theme) { resumeTutorial() }
                        .accessibilityIdentifier("resume-tutorial")
                }
                action(detailSections.contains("coverage") ? "Hide status details" : "Status details", icon: "info.circle") { toggleDetails("coverage") }
                if detailSections.contains("coverage") {
                    VStack(alignment: .leading, spacing: 12) {
                        Text(coverageTitle).font(.headline).foregroundColor(theme.warning)
                        Text("No output observation").font(.subheadline)
                        Text(AppPreviewMode.connectedDemo ? "The colored head demonstrates a connected appearance. No physical TV connection or audio protection is verified." : "This preview has no verified TV connection. Setup pictures explain the official apps.")
                            .font(.callout).foregroundColor(theme.muted)
                        action("Review readiness", icon: "checklist") { jump("capability"); checklistExpanded = true }
                    }.id("coverage")
                }
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
            destinationCard("Voice check", subtitle: "See microphone activity and recognized words", icon: "waveform") { voiceCheckVisible = true }
            card(target: "options") {
                Text("Sound options").font(.title2.bold()).accessibilityAddTraits(.isHeader)
                action(optionsExpanded ? "Hide options" : "Options", icon: "slider.horizontal.3") { closeTutorial(restore: false); optionsExpanded.toggle() }
                    .accessibilityValue(optionsExpanded ? "Expanded" : "Collapsed")
                if optionsExpanded {
                    helpButton("Help with options", topic: "sound")
                }
            }
            if optionsExpanded {
                section("Volume", detail: "Unavailable", explanation: "No qualified device volume control is connected.", target: "volume", icon: "speaker.wave.2")
                card(target: "sound") {
                    badge("UNAVAILABLE", color: theme.warning)
                    Text("Sound presets").font(.title2.bold()).accessibilityAddTraits(.isHeader)
                    preset("Dialogue", detail: "A proposed speech-focused setting", icon: "bubble.left.and.bubble.right")
                    preset("Night", detail: "A proposed quieter listening setting", icon: "moon")
                }
                section("Custom Equalizer", detail: "Unavailable", explanation: "Frequency-band adjustments need a qualified device capability. No bands are being changed.", target: "equalizer", icon: "slider.vertical.3")
                section("Captions option", detail: "Unavailable", explanation: "No authored caption track or selectable caption mode is connected.", target: "captionOption", icon: "captions.bubble")
                section("Defaults and Undo", detail: "Unavailable", explanation: "No confirmed device settings or verified change are available to save, restore, or undo.", target: "defaults", icon: "arrow.uturn.backward")
            }
            section("Captions", detail: "Not observed", explanation: "No authored caption track has been discovered or selected.", target: "captions", icon: "text.bubble")
        }
    }

    private var devicesPage: some View {
        VStack(alignment: .leading, spacing: 18) {
            destinationCard("TV photo setup", subtitle: "Read a model label or Network settings photo", icon: "camera") { photoCheckVisible = true }
            destinationCard("Illustrated setup guides", subtitle: "TV pairing, Google Home & Alexa · one picture at a time", icon: "rectangle.stack") { showSetup() }
            Text("No qualified device connected").font(.subheadline).foregroundColor(theme.muted)
            action(deviceDetails ? "Hide device details" : "More device details", icon: "info.circle") { deviceDetails.toggle() }
            if deviceDetails {
            helpButton("TV & smart-home guide", topic: "getting_started")
            connectionStages(currentTarget: nil)
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
                    action(detailSections.contains("trends") ? "Hide measurement details" : "Measurement details", icon: "info.circle") { toggleDetails("trends") }
                    if detailSections.contains("trends") { Text("A qualified observation source is needed before a real trend can appear. Missing measurements cannot establish safe audio.").foregroundColor(theme.muted) }
                    action("Explore an example", icon: "chart.xyaxis.line", primary: true) { chartValuesVisible = false; showingExample = true }
                }
            }
            section("Session history", detail: "No observed events", explanation: "A missing history cannot establish continuous coverage. Requests and verified results will need distinct records.", target: "history", icon: "clock")
        }
    }

    private var settingsPage: some View {
        VStack(alignment: .leading, spacing: 18) {
            if !advancedExpanded {
            card(target: "appearance") {
                HStack {
                    Text("Appearance").font(.title2.bold()).accessibilityAddTraits(.isHeader)
                    Spacer()
                    question("Appearance", explanation: "Midnight uses a dark background. Daylight uses a light background. System follows your phone’s appearance. This choice is saved on this phone and works without a TV connection.", target: "appearance")
                }
                ForEach(["midnight", "daylight", "system"], id: \.self) { value in
                    Button { appearance = value } label: {
                        HStack { Image(systemName: value == "midnight" ? "moon.stars" : value == "daylight" ? "sun.max" : "circle.lefthalf.filled"); Text(value.capitalized); Spacer(); if appearance == value { Image(systemName: "checkmark") } }.frame(maxWidth: .infinity, minHeight: 44)
                    }.buttonStyle(AppButtonStyle(theme: theme, primary: appearance == value)).accessibilityLabel(value.capitalized).accessibilityValue(appearance == value ? "Selected" : "Not selected")
                }
            }
            action("Advanced Settings", icon: "chevron.right") {
                rememberPage(); closeTutorial(restore: false); advancedExpanded = true
                navigationTarget = "page-heading"; navigationRequest += 1
            }
            } else {
                whiteSettingsCard(target: "advanced") {
                    ForEach(AQSSInterfaceContent.settings, id: \.id) { item in
                        settingRow(item)
                        if item.id != AQSSInterfaceContent.settings.last?.id { Divider().padding(.leading, 42) }
                    }
                }
                whiteSettingsCard {
                    settingInfo("Device and route", detail: "Unknown", explanation: "No qualified output hardware or route has been identified. Use the matching device guide, then independently verify its output path.", target: "route")
                    Divider()
                    settingInfo("Physical output", detail: "Unknown", explanation: "No independent observation is available. Options cannot verify audible output. A completed guide or an app button does not prove a physical connection.", target: "physical")
                    Divider()
                    settingInfo("Privacy and storage", explanation: "No audio files saved by this app. Appearance and guide dismissal stay on this phone. Voice check uses the microphone only after you start it. Audio, recognized words and photo details are not saved by AQSS or uploaded. Closing the tool clears its details.", target: "privacy")
                    Divider()
                    settingInfo("Move this session", detail: "Unavailable", explanation: "No authorized endpoint or verified transfer path is connected. Moving a session between iPhone and Android requires qualification in both directions.", target: "handoffOption")
                    Divider()
                    settingInfo("Private support report", detail: "Planned", explanation: AQSSInterfaceContent.future.first { $0.id == "support" }!.explanation, target: "support")
                }
                helpButton("Advanced Settings tutorial", topic: "advanced")
            }
        }
    }

    private func question(_ title: String, explanation: String, target: String, light: Bool = false) -> some View {
        Button { settingHelp = SettingExplanation(id: target, title: title, explanation: explanation) } label: {
            Text("[?]").font(.system(size: 18, weight: .semibold)).frame(width: 44, height: 44)
                .foregroundColor(light ? .black : theme.text)
        }.buttonStyle(.plain).accessibilityLabel("About " + title).accessibilityIdentifier("help-" + target)
    }
    private func whiteSettingsCard<Content: View>(target: String = "", @ViewBuilder content: () -> Content) -> some View {
        VStack(alignment: .leading, spacing: 0, content: content).padding(.horizontal, 14).padding(.vertical, 4)
            .frame(maxWidth: .infinity, alignment: .leading).background(Color.white)
            .clipShape(RoundedRectangle(cornerRadius: 20))
            .foregroundColor(.black).modifier(SectionAnchor(target: target))
    }
    private func settingRow(_ item: AQSSInterfaceSetting) -> some View {
        VStack(alignment: .leading, spacing: 0) {
            if textSize.isAccessibilitySize {
                Label(item.title, systemImage: item.icon).font(.body.weight(.semibold)).padding(.top, 14)
                HStack { question(item.title, explanation: item.explanation, target: item.id, light: true); Spacer(); settingToggle(item) }
            } else {
                HStack(spacing: 10) {
                    Image(systemName: item.icon).font(.title3).frame(width: 28).accessibilityHidden(true)
                        .foregroundColor(settingSwitches.isOn(item.id) ? Color(red: 0, green: 0.4, blue: 0.46) : .black)
                    Text(item.title).font(.body.weight(.semibold)).fixedSize(horizontal: false, vertical: true)
                    Spacer(minLength: 0)
                    question(item.title, explanation: item.explanation, target: item.id, light: true)
                    settingToggle(item)
                }.padding(.vertical, 10)
            }
            if settingSwitches.isAttempting(item.id) {
                Text("Not connected.").font(.subheadline.weight(.semibold)).padding(.bottom, 12)
                    .accessibilityIdentifier("not-connected-" + item.id)
            }
        }.modifier(SectionAnchor(target: item.id))
    }
    private func settingToggle(_ item: AQSSInterfaceSetting) -> some View {
        Toggle(item.title, isOn: Binding(get: { settingSwitches.isOn(item.id) }, set: { _ in
            settingSwitches.press(item.id, connectionVerified: settingsConnectionVerified, now: ProcessInfo.processInfo.systemUptime)
            scheduleSettingReset()
        })).labelsHidden().toggleStyle(SwitchToggleStyle(tint: Color(red: 100 / 255.0, green: 218 / 255.0, blue: 232 / 255.0)))
            .overlay(Capsule().stroke(settingSwitches.isOn(item.id) ? Color(red: 0, green: 0.4, blue: 0.46) : Color(white: 0.5), lineWidth: 0.7).frame(width: 51, height: 31).allowsHitTesting(false))
            .frame(minHeight: 44).fixedSize()
            .accessibilityLabel(item.title).accessibilityValue(settingSwitches.isAttempting(item.id) ? "On temporarily. Not connected." : settingSwitches.isOn(item.id) ? "On" : "Off")
            .accessibilityIdentifier("setting-" + item.id)
    }
    private func settingInfo(_ title: String, detail: String = "", explanation: String, target: String) -> some View {
        HStack(alignment: .center) {
            VStack(alignment: .leading, spacing: 4) {
                Text(title).font(.body.weight(.semibold))
                if !detail.isEmpty { Text(detail).font(.subheadline).foregroundColor(Color(white: 0.3)) }
            }.fixedSize(horizontal: false, vertical: true)
            Spacer(minLength: 8)
            question(title, explanation: explanation, target: target, light: true)
        }.padding(.vertical, 8).modifier(SectionAnchor(target: target))
    }
    private func scheduleSettingReset() {
        settingResetTask?.cancel(); settingResetTask = nil
        guard let expiry = settingSwitches.nextExpiry else { return }
        let remaining = max(0, expiry - ProcessInfo.processInfo.systemUptime)
        settingResetTask = Task { @MainActor in
            do { try await Task.sleep(nanoseconds: UInt64(remaining * 1_000_000_000)) } catch { return }
            guard !Task.isCancelled else { return }
            settingSwitches.expire(now: ProcessInfo.processInfo.systemUptime)
            scheduleSettingReset()
        }
    }
    private func resetSettingSwitches() { settingResetTask?.cancel(); settingResetTask = nil; settingSwitches.connectionLost() }

    private var navigationBar: some View {
        Group {
            if textSize.isAccessibilitySize {
                Button { pagesVisible = true } label: { Label("Pages · \(currentPage.title)", systemImage: currentPage.icon).frame(maxWidth: .infinity, minHeight: 44) }
                    .buttonStyle(AppButtonStyle(theme: theme)).padding(12).accessibilityIdentifier("page-picker")
            } else {
                HStack(spacing: 5) {
                    ForEach(AQSSInterfaceContent.pages, id: \.id) { item in
                        Button { openPage(item.id) } label: {
                            VStack(spacing: 5) { Image(systemName: item.icon).font(.system(size: 20)); Text(item.title).font(.caption.weight(.semibold)) }
                                .frame(maxWidth: .infinity, minHeight: 56).contentShape(Rectangle())
                                .foregroundColor(page == item.id ? theme.accent : theme.muted)
                                .background(page == item.id ? theme.raised : Color.clear).clipShape(RoundedRectangle(cornerRadius: 14))
                                .overlay(alignment: .top) { if page == item.id { Capsule().fill(theme.accent).frame(width: 18, height: 3).padding(.top, 3) } }
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
            HStack(alignment: .top) { Image(systemName: icon).foregroundColor(theme.violet).font(.title3).accessibilityHidden(true); Text(title).font(.title3.bold()).accessibilityAddTraits(.isHeader); Spacer(minLength: 0); question(title, explanation: explanation, target: target) }
            Text(detail).font(.headline).foregroundColor(detail.contains("Unknown") || detail == "Unavailable" ? theme.warning : theme.text)
        }
    }
    private func preset(_ title: String, detail: String, icon: String) -> some View {
        HStack(alignment: .center, spacing: 14) { Image(systemName: icon).foregroundColor(theme.violet).font(.title2).frame(width: 32).accessibilityHidden(true); Text(title + " preset").font(.headline); Spacer(minLength: 0); question(title + " preset", explanation: AQSSInterfaceContent.settings.first { $0.id == title.lowercased() }!.explanation, target: title.lowercased()) }.padding(14).frame(maxWidth: .infinity, alignment: .leading).background(theme.surface).clipShape(RoundedRectangle(cornerRadius: 14))
    }
    private func pathNode(_ icon: String, title: String) -> some View {
        VStack(spacing: 10) { Image(systemName: icon).font(.system(size: 34, weight: .light)).foregroundColor(theme.accent).accessibilityHidden(true); Text(title).font(.subheadline.weight(.semibold)) }.frame(maxWidth: .infinity).padding(.vertical, 12)
    }
    private func destinationCard(_ title: String, subtitle: String, icon: String, perform: @escaping () -> Void) -> some View {
        Button(action: perform) {
            HStack(spacing: 14) {
                Image(systemName: icon).font(.title2).accessibilityHidden(true)
                VStack(alignment: .leading, spacing: 5) { Text(title).font(.headline); Text(subtitle).font(.subheadline) }
                Spacer(minLength: 0)
                Image(systemName: "chevron.right").accessibilityHidden(true)
            }.frame(maxWidth: .infinity, minHeight: 52, alignment: .leading)
        }.buttonStyle(AppButtonStyle(theme: theme))
    }
    private func menuSheet<Content: View>(_ title: String, @ViewBuilder content: () -> Content) -> some View {
        ScrollView { VStack(alignment: .leading, spacing: 16) {
            HStack { Text(title).font(.title2.bold()); Spacer(); RoseButton(title: "Back", theme: theme, compact: true) { helpVisible = false; navigationVisible = false; pagesVisible = false } }
            content()
        }.padding(20) }
            .background(theme.background).foregroundColor(theme.text).accessibilityIdentifier("menu-scroll")
    }

    private func openPage(_ id: String) {
        guard page != id else { return }
        rememberPage(); closeTutorial(restore: false); showingExample = false; page = id
        optionsExpanded = false; advancedExpanded = false; checklistExpanded = false; deviceDetails = false
        detailSections.removeAll()
        navigationTarget = "page-heading"; navigationRequest += 1
    }
    private func toggleDetails(_ id: String) { if !detailSections.insert(id).inserted { detailSections.remove(id) } }
    private func rememberPage() {
        if pageHistory.count >= 32 { pageHistory.removeFirst() }
        pageHistory.append(PageLocation(page: page, target: navigationTarget, options: optionsExpanded, advanced: advancedExpanded, checklist: checklistExpanded, devices: deviceDetails, details: detailSections, example: showingExample, chartValues: chartValuesVisible))
    }
    private func backPage() {
        guard let previous = pageHistory.popLast() else { return }
        page = previous.page; optionsExpanded = previous.options; advancedExpanded = previous.advanced; checklistExpanded = previous.checklist
        deviceDetails = previous.devices; detailSections = previous.details
        showingExample = previous.example; chartValuesVisible = previous.chartValues
        navigationTarget = previous.target; navigationRequest += 1
    }
    private func reveal(_ target: String, area: String? = nil) {
        page = AQSSInterfaceContent.targetPages[target] ?? "home"
        if page == "sound" { optionsExpanded = true }
        if page == "settings" { advancedExpanded = true }
        if page == "devices" { deviceDetails = true }
        detailSections.insert(target)
        if area == "checklist" { checklistExpanded = true }
    }
    private func jump(_ target: String) {
        let destination = AQSSInterfaceContent.targetPages[target] ?? "home"
        if destination != page || (destination == "settings" && !advancedExpanded && target != "appearance") { rememberPage() }
        closeTutorial(restore: false); showingExample = false; reveal(target)
        navigationTarget = target; navigationRequest += 1
    }
    private func startTutorial(_ id: String) {
        if tutorialTopicID == nil { previousPage = page }
        guard guide.start(id) else { return }
        pausedGuide = nil
        showingExample = false; chartValuesVisible = false
    }
    private func closeTutorial(restore: Bool = true) {
        guard tutorialTopicID != nil else { return }
        if tutorialTopicID == "getting_started" { guideDismissed = true }
        guide.close()
        if restore { page = previousPage; focusedElement = .help }
    }
    private func exitToHome() {
        pausedGuide = guide
        if page != "home" { rememberPage() }
        closeTutorial(restore: false)
        page = "home"; navigationTarget = "page-heading"; navigationRequest += 1
    }
    private func resumeTutorial() {
        if let saved = pausedGuide {
            previousPage = page; guide = saved; pausedGuide = nil
            moreFeatures = false; tutorialHelp = false
        } else { startTutorial("getting_started") }
    }
    private func tutorialPanel(topic: AQSSTutorialTopic, step: AQSSTutorialStep) -> some View {
        VStack(spacing: 0) {
            VStack(alignment: .leading, spacing: 4) {
                HStack {
                    Text("Step \(tutorialIndex + 1) of \(topic.steps.count)").font(.subheadline.weight(.semibold)).foregroundColor(theme.muted)
                    Spacer(minLength: 8)
                    RoseButton(title: "Exit Home", theme: theme) { exitToHome() }
                        .accessibilityIdentifier("exit-tutorial")
                }
                if topic.id == "getting_started" { Text(AQSSTutorialContent.previewNotice).font(.caption).foregroundColor(theme.muted) }
            }.padding(.horizontal, 20).padding(.vertical, 10)
            GuideScrollView(screenKey: tutorialStepKey, identifier: "guide-scroll", onStepReady: { key in
                if scenePhase == .active { focusedElement = .tutorial(key) }
            }) {
                VStack(alignment: .leading, spacing: 16) {
                    HStack(spacing: 18) {
                        Image(systemName: "iphone")
                        Image(systemName: step.target == "chooseHome" ? "house" : "tv")
                        if step.target == "welcome" { Image(systemName: "hifispeaker") }
                    }.font(.system(size: 32, weight: .light)).foregroundColor(theme.violet).accessibilityHidden(true)
                    Text(step.title).font(.largeTitle.bold()).fixedSize(horizontal: false, vertical: true)
                        .accessibilityAddTraits(.isHeader).accessibilityFocused($focusedElement, equals: .tutorial(tutorialStepKey))
                    Text(step.explanation).font(.body).fixedSize(horizontal: false, vertical: true)
                    if topic.id == "getting_started" && step.target == "welcome" { connectionStages(currentTarget: nil) }
                    else if topic.id == "getting_started", let stage = AQSSTutorialContent.connectionStages.first(where: { $0.targets.contains(step.target) }), !["connectionPlan", "connectionCheck"].contains(step.target) {
                        Text("Connection \(stage.number) of 2").font(.caption.weight(.semibold)).foregroundColor(theme.accent)
                    }
                    ForEach(guide.choices, id: \.id) { choice in
                        Button { _ = guide.select(choice.id) } label: {
                            HStack(spacing: 14) {
                                Image(systemName: choice.icon == "speaker" ? "hifispeaker" : choice.icon).font(.title2).accessibilityHidden(true)
                                Text(choice.title).fixedSize(horizontal: false, vertical: true)
                                Spacer(minLength: 0)
                                if guide.selected(step.target)?.id == choice.id { Image(systemName: "checkmark.circle.fill").accessibilityHidden(true) }
                            }.frame(maxWidth: .infinity, minHeight: 44, alignment: .leading)
                        }.buttonStyle(AppButtonStyle(theme: theme, primary: guide.selected(step.target)?.id == choice.id)).accessibilityIdentifier("choice-\(choice.id)")
                            .accessibilityLabel(choice.title).accessibilityValue(guide.selected(step.target)?.id == choice.id ? "Selected" : "Not selected")
                    }
                    if ["connectionPlan", "connectionCheck"].contains(step.target) {
                        if step.target == "connectionCheck" {
                            action("Phone Wi-Fi pictures", icon: "wifi", primary: true) { showSetup("phone") }
                        }
                        if step.target == "connectionPlan" { selectedConnectionActions(primaryTV: true) }
                    }
                    if topic.id == "getting_started" && step.target == "welcome" {
                        featureCatalog
                    } else if !step.example.isEmpty {
                        if !step.example.isEmpty {
                            Button { tutorialHelp.toggle() } label: {
                                Label(tutorialHelp ? "Hide help" : AQSSTutorialContent.helpLabel, systemImage: tutorialHelp ? "chevron.up" : "chevron.down")
                                    .frame(maxWidth: .infinity, minHeight: 44, alignment: .leading)
                            }.buttonStyle(AppButtonStyle(theme: theme)).accessibilityValue(tutorialHelp ? "Expanded" : "Collapsed")
                            if tutorialHelp {
                                VStack(alignment: .leading, spacing: 12) {
                                    Text(step.example).font(.callout).foregroundColor(theme.muted).fixedSize(horizontal: false, vertical: true)
                                    if ["connectionPlan", "connectionCheck"].contains(step.target) {
                                        ForEach(["chooseTV", "chooseHome"], id: \.self) { target in
                                            if let selected = guide.selected(target) { Text(selected.detail).font(.callout).foregroundColor(theme.muted) }
                                        }
                                        if step.target == "connectionCheck" { selectedConnectionActions(primaryTV: false) }
                                    }
                                }.padding(14).background(theme.surface).clipShape(RoundedRectangle(cornerRadius: 14))
                            }
                        }
                    }
                }.frame(maxWidth: 640, alignment: .leading).padding(20).frame(maxWidth: .infinity)
            }
            VStack(spacing: 8) {
                if !guide.choices.isEmpty {
                    Text(guide.selected(step.target).map { "Selected: \($0.title)" } ?? "Choose one option above to continue.")
                        .font(.subheadline).foregroundColor(theme.muted)
                }
                HStack(spacing: 12) {
                    if tutorialIndex > 0 { Button("Back") { guide.back() }.buttonStyle(AppButtonStyle(theme: theme)) }
                    action(guide.isLast ? (topic.id == "getting_started" ? "Open full app" : "Done") : (tutorialIndex == 0 ? (topic.id == "getting_started" ? AQSSTutorialContent.startLabel : "Begin") : "Next"), icon: "arrow.right", primary: !["connectionPlan", "connectionCheck"].contains(step.target)) {
                        guard guide.canContinue else { return }
                        if guide.isLast { if topic.id == "getting_started" { beginnerTourFinished = true }; closeTutorial() }
                        else { _ = guide.next() }
                    }.disabled(!guide.canContinue).accessibilityIdentifier("guide-next")
                }
            }.padding(16).background(theme.surface)
        }
    }
    @ViewBuilder private func selectedConnectionActions(primaryTV: Bool) -> some View {
        ForEach(["chooseTV", "chooseHome"], id: \.self) { target in
            if let selected = guide.selected(target), !["both", "neither"].contains(selected.id) {
                action("Show \(selected.title) steps", icon: target == "chooseTV" ? "tv" : "house", primary: primaryTV && target == "chooseTV") { showSetup(selected.id) }
                    .accessibilityIdentifier("setup-from-\(selected.id)")
            }
        }
        if guide.selected("chooseHome")?.id == "both" {
            ForEach(["alexa", "google"], id: \.self) { id in
                if let choice = AQSSTutorialContent.choices["chooseHome"]?.first(where: { $0.id == id }) {
                    action("Show \(choice.title) steps", icon: "house") { showSetup(id) }
                }
            }
        }
    }

    private func connectionStages(currentTarget: String?) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("Both connections are required").font(.subheadline.bold()).accessibilityAddTraits(.isHeader)
            ForEach(AQSSTutorialContent.connectionStages, id: \.number) { stage in
                HStack(alignment: .top, spacing: 12) {
                    Text("\(stage.number)").font(.headline).foregroundColor(theme.accent)
                        .frame(width: 28, height: 28).background(theme.raised).clipShape(Circle()).accessibilityHidden(true)
                    VStack(alignment: .leading, spacing: 3) {
                        Text("\(stage.number). \(stage.title)").font(.subheadline.weight(.semibold)).fixedSize(horizontal: false, vertical: true)
                        if let target = currentTarget, stage.targets.contains(target) {
                            Text("Current guide section").font(.caption).foregroundColor(theme.accent)
                        }
                    }
                }.accessibilityElement(children: .combine)
            }
        }.padding(16).frame(maxWidth: .infinity, alignment: .leading).background(theme.surface).clipShape(RoundedRectangle(cornerRadius: 18))
    }

    private var featureCatalog: some View {
        VStack(alignment: .leading, spacing: 12) {
            Button(moreFeatures ? "Fewer features" : AQSSTutorialContent.moreFeaturesLabel) { moreFeatures.toggle() }
                .buttonStyle(AppButtonStyle(theme: theme)).accessibilityIdentifier("more-features")
                .accessibilityValue(moreFeatures ? "Expanded" : "Collapsed")
            if moreFeatures {
            ForEach(AQSSTutorialContent.features, id: \.id) { feature in
                VStack(alignment: .leading, spacing: 3) {
                    Text(feature.title).font(.callout.weight(.semibold)).fixedSize(horizontal: false, vertical: true)
                    Text(feature.availability == "preview" ? "Preview" : "Planned").font(.subheadline.weight(.semibold)).foregroundColor(theme.accent)
                    Text(feature.detail).font(.callout).foregroundColor(theme.muted)
                }.accessibilityElement(children: .combine)
            }
            }
        }.frame(maxWidth: .infinity, alignment: .leading)
            .accessibilityIdentifier("welcome-feature-catalog")
    }

}

/// Keeps the scrolling container alive when a guide changes its content.
/// Reset only its position: replacing the container also tears down gestures,
/// accessibility elements and the native scrolling view on every Next/Back.
struct GuideScrollView<Content: View>: View {
    let screenKey: String
    let identifier: String
    let onStepReady: (String) -> Void
    let content: Content
    @State private var lifetimeID = UUID().uuidString
    private static var traceNavigation: Bool { ProcessInfo.processInfo.arguments.contains("--aqss-trace-navigation") }

    init(screenKey: String, identifier: String, onStepReady: @escaping (String) -> Void = { _ in }, @ViewBuilder content: () -> Content) {
        self.screenKey = screenKey; self.identifier = identifier; self.onStepReady = onStepReady
        self.content = content()
    }
    var body: some View {
        ScrollViewReader { proxy in
            ScrollView { content.id("guide-content-top") }
                .accessibilityIdentifier(identifier)
                // Opt-in test evidence only; no user content or telemetry.
                .accessibilityValue(Self.traceNavigation ? lifetimeID : "")
                .onChange(of: screenKey) { key in
                    var transaction = Transaction(animation: nil)
                    transaction.disablesAnimations = true
                    withTransaction(transaction) { proxy.scrollTo("guide-content-top", anchor: .top) }
                    onStepReady(key)
                }
                .onAppear { onStepReady(screenKey) }
        }
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
