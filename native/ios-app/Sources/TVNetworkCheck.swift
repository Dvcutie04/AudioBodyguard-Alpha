import SwiftUI
import Network
import UIKit

/// One foreground diagnostic at a time. A certificate read always rejects TLS.
/// Retain ownership until the connection reports cancellation.
@MainActor
final class TVNetworkCheck: ObservableObject {
    private struct ReachedService {
        let target: AQSSLocalTVTarget
        let port: NWEndpoint.Port
        let interface: NWInterface
        let localHost: NWEndpoint.Host

        init?(target: AQSSLocalTVTarget, port: NWEndpoint.Port, path: NWPath?) {
            guard let path = path, path.status == .satisfied, path.usesInterfaceType(.wifi),
                  case .hostPort(let host, _)? = path.localEndpoint else { return nil }
            let wifi = path.availableInterfaces.filter { $0.type == .wifi }
            guard wifi.count == 1, let interface = wifi.first else { return nil }
            self.target = target
            self.port = port
            self.interface = interface
            localHost = host
        }

        func makeCertificateConnection(options: NWProtocolTLS.Options) -> NWConnection {
            let parameters = NWParameters(tls: options)
            parameters.requiredInterface = interface
            parameters.requiredLocalEndpoint = .hostPort(host: localHost, port: .any)
            return NWConnection(host: NWEndpoint.Host(target.address), port: port, using: parameters)
        }
    }

    private static var owner: TVNetworkCheck?
    @Published var address = "" {
        didSet {
            if !busy && address != oldValue {
                clearCertificate()
                lastOutcome = nil
                message = "Ready to check the address you enter."
            }
        }
    }
    @Published private(set) var busy = false
    @Published private(set) var stopping = false
    @Published private(set) var message = "Ready to check the address you enter."
    @Published private(set) var lastOutcome: TVTrialOutcome?
    @Published private(set) var fingerprint: String?
    private var reachedService: ReachedService?
    private var certificateObserver: AQSSPeerCertificateObserver?
    private var certificateRead: AQSSCertificateRead?
    private var target: AQSSLocalTVTarget?
    private var connection: NWConnection?
    private var timeout: DispatchWorkItem?
    private var portIndex = 0
    private var stopped = false
    private var showResult = true
    private var nextPort = false
    private var pendingMessage = ""
    private var pendingOutcome: TVTrialOutcome?

    var canReadCertificate: Bool {
        guard !busy, lastOutcome == .serviceAnswered, let service = reachedService else { return false }
        return AQSSLocalTVTarget(address) == service.target
    }

    func start() {
        guard !busy else { return }
        clearCertificate()
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

    func readCertificate() {
        guard canReadCertificate, let service = reachedService else { return }
        guard Self.owner == nil else {
            message = "A previous network check is still closing. Try again after it finishes."; return
        }
        Self.owner = self
        let observer = AQSSPeerCertificateObserver()
        certificateObserver = observer
        let read = AQSSCertificateRead(startedAt: .now())
        certificateRead = read
        fingerprint = nil
        stopped = false; showResult = true; busy = true; stopping = false; nextPort = false
        pendingMessage = AQSSCertificateRead.Result.noCertificate.message; pendingOutcome = nil
        message = "Reading the certificate from the service that answered…"
        let options = observer.makeTLSOptions { [weak self, weak observer] in
            DispatchQueue.main.async { [weak self, weak observer] in
                guard let self = self, let observer = observer, self.certificateObserver === observer,
                      !self.stopping else { return }
                self.closeCertificateAttempt(observer.fingerprint)
            }
        }
        begin(service.makeCertificateConnection(options: options), expires: read.expires)
    }

    func stop(clear: Bool = false) {
        if clear {
            clearCertificate()
            address = ""; message = "Ready to check the address you enter."; lastOutcome = nil; showResult = false
        }
        guard busy else { return }
        stopped = true; nextPort = false
        if certificateRead != nil {
            certificateRead?.stop(clear: clear)
        } else {
            reachedService = nil
            pendingMessage = "Check stopped. Start again only when you are ready."
            pendingOutcome = .stopped
        }
        cancelConnection()
        if !clear { message = "Stopping the network check…" }
    }

    private func attempt() {
        guard !stopped, let target = target, portIndex < AQSSLocalTVTarget.ports.count else {
            finish("Check stopped.", outcome: .stopped); return
        }
        let port = NWEndpoint.Port(rawValue: AQSSLocalTVTarget.ports[portIndex])!
        let parameters = NWParameters.tcp
        parameters.requiredInterfaceType = .wifi
        nextPort = false; pendingMessage = "The check ended without a verified result."; pendingOutcome = .noResponse
        message = "Checking the address you entered…"
        begin(NWConnection(host: NWEndpoint.Host(target.address), port: port, using: parameters))
    }

    private func begin(_ current: NWConnection,
                       expires: DispatchTime = .now() + .seconds(AQSSLocalTVTarget.timeoutSeconds)) {
        connection = current
        current.stateUpdateHandler = { [weak self, weak current] state in
            // Network's callback is Sendable even when its queue is .main.
            // Enter the main actor explicitly before touching the run owner.
            DispatchQueue.main.async { [weak self, weak current] in
                guard let self = self, let current = current, self.connection === current else { return }
                switch state {
                case .ready, .failed, .waiting:
                    guard !self.stopping else { return }
                    guard DispatchTime.now() < expires else { self.expireAttempt(); return }
                    self.handleResult(state, from: current)
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
            self.expireAttempt()
        }
        timeout = deadline
        current.start(queue: .main)
        DispatchQueue.main.asyncAfter(deadline: expires, execute: deadline)
    }

    private func handleResult(_ state: NWConnection.State, from current: NWConnection) {
        if let observer = certificateObserver {
            if case .ready = state { closeCertificateAttempt(nil) }
            else { closeCertificateAttempt(observer.fingerprint) }
        } else if case .ready = state, let target = target,
                  case .hostPort(_, let port) = current.endpoint {
            reachedService = ReachedService(target: target, port: port, path: current.currentPath)
            closeAttempt("A network service answered. TV pairing is still needed.", outcome: .serviceAnswered, fallback: false)
        } else {
            closeAttempt("No service answered. The reason is unknown.", outcome: .noResponse, fallback: true)
        }
    }

    private func closeCertificateAttempt(_ observed: String?, at instant: DispatchTime = .now()) {
        guard certificateRead?.resolve(observed, at: instant) == true else { return }
        cancelConnection()
    }

    private func expireAttempt() {
        if let expires = certificateRead?.expires {
            closeCertificateAttempt(nil, at: expires)
        } else {
            closeAttempt("No service answered. The reason is unknown.", outcome: .noResponse, fallback: true)
        }
    }

    private func closeAttempt(_ result: String, outcome: TVTrialOutcome?, fallback: Bool) {
        nextPort = fallback && !stopped; pendingMessage = result
        pendingOutcome = outcome
        cancelConnection()
    }

    private func cancelConnection() {
        stopping = true
        timeout?.cancel(); timeout = nil
        connection?.cancel()
    }

    private func finish(_ result: String, outcome: TVTrialOutcome?) {
        timeout?.cancel(); timeout = nil; target = nil
        let certificateResult = certificateRead?.finishCancellation()
        if showResult {
            message = certificateResult?.message ?? result
            if let outcome = outcome { lastOutcome = outcome }
            fingerprint = certificateResult?.fingerprint
        }
        certificateObserver = nil; certificateRead = nil
        busy = false; stopping = false
        if Self.owner === self { Self.owner = nil }
    }

    private func clearCertificate() {
        reachedService = nil; fingerprint = nil
    }
}

struct TVNetworkCheckView: View {
    let theme: AppTheme
    var takePhotoTarget: (() -> AQSSLocalTVTarget?)? = nil
    @Environment(\.dismiss) private var dismiss
    @Environment(\.scenePhase) private var scenePhase
    @StateObject private var check = TVNetworkCheck()
    @State private var help = false
    @State private var guideContext: TVCheckPictureGuide.Context?
    @State private var reviewedReport: TVTrialReport?
    @State private var reportError: String?

    var body: some View {
        VStack(spacing: 0) {
            if let guideContext = guideContext {
                TVCheckPictureGuide(theme: theme, context: guideContext) { self.guideContext = nil }
            } else if let report = reviewedReport {
                reviewContent(report)
            } else {
                checkContent
            }
        }
        .onAppear {
            if let target = takePhotoTarget?(), scenePhase == .active { check.address = target.address }
        }
        .onChange(of: scenePhase) { phase in if phase != .active { check.stop(clear: true) } }
        .onDisappear { check.stop(clear: true) }
    }

    private var checkContent: some View {
        let followUp = check.lastOutcome?.followUp
        return VStack(spacing: 0) {
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
                    if let route = TVCheckPictureGuide.Context.addressField.route {
                        Button(route.title) { openGuide(.addressField) }
                            .buttonStyle(AppButtonStyle(theme: theme, primary: followUp == .addressPictures))
                            .disabled(check.busy).accessibilityIdentifier("tv-address-guide-open")
                    }
                    Text("Check contacts only this address on Wi-Fi. It sends no TV command.").font(.subheadline)
                    Text(check.message).font(.headline).fixedSize(horizontal: false, vertical: true)
                        .accessibilityIdentifier("tv-network-result")
                    Text(AQSSLocalTVTarget.boundary).font(.subheadline).foregroundColor(theme.muted)
                        .accessibilityIdentifier("tv-network-boundary")
                    Button(check.busy ? "Stop check" : "Check this address") {
                        guard scenePhase == .active else { return }
                        reportError = nil
                        UIApplication.shared.sendAction(#selector(UIResponder.resignFirstResponder), to: nil, from: nil, for: nil)
                        if check.busy { check.stop() } else { check.start() }
                    }.buttonStyle(AppButtonStyle(theme: theme, primary: followUp == nil))
                        .disabled(check.stopping || (!check.busy && check.address.isEmpty))
                        .accessibilityIdentifier("tv-network-start-stop")
                    if check.canReadCertificate {
                        Button("Read service certificate") {
                            guard scenePhase == .active else { return }
                            reportError = nil
                            check.readCertificate()
                        }.buttonStyle(AppButtonStyle(theme: theme, primary: check.fingerprint == nil))
                            .accessibilityIdentifier("tv-network-certificate-read")
                    }
                    if let fingerprint = check.fingerprint {
                        Text("SHA-256 fingerprint\n\(fingerprint)")
                            .font(.system(.footnote, design: .monospaced)).textSelection(.enabled)
                            .fixedSize(horizontal: false, vertical: true)
                            .accessibilityIdentifier("tv-network-certificate-fingerprint")
                    }
                    if followUp == .phoneWiFi {
                        Text("Check that this device and your TV use the same home Wi-Fi.").fixedSize(horizontal: false, vertical: true)
                        phoneWiFiButton(primary: true)
                    }
                    if check.lastOutcome != nil && !check.busy {
                        Button("Review test result", action: reviewResult)
                            .buttonStyle(AppButtonStyle(theme: theme,
                                primary: followUp == .review && (!check.canReadCertificate || check.fingerprint != nil)))
                            .accessibilityIdentifier("tv-network-review")
                    }
                    if let error = reportError { Text(error).font(.subheadline) }
                    QuestionDisclosure(title: "Help with this check", theme: theme, isExpanded: $help, identifier: "tv-network-help") {
                        Text("Use the same home Wi-Fi for phone and TV. Guest Wi-Fi or device isolation can prevent contact. This check cannot diagnose your router’s policy.")
                        if followUp != .phoneWiFi { phoneWiFiButton(primary: false) }
                        Text("This first check tries TCP ports 7345 and 9000, for up to four seconds each, on one private IPv4 address. These are SmartCast research candidates, not a guarantee for every VIZIO model. An answer proves only service reachability at that moment.")
                        Text("After a reply, Read service certificate checks that service again on Wi-Fi and shows a fingerprint for comparison. TV identity still needs independent verification.")
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

    private func openGuide(_ context: TVCheckPictureGuide.Context) {
        guard !check.busy else { return }
        UIApplication.shared.sendAction(#selector(UIResponder.resignFirstResponder), to: nil, from: nil, for: nil)
        guideContext = context
    }

    private func phoneWiFiButton(primary: Bool) -> some View {
        Button(UIDevice.current.userInterfaceIdiom == .pad ? "Check iPad Wi-Fi" : "Check phone Wi-Fi") { openGuide(.phoneWiFi) }
            .buttonStyle(AppButtonStyle(theme: theme, primary: primary))
            .disabled(check.busy).accessibilityIdentifier("tv-network-wifi-guide-open")
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

/// Local guide that returns to its caller with the current form still in memory.
struct TVCheckPictureGuide: View {
    enum Context: Equatable {
        case addressField, photoSetup, phoneWiFi

        @MainActor var route: AQSSSetupRoute? {
            let id: String
            if self == .phoneWiFi {
                id = UIDevice.current.userInterfaceIdiom == .pad ? "phone_ipad" : "phone_iphone"
            } else { id = "vizio_v505m_k09_address" }
            return AQSSSetupContent.routes.first { $0.id == id }
        }
    }

    let theme: AppTheme
    let context: Context
    let onReturn: () -> Void
    @State private var index = -1
    @State private var mismatch = false
    @AccessibilityFocusState private var focusedHeading: String?

    private var route: AQSSSetupRoute? { context.route }
    private var isWiFi: Bool { context == .phoneWiFi }
    private var isPad: Bool { UIDevice.current.userInterfaceIdiom == .pad }
    private var steps: [AQSSSetupStep] {
        let all = route?.steps ?? []
        if context == .photoSetup || (context == .addressField && isPad) {
            // On iPad the last TV picture returns directly to the address field.
            return all.filter { $0.surface == "tv" }
        }
        return all
    }
    private var step: AQSSSetupStep? { steps.indices.contains(index) ? steps[index] : nil }
    private var screenKey: String { "\(index)-\(mismatch)" }
    private var returnsToCaller: Bool { mismatch || index == steps.count - 1 }
    private var helpTitle: String { isWiFi ? "Wi-Fi help" : "TV address help" }
    private var prefix: String { isWiFi ? "tv-wifi-guide" : "tv-address-guide" }
    private var returnTitle: String {
        switch context {
        case .addressField: return "Back to address field"
        case .photoSetup: return "Back to photo setup"
        case .phoneWiFi: return "Back to network check"
        }
    }

    var body: some View {
        VStack(spacing: 0) {
            HStack {
                Text(index >= 0 && !mismatch ? "Step \(index + 1) of \(steps.count)" : helpTitle)
                    .font(.headline).fixedSize(horizontal: false, vertical: true).layoutPriority(1)
                Spacer(minLength: 8)
                Button("Back", action: back).buttonStyle(AppButtonStyle(theme: theme))
                    .accessibilityIdentifier(prefix + "-back")
            }.padding(16).background(theme.surface)
            GuideScrollView(screenKey: screenKey, identifier: prefix + "-scroll", onStepReady: { focusedHeading = $0 }) {
                VStack(alignment: .leading, spacing: 18) {
                    if !isWiFi, let route = route {
                        let device = isPad ? "iPad" : "iPhone"
                        Text("VIZIO \(route.models.joined(separator: ", ")) · \(device)").font(.subheadline.weight(.semibold))
                            .foregroundColor(theme.muted).accessibilityIdentifier(prefix + "-model")
                    }
                    Text(mismatch ? "Find the right screen" : step?.title ?? route?.title ?? "Connect to your home Wi-Fi")
                        .font(.title.bold()).fixedSize(horizontal: false, vertical: true)
                        .accessibilityAddTraits(.isHeader).accessibilityFocused($focusedHeading, equals: screenKey)
                    if mismatch {
                        Text(isWiFi ? "Search for Wi-Fi in Settings." : "Look up the network information for your exact TV model in VIZIO Support.")
                    } else {
                        if let step = step {
                            Text(step.instruction).font(.body.weight(.medium)).fixedSize(horizontal: false, vertical: true)
                            GuidePictureCue(screenKey: screenKey) {
                                if step.pictureKind == "remote" {
                                    RemoteButtonsIllustration(step: step, number: index + 1, theme: theme)
                                } else {
                                    SetupScreenIllustration(step: step, number: index + 1, theme: theme)
                                }
                            }
                        } else if let route = route {
                            Text(route.appliesTo)
                        } else {
                            Text("1. Open Settings.")
                            Text("2. Tap Wi-Fi.")
                            Text("3. Choose the home network your TV uses.")
                        }
                        if route != nil {
                            Button("My screen looks different") { mismatch = true }
                                .buttonStyle(AppButtonStyle(theme: theme)).accessibilityIdentifier(prefix + "-mismatch")
                        }
                    }
                }.frame(maxWidth: 620, alignment: .leading).padding(20).frame(maxWidth: .infinity)
            }
            Button {
                if returnsToCaller { onReturn() } else { index += 1 }
            } label: {
                Text(returnsToCaller ? returnTitle : index < 0 ? (isWiFi ? "Start Wi-Fi steps" : "My TV matches") : "Next")
                    // Keep the painted cyan control and its hit target wide in the
                    // compact iPad sheet and at accessibility text sizes.
                    .frame(maxWidth: .infinity, minHeight: 52)
            }.buttonStyle(AppButtonStyle(theme: theme, primary: true))
                .accessibilityIdentifier(prefix + "-next")
                .padding(16).frame(maxWidth: .infinity).background(theme.surface)
        }.background(theme.background.ignoresSafeArea()).foregroundColor(theme.text)
    }

    private func back() {
        if mismatch { mismatch = false }
        else if index >= 0 { index -= 1 }
        else { onReturn() }
    }
}
