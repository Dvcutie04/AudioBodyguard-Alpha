import SwiftUI
import Network
import UIKit

/// One foreground TCP handshake at a time. No bytes, TLS exceptions, TV commands,
/// discovery, credentials or automatic restarts. Retain ownership until cancelled.
@MainActor
final class TVNetworkCheck: ObservableObject {
    private static var owner: TVNetworkCheck?
    @Published var address = ""
    @Published private(set) var busy = false
    @Published private(set) var stopping = false
    @Published private(set) var message = "Ready to check the address you enter."
    private var target: AQSSLocalTVTarget?
    private var connection: NWConnection?
    private var timeout: DispatchWorkItem?
    private var portIndex = 0
    private var stopped = false
    private var showResult = true
    private var nextPort = false
    private var pendingMessage = ""

    func start() {
        guard !busy else { return }
        guard let target = AQSSLocalTVTarget(address) else {
            message = AQSSLocalTVTarget.invalidAddress; return
        }
        guard Self.owner == nil else {
            message = "A previous network check is still closing. Try again after it finishes."; return
        }
        Self.owner = self
        self.target = target
        portIndex = 0; stopped = false; showResult = true; busy = true; stopping = false
        attempt()
    }

    func stop(clear: Bool = false) {
        if clear { address = ""; message = "Ready to check the address you enter."; showResult = false }
        guard busy else { return }
        stopped = true; stopping = true; nextPort = false
        pendingMessage = "Check stopped. Start again only when you are ready."
        timeout?.cancel(); timeout = nil
        if !clear { message = "Stopping the network check…" }
        connection?.cancel()
    }

    private func attempt() {
        guard !stopped, let target = target, portIndex < AQSSLocalTVTarget.ports.count else {
            finish("Check stopped."); return
        }
        let port = AQSSLocalTVTarget.ports[portIndex]
        let parameters = NWParameters.tcp
        parameters.requiredInterfaceType = .wifi
        let current = NWConnection(host: NWEndpoint.Host(target.address),
            port: NWEndpoint.Port(rawValue: port)!, using: parameters)
        connection = current
        nextPort = false; pendingMessage = "The check ended without a verified result."
        message = "Checking the address you entered…"
        current.stateUpdateHandler = { [weak self, weak current] state in
            guard let self = self, let current = current, self.connection === current else { return }
            switch state {
            case .ready:
                guard !self.stopping else { return }
                self.closeAttempt("A network service answered. TV pairing is still needed.", fallback: false)
            case .failed, .waiting:
                guard !self.stopping else { return }
                self.closeAttempt("Could not reach the service. Check home Wi-Fi and TV power, then try again.", fallback: true)
            case .cancelled:
                self.timeout?.cancel(); self.timeout = nil
                current.stateUpdateHandler = nil
                self.connection = nil
                if self.nextPort && !self.stopped && self.portIndex + 1 < AQSSLocalTVTarget.ports.count {
                    self.portIndex += 1; self.stopping = false; self.attempt()
                } else { self.finish(self.pendingMessage) }
            default: break
            }
        }
        let deadline = DispatchWorkItem { [weak self, weak current] in
            guard let self = self, let current = current, self.connection === current, !self.stopping else { return }
            self.closeAttempt("Could not reach the service. Check home Wi-Fi and TV power, then try again.", fallback: true)
        }
        timeout = deadline
        current.start(queue: .main)
        DispatchQueue.main.asyncAfter(deadline: .now() + .seconds(AQSSLocalTVTarget.timeoutSeconds), execute: deadline)
    }

    private func closeAttempt(_ result: String, fallback: Bool) {
        stopping = true; nextPort = fallback && !stopped; pendingMessage = result
        timeout?.cancel(); timeout = nil
        connection?.cancel()
    }

    private func finish(_ result: String) {
        timeout?.cancel(); timeout = nil; target = nil
        if showResult { message = result }
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

    var body: some View {
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
                        UIApplication.shared.sendAction(#selector(UIResponder.resignFirstResponder), to: nil, from: nil, for: nil)
                        if check.busy { check.stop() } else { check.start() }
                    }.buttonStyle(AppButtonStyle(theme: theme, primary: true))
                        .disabled(check.stopping || (!check.busy && check.address.isEmpty))
                        .accessibilityIdentifier("tv-network-start-stop")
                    QuestionDisclosure(title: "Help with this check", theme: theme, isExpanded: $help, identifier: "tv-network-help") {
                        Text("Use the same home Wi-Fi for phone and TV. Guest Wi-Fi or device isolation can prevent contact. This check cannot diagnose your router’s policy.")
                        Text("This first check tries TCP ports 7345 and 9000, for up to four seconds each, on one private IPv4 address. These are SmartCast research candidates, not a guarantee for every VIZIO model. An answer proves only service reachability at that moment.")
                        Text("Allow Local Network access if iPhone asks. After changing permission, tap Check again. Leaving this screen or the foreground clears the address and result and stops the check.")
                        Button("Open this app’s settings") {
                            guard let url = URL(string: UIApplication.openSettingsURLString) else { return }
                            UIApplication.shared.open(url)
                        }.buttonStyle(AppButtonStyle(theme: theme))
                    }
                }.padding().frame(maxWidth: 680, alignment: .leading).frame(maxWidth: .infinity)
            }.accessibilityIdentifier("tv-network-scroll")
        }.background(theme.background.ignoresSafeArea()).foregroundColor(theme.text)
            .onChange(of: scenePhase) { phase in if phase != .active { check.stop(clear: true) } }
            .onDisappear { check.stop(clear: true) }
    }
}
