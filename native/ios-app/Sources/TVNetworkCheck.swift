import SwiftUI
import Network
import UIKit

/// One foreground TCP handshake at a time. No bytes, TLS exceptions, TV commands,
/// discovery, credentials or automatic restarts. Retain ownership until cancelled.
@MainActor
final class TVNetworkCheck: ObservableObject {
    private static var owner: TVNetworkCheck?
    @Published var address = "" {
        didSet {
            if !busy && address != oldValue {
                lastOutcome = nil
                message = "Ready to check the address you enter."
            }
        }
    }
    @Published private(set) var busy = false
    @Published private(set) var stopping = false
    @Published private(set) var message = "Ready to check the address you enter."
    @Published private(set) var lastOutcome: TVTrialOutcome?
    private var target: AQSSLocalTVTarget?
    private var connection: NWConnection?
    private var timeout: DispatchWorkItem?
    private var portIndex = 0
    private var stopped = false
    private var showResult = true
    private var nextPort = false
    private var pendingMessage = ""
    private var pendingOutcome: TVTrialOutcome = .noResponse

    func start() {
        guard !busy else { return }
        lastOutcome = nil
        guard let target = AQSSLocalTVTarget(address) else {
            message = AQSSLocalTVTarget.invalidAddress; lastOutcome = .addressRejected; return
        }
        guard Self.owner == nil else {
            message = "A previous network check is still closing. Try again after it finishes."; lastOutcome = .unavailable; return
        }
        Self.owner = self
        self.target = target
        portIndex = 0; stopped = false; showResult = true; busy = true; stopping = false
        attempt()
    }

    func stop(clear: Bool = false) {
        if clear { address = ""; message = "Ready to check the address you enter."; lastOutcome = nil; showResult = false }
        guard busy else { return }
        stopped = true; stopping = true; nextPort = false
        pendingMessage = "Check stopped. Start again only when you are ready."
        pendingOutcome = .stopped
        timeout?.cancel(); timeout = nil
        if !clear { message = "Stopping the network check…" }
        connection?.cancel()
    }

    private func attempt() {
        guard !stopped, let target = target, portIndex < AQSSLocalTVTarget.ports.count else {
            finish("Check stopped.", outcome: .stopped); return
        }
        let port = AQSSLocalTVTarget.ports[portIndex]
        let parameters = NWParameters.tcp
        parameters.requiredInterfaceType = .wifi
        let current = NWConnection(host: NWEndpoint.Host(target.address),
            port: NWEndpoint.Port(rawValue: port)!, using: parameters)
        connection = current
        nextPort = false; pendingMessage = "The check ended without a verified result."; pendingOutcome = .noResponse
        message = "Checking the address you entered…"
        current.stateUpdateHandler = { [weak self, weak current] state in
            // Network's callback is Sendable even when its queue is .main.
            // Enter the main actor explicitly before touching the run owner.
            DispatchQueue.main.async { [weak self, weak current] in
                guard let self = self, let current = current, self.connection === current else { return }
                switch state {
                case .ready:
                    guard !self.stopping else { return }
                    self.closeAttempt("A network service answered. TV pairing is still needed.", outcome: .serviceAnswered, fallback: false)
                case .failed, .waiting:
                    guard !self.stopping else { return }
                    self.closeAttempt("Could not reach the service. Check home Wi-Fi and TV power, then try again.", outcome: .noResponse, fallback: true)
                case .cancelled:
                    self.timeout?.cancel(); self.timeout = nil
                    current.stateUpdateHandler = nil
                    self.connection = nil
                    if self.nextPort && !self.stopped && self.portIndex + 1 < AQSSLocalTVTarget.ports.count {
                        self.portIndex += 1; self.stopping = false; self.attempt()
                    } else { self.finish(self.pendingMessage, outcome: self.pendingOutcome) }
                default: break
                }
            }
        }
        let deadline = DispatchWorkItem { [weak self, weak current] in
            guard let self = self, let current = current, self.connection === current, !self.stopping else { return }
            self.closeAttempt("Could not reach the service. Check home Wi-Fi and TV power, then try again.", outcome: .noResponse, fallback: true)
        }
        timeout = deadline
        current.start(queue: .main)
        DispatchQueue.main.asyncAfter(deadline: .now() + .seconds(AQSSLocalTVTarget.timeoutSeconds), execute: deadline)
    }

    private func closeAttempt(_ result: String, outcome: TVTrialOutcome, fallback: Bool) {
        stopping = true; nextPort = fallback && !stopped; pendingMessage = result
        pendingOutcome = outcome
        timeout?.cancel(); timeout = nil
        connection?.cancel()
    }

    private func finish(_ result: String, outcome: TVTrialOutcome) {
        timeout?.cancel(); timeout = nil; target = nil
        if showResult { message = result; lastOutcome = outcome }
        busy = false; stopping = false
        if Self.owner === self { Self.owner = nil }
    }
}

struct TVNetworkCheckView: View {
    let theme: AppTheme
    @Environment(\.dismiss) private var dismiss
    @Environment(\.scenePhase) private var scenePhase
    @StateObject private var check = TVNetworkCheck()
    @State private var help = false
    @State private var reviewedReport: TVTrialReport?
    @State private var reportError: String?

    var body: some View {
        Group {
            if let report = reviewedReport { reviewContent(report) } else { checkContent }
        }
        .onChange(of: scenePhase) { phase in if phase != .active { check.stop(clear: true) } }
        .onDisappear { check.stop(clear: true) }
    }

    private var checkContent: some View {
        VStack(spacing: 0) {
            HStack {
                Text("VIZIO network check").font(.title2.bold()).fixedSize(horizontal: false, vertical: true)
                Spacer()
                Button("Back") { check.stop(clear: true); dismiss() }
                    .buttonStyle(AppButtonStyle(theme: theme)).accessibilityIdentifier("tv-network-back")
            }.padding()
            ScrollView {
                VStack(alignment: .leading, spacing: 18) {
                    Label("Phone → Wi-Fi → TV", systemImage: "wifi").font(.headline)
                    Text("Enter the IP address shown in your VIZIO TV’s network settings.")
                    TextField("TV IP address", text: $check.address)
                        .keyboardType(.numbersAndPunctuation).autocapitalization(.none).disableAutocorrection(true)
                        .padding(12).background(theme.raised).cornerRadius(12)
                        .disabled(check.busy).accessibilityLabel("TV IP address").accessibilityIdentifier("tv-network-address")
                    Text("Check contacts only this address on Wi-Fi. It sends no TV command.").font(.subheadline)
                    Text(check.message).font(.headline).fixedSize(horizontal: false, vertical: true)
                        .accessibilityIdentifier("tv-network-result")
                    Text(AQSSLocalTVTarget.boundary).font(.subheadline).foregroundColor(theme.muted)
                        .accessibilityIdentifier("tv-network-boundary")
                    Button(check.busy ? "Stop check" : "Check this address") {
                        reportError = nil
                        UIApplication.shared.sendAction(#selector(UIResponder.resignFirstResponder), to: nil, from: nil, for: nil)
                        if check.busy { check.stop() } else { check.start() }
                    }.buttonStyle(AppButtonStyle(theme: theme, primary: true))
                        .disabled(check.stopping || (!check.busy && check.address.isEmpty))
                        .accessibilityIdentifier("tv-network-start-stop")
                    if check.lastOutcome != nil && !check.busy {
                        Button("Review test result", action: reviewResult)
                            .buttonStyle(AppButtonStyle(theme: theme)).accessibilityIdentifier("tv-network-review")
                    }
                    if let error = reportError { Text(error).font(.subheadline) }
                    QuestionDisclosure(title: "Help with this check", theme: theme, isExpanded: $help, identifier: "tv-network-help") {
                        Text("Use the same home Wi-Fi for phone and TV. Guest Wi-Fi or device isolation can prevent contact. This check cannot diagnose your router’s policy.")
                        Text("This first check tries TCP ports 7345 and 9000, for up to four seconds each, on one private IPv4 address. These are SmartCast research candidates, not a guarantee for every VIZIO model. An answer proves only service reachability at that moment.")
                        Text("Allow Local Network access if iPhone asks. After changing permission, tap Check again. Leaving this screen or the foreground clears the address and result and stops the check.")
                        Text("Review test result removes the address and opens a historical copy. You can then choose Share. The report contains the app build and a fixed result description, without TV addresses, Wi-Fi names, passwords, photos or audio. Nothing is sent automatically.")
                        Button("Open this app’s settings") {
                            guard let url = URL(string: UIApplication.openSettingsURLString) else { return }
                            UIApplication.shared.open(url)
                        }.buttonStyle(AppButtonStyle(theme: theme))
                    }
                }.padding().frame(maxWidth: 680, alignment: .leading).frame(maxWidth: .infinity)
            }.accessibilityIdentifier("tv-network-scroll")
        }.background(theme.background.ignoresSafeArea()).foregroundColor(theme.text)
    }

    private func reviewResult() {
        guard scenePhase == .active, !check.busy, let outcome = check.lastOutcome else { return }
        let millis = Date().timeIntervalSince1970 * 1000
        guard millis.isFinite, millis >= 0, millis <= 253_402_300_799_999 else {
            reportError = "The phone clock is unavailable. No report was prepared."; return
        }
        do {
            let frozen = try TVTrialReport.capture(buildDetails: installedAppBuildDetails(), outcome: outcome,
                reviewedAtMillis: Int64(millis))
            check.stop(clear: true); reportError = nil; reviewedReport = frozen
        } catch { reportError = "The installed build or phone clock could not be included. No report was prepared." }
    }

    private func reviewContent(_ report: TVTrialReport) -> some View {
        VStack(spacing: 16) {
            HStack {
                Text("Review test result").font(.title2.bold()).fixedSize(horizontal: false, vertical: true)
                Spacer()
                Button("Back") { reviewedReport = nil }
                    .buttonStyle(AppButtonStyle(theme: theme)).accessibilityIdentifier("tv-network-report-back")
            }
            ScrollView {
                Text(report.text).frame(maxWidth: .infinity, alignment: .leading)
                    .fixedSize(horizontal: false, vertical: true).textSelection(.enabled)
                    .accessibilityIdentifier("tv-network-report-preview")
            }.accessibilityIdentifier("tv-network-report-scroll")
            Text(TVTrialReport.notice).font(.subheadline).fixedSize(horizontal: false, vertical: true)
            ReviewedTextShareButton(text: report.text, theme: theme, title: "Share test result", identifier: "tv-network-report-share")
        }.padding(20).foregroundColor(theme.text).background(theme.background.ignoresSafeArea())
    }
}
