import AVFoundation
import Foundation
import SwiftUI

/// Reads a single session route only. No category/activation/preference setters,
/// permission requests, player, engine, microphone or device identifiers.
@MainActor
private enum SessionOutputReader {
    static func capture() throws -> OutputDetailsSnapshot {
        let outputs = AVAudioSession.sharedInstance().currentRoute.outputs
        let types = outputs.prefix(OutputDetailsSnapshot.maxPorts).map { port -> IOSOutputKind in
            switch port.portType {
            case .builtInSpeaker: return .speaker
            case .builtInReceiver: return .receiver
            case .headphones: return .headphones
            case .bluetoothA2DP: return .bluetoothA2DP
            case .bluetoothHFP: return .bluetoothHFP
            case .bluetoothLE: return .bluetoothLE
            case .airPlay: return .airPlay
            case .usbAudio: return .usb
            case .HDMI: return .hdmi
            case .lineOut: return .lineOut
            case .carAudio: return .car
            default: return .other
            }
        }
        let now = Date().timeIntervalSince1970 * 1000
        guard now.isFinite, now >= 0, now < Double(Int64.max) else { throw OutputDetailsError.invalidClock }
        return try OutputDetailsSnapshot.capture(buildDetails: installedAppBuildDetails(),
            osVersion: UIDevice.current.systemVersion, portTypes: types,
            totalReported: outputs.count, capturedAtMillis: Int64(now))
    }
}

@MainActor
struct OutputDetailsView: View {
    let theme: AppTheme
    @Environment(\.dismiss) private var dismiss
    @Environment(\.scenePhase) private var scenePhase
    @Environment(\.dynamicTypeSize) private var textSize
    @State private var snapshot: OutputDetailsSnapshot?
    @State private var reviewing = false
    @State private var setupVisible = false
    @StateObject private var setupDraft = TestSetupDraft()
    @State private var status = "Tap Check sound to see which speaker is selected."
    @State private var explanationVisible = false

    var body: some View {
        VStack(spacing: 0) {
            if setupVisible {
                TestSetupView(theme: theme, draft: setupDraft, onClose: { setupVisible = false })
            } else { detailsContent }
        }
        .onChange(of: scenePhase) { if $0 != .active { clear() } }
        .onReceive(NotificationCenter.default.publisher(for: AVAudioSession.routeChangeNotification).receive(on: DispatchQueue.main)) { _ in changed() }
        .onReceive(NotificationCenter.default.publisher(for: AVAudioSession.interruptionNotification).receive(on: DispatchQueue.main)) { _ in changed() }
        .onReceive(NotificationCenter.default.publisher(for: AVAudioSession.mediaServicesWereLostNotification).receive(on: DispatchQueue.main)) { _ in changed() }
        .onReceive(NotificationCenter.default.publisher(for: AVAudioSession.mediaServicesWereResetNotification).receive(on: DispatchQueue.main)) { _ in changed() }
        .onDisappear { clear(); setupDraft.clear() }
    }

    private var detailsContent: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(spacing: 12) {
                Text(reviewing ? "Sound report" : "Sound output")
                    .font(.title2.bold()).fixedSize(horizontal: false, vertical: true)
                    .accessibilityAddTraits(.isHeader).accessibilityIdentifier("output-details-heading")
                Spacer(minLength: 0)
                Button {
                    if reviewing { reviewing = false } else { clear(); dismiss() }
                } label: {
                    Label("Back", systemImage: "chevron.left").fixedSize(horizontal: true, vertical: false)
                }.buttonStyle(AppButtonStyle(theme: theme)).accessibilityIdentifier("output-details-back")
            }
            if reviewing, let report = snapshot {
                ScrollView {
                    VStack(alignment: .leading, spacing: 16) {
                        Button { beginSetup(report) } label: {
                            Text("Add setup notes").frame(maxWidth: .infinity, minHeight: 44)
                                .contentShape(Rectangle())
                        }.buttonStyle(AppButtonStyle(theme: theme)).accessibilityIdentifier("output-details-add-notes")
                        Text(report.text).font(.body).fixedSize(horizontal: false, vertical: true)
                            .frame(maxWidth: .infinity, alignment: .leading).textSelection(.enabled)
                            .accessibilityIdentifier("output-details-preview")
                    }
                }.accessibilityIdentifier("output-details-report-scroll")
                Text(OutputDetailsSnapshot.notice).font(.subheadline).fixedSize(horizontal: false, vertical: true)
                    .accessibilityIdentifier("output-details-notice")
                ReviewedTextShareButton(text: report.text, theme: theme,
                    title: textSize.isAccessibilitySize ? "Share" : "Share output details", identifier: "output-details-share")
                    .accessibilityLabel("Share output details")
            } else {
                ScrollView {
                    VStack(alignment: .leading, spacing: 16) {
                        if let result = snapshot {
                            VStack(alignment: .leading, spacing: 14) {
                                Text(soundSetting(result.connectionGuide))
                                    .font(.title3.bold()).accessibilityAddTraits(.isHeader)
                                    .accessibilityIdentifier("output-connection-guide-title")
                                if result.connectionGuide == .phone || result.connectionGuide == .unavailable {
                                    airPlaySteps
                                } else {
                                    Text(result.connectionGuide.nextStep)
                                        .accessibilityIdentifier("output-connection-guide-next")
                                }
                                Text("TV connection unconfirmed. No TV command sent.")
                                    .font(.subheadline).foregroundColor(theme.muted)
                                    .accessibilityIdentifier("output-connection-boundary")
                            }
                            .padding(16).background(theme.raised)
                            .clipShape(RoundedRectangle(cornerRadius: 16))
                            .overlay(RoundedRectangle(cornerRadius: 16).stroke(theme.outline, lineWidth: 1))
                            .accessibilityElement(children: .contain)
                            .accessibilityIdentifier("output-connection-guide")
                            QuestionDisclosure(title: "About this check", theme: theme,
                                isExpanded: $explanationVisible, identifier: "output-connection-explanation") {
                                VStack(alignment: .leading, spacing: 10) {
                                    Text("This check reads the speaker setting. It does not play a sound or use the microphone. To check that sound reaches the TV, listen at the TV.")
                                    Text(result.summary).font(.subheadline).fixedSize(horizontal: false, vertical: true)
                                        .accessibilityIdentifier("output-details-summary")
                                    Text("Check again after switching speakers or coming back to this app.")
                                        .font(.subheadline).fixedSize(horizontal: false, vertical: true)
                                }
                            }
                            Button { reviewing = true } label: {
                                Text("View sound report").frame(maxWidth: .infinity, minHeight: 44)
                            }.buttonStyle(AppButtonStyle(theme: theme))
                                .accessibilityIdentifier("output-details-review")
                        } else {
                            Text(status).font(.headline)
                                .accessibilityIdentifier("output-details-status")
                        }
                    }.frame(maxWidth: .infinity, alignment: .leading)
                    .fixedSize(horizontal: false, vertical: true)
                    .padding(2)
                }.accessibilityIdentifier("output-details-scroll")
                Button(action: refresh) {
                    Text(snapshot == nil ? "Check sound" : "Check again").frame(maxWidth: .infinity, minHeight: 44)
                }.buttonStyle(AppButtonStyle(theme: theme, primary: true)).accessibilityIdentifier("output-details-refresh")
            }
        }
        .padding(20).frame(maxWidth: 680, maxHeight: .infinity).frame(maxWidth: .infinity, maxHeight: .infinity)
        .foregroundColor(theme.text).accentColor(theme.accent).background(theme.background.ignoresSafeArea())
    }

    private var deviceName: String {
        UIDevice.current.userInterfaceIdiom == .pad ? "iPad" : "iPhone"
    }

    private func soundSetting(_ guide: IOSConnectionGuide) -> String {
        switch guide {
        case .phone: return "Sound is set to this \(deviceName)."
        case .personalAudio: return "Headphones or Bluetooth audio are selected."
        case .homeAudioCandidate: return "AirPlay or HDMI is selected."
        case .externalAudio: return "A cable or accessory is selected."
        case .mixed: return "Check which speaker is selected."
        case .unavailable: return "The speaker setting is unknown."
        }
    }

    private var airPlaySteps: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("To hear your \(deviceName) on your TV").font(.headline)
                .accessibilityIdentifier("output-connection-guide-next")
            Text("1. Swipe down from the top-right corner to open Control Center.")
            if UIDevice.current.userInterfaceIdiom == .phone {
                Text("If your iPhone has a round Home button, swipe up from the bottom instead.")
                    .font(.subheadline)
            }
            Text("2. In the music controls, tap the AirPlay symbol shown below.")
            airPlayPicture
            Text("3. Tap your TV’s name. If you don’t see it, check that your TV supports AirPlay and uses the same Wi-Fi as your \(deviceName).")
            Text("4. Come back here and tap Check sound to see the new setting.")
        }
    }

    // A noninteractive illustration of the music tile, with the audio destination circled.
    private var airPlayPicture: some View {
        VStack(spacing: 12) {
            HStack {
                Image(systemName: "music.note")
                    .frame(width: 40, height: 40).background(theme.raised).cornerRadius(6)
                Spacer()
                Image(systemName: "airplayaudio")
                    .font(.system(size: 30, weight: .semibold)).frame(width: 52, height: 52)
                    .background(Circle().fill(theme.control)).foregroundColor(theme.controlText)
                    .overlay(Circle().stroke(theme.controlBorder, lineWidth: 3))
            }
            HStack(spacing: 22) {
                Image(systemName: "backward.fill")
                Image(systemName: "play.fill")
                Image(systemName: "forward.fill")
            }.font(.system(size: 18))
        }
        .padding(12).frame(maxWidth: 188)
        .background(RoundedRectangle(cornerRadius: 14).fill(theme.surface))
        .overlay(RoundedRectangle(cornerRadius: 14).stroke(theme.outline, lineWidth: 2))
        .accessibilityElement(children: .ignore)
        .accessibilityLabel("Picture of the music controls. The AirPlay symbol is circled at the top right. It looks like a triangle with rings above it.")
        .accessibilityAddTraits(.isImage)
        .accessibilityIdentifier("output-airplay-picture")
    }

    private func beginSetup(_ report: OutputDetailsSnapshot) {
        guard scenePhase == .active, reviewing, snapshot == report, !setupVisible else { return }
        setupDraft.clear(); setupDraft.outputDetails = report; setupVisible = true
    }

    private func clear() {
        snapshot = nil; reviewing = false; explanationVisible = false
        status = "Tap Check sound to see which speaker is selected."
    }
    private func changed() {
        clear(); status = "The speaker setting may have changed. Tap Check sound."
    }
    private func refresh() {
        guard scenePhase == .active else { return }
        clear()
        guard ForegroundMicrophoneGate.shared.available else {
            status = ForegroundMicrophoneGate.shared.blocked ? "Close Audio Bodyguard, then open it again to check the speaker." :
                "Stop the sound or voice check, then tap Check sound."
            return
        }
        do { snapshot = try SessionOutputReader.capture() }
        catch { status = "The speaker setting could not be read. Check the date on this device, then tap Check sound." }
    }
}
