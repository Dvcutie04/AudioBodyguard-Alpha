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
            case .USBAudio: return .usb
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
    @State private var status = "Ready to read output details"

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(spacing: 12) {
                Text(reviewing ? "Review output details" : "Output details")
                    .font(.title2.bold()).fixedSize(horizontal: false, vertical: true)
                    .accessibilityAddTraits(.isHeader).accessibilityIdentifier("output-details-heading")
                Spacer(minLength: 0)
                RoseButton(title: "Back", theme: theme, compact: true) {
                    if reviewing { reviewing = false } else { clear(); dismiss() }
                }.accessibilityIdentifier("output-details-back")
            }
            if reviewing, let report = snapshot {
                ScrollView {
                    Text(report.text).font(.body).fixedSize(horizontal: false, vertical: true)
                        .frame(maxWidth: .infinity, alignment: .leading).textSelection(.enabled)
                        .accessibilityIdentifier("output-details-preview")
                }.accessibilityIdentifier("output-details-report-scroll")
                Text(OutputDetailsSnapshot.notice).font(.subheadline).fixedSize(horizontal: false, vertical: true)
                    .accessibilityIdentifier("output-details-notice")
                ReviewedTextShareButton(text: report.text, theme: theme,
                    title: textSize.isAccessibilitySize ? "Share details" : "Share output details", identifier: "output-details-share")
                    .accessibilityLabel("Share output details")
            } else {
                ScrollView {
                    VStack(alignment: .leading, spacing: 16) {
                        Text("Read the output port types iOS reports for this app’s audio session.")
                            .fixedSize(horizontal: false, vertical: true)
                        Text("This plays no sound and uses no microphone. It does not switch outputs or show every available device.")
                            .font(.subheadline).fixedSize(horizontal: false, vertical: true)
                        Text(status).font(.headline).fixedSize(horizontal: false, vertical: true)
                            .accessibilityIdentifier("output-details-status")
                        if let result = snapshot {
                            Text(result.summary).fixedSize(horizontal: false, vertical: true)
                                .accessibilityIdentifier("output-details-summary")
                        }
                        Text("Actual playback route: Unknown\nNegotiated format: Unknown")
                            .fixedSize(horizontal: false, vertical: true)
                        Text("Details clear after an output-change notice, when you leave the app, or when you close this screen. Tap Refresh details for a new snapshot.")
                            .font(.subheadline).fixedSize(horizontal: false, vertical: true)
                        Text(OutputDetailsSnapshot.notice).foregroundColor(theme.warning)
                            .fixedSize(horizontal: false, vertical: true)
                    }.frame(maxWidth: .infinity, alignment: .leading)
                }.accessibilityIdentifier("output-details-scroll")
                Button { reviewing = snapshot != nil } label: {
                    Text("Review output details").frame(maxWidth: .infinity, minHeight: 44)
                }.buttonStyle(AppButtonStyle(theme: theme)).disabled(snapshot == nil)
                    .accessibilityIdentifier("output-details-review")
                Button(action: refresh) {
                    Text("Refresh details").frame(maxWidth: .infinity, minHeight: 44)
                }.buttonStyle(AppButtonStyle(theme: theme, primary: true)).accessibilityIdentifier("output-details-refresh")
            }
        }
        .padding(20).frame(maxWidth: 680, maxHeight: .infinity).frame(maxWidth: .infinity, maxHeight: .infinity)
        .foregroundColor(theme.text).accentColor(theme.accent).background(theme.background.ignoresSafeArea())
        .onChange(of: scenePhase) { if $0 != .active { clear() } }
        .onReceive(NotificationCenter.default.publisher(for: AVAudioSession.routeChangeNotification).receive(on: DispatchQueue.main)) { _ in changed() }
        .onReceive(NotificationCenter.default.publisher(for: AVAudioSession.interruptionNotification).receive(on: DispatchQueue.main)) { _ in changed() }
        .onReceive(NotificationCenter.default.publisher(for: AVAudioSession.mediaServicesWereLostNotification).receive(on: DispatchQueue.main)) { _ in changed() }
        .onReceive(NotificationCenter.default.publisher(for: AVAudioSession.mediaServicesWereResetNotification).receive(on: DispatchQueue.main)) { _ in changed() }
        .onDisappear { clear() }
    }

    private func clear() { snapshot = nil; reviewing = false; status = "Ready to read output details" }
    private func changed() {
        clear(); status = "Output details may have changed. Tap Refresh details."
    }
    private func refresh() {
        guard scenePhase == .active else { return }
        clear()
        guard ForegroundMicrophoneGate.shared.available else {
            status = ForegroundMicrophoneGate.shared.blocked ? "Audio cleanup is unresolved. Close this app before trying again." :
                "Stop the sound or voice check before refreshing these details."
            return
        }
        do { snapshot = try SessionOutputReader.capture(); status = "Details captured. Review the snapshot before sharing." }
        catch { status = "Output details are unavailable. Check this phone’s date, then try Refresh details." }
    }
}
