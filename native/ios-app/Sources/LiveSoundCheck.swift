import AVFoundation
import SwiftUI

/// User-started foreground input. No speech task, file, network or output command.
@MainActor
final class LiveSoundCheck: ObservableObject {
    @Published private(set) var status = "Microphone off"
    @Published private(set) var levelText = "No live input"
    @Published private(set) var levels: [Double] = []
    @Published private(set) var details = "Input details appear while the check runs."
    @Published private(set) var running = false
    @Published private(set) var requesting = false
    @Published private(set) var cleanupFailed = false
    @Published private(set) var permissionDenied = false
    private let microphone = ForegroundMicrophoneGate.shared
    private let recaps = SoundCheckRecaps.shared
    private var recapToken: SoundCheckRecaps.Token?
    private var lease: ForegroundMicrophoneGate.Lease?
    private var permissionRequest = UUID()
    private var settingsAttempt = UUID()
    private var permissionGuidance = false
    private let permissionDeniedMessage = "Microphone permission denied. In app settings, turn on Microphone."
    private var engine: AVAudioEngine?
    private var tapped = false
    private var mailbox: SoundInputMailbox?
    private var timer: Timer?
    private var window = SoundInputWindow()
    private var run: UInt64 = 0
    private var lastSampleAt = 0.0
    private var inputRoute = ""

    func start() {
        settingsAttempt = UUID()
        guard !running, !requesting, !cleanupFailed else { return }
        guard microphone.available else {
            cleanupFailed = microphone.blocked
            status = microphone.blocked ? "Microphone cleanup failed. Close this app completely before trying again."
                : "Another microphone tool is in use. Stop it before starting this check."
            return
        }
        guard UIApplication.shared.applicationState == .active else { return }
        let session = AVAudioSession.sharedInstance()
        switch session.recordPermission {
        case .granted:
            permissionGuidance = false; permissionDenied = false; begin()
        case .denied:
            permissionGuidance = true; permissionDenied = true; status = permissionDeniedMessage
        default:
            permissionGuidance = true; permissionDenied = false
            requesting = true; status = "Requesting microphone permission"
            permissionRequest = UUID(); let token = permissionRequest
            session.requestRecordPermission { [weak self] _ in
                DispatchQueue.main.async {
                    guard let self = self, self.permissionRequest == token else { return }
                    self.requesting = false
                    // Permission is consent to a later explicit Start, never delayed capture.
                    self.refreshPermissionGuidance()
                }
            }
        }
    }

    func refreshPermissionGuidance() {
        guard permissionGuidance else { return }
        settingsAttempt = UUID()
        let permission = AVAudioSession.sharedInstance().recordPermission
        permissionDenied = permission == .denied
        guard !running, !requesting, !cleanupFailed else { return }
        if permission == .granted { status = "Permission granted. Tap Start when you are ready." }
        else if permission == .denied { status = permissionDeniedMessage }
        else { status = "Microphone off. Tap Start to choose permission." }
    }

    func openPermissionSettings() {
        guard permissionDenied, !running, !requesting, !cleanupFailed,
              UIApplication.shared.applicationState == .active else { return }
        guard AVAudioSession.sharedInstance().recordPermission == .denied else {
            refreshPermissionGuidance(); return
        }
        stop("Microphone off", reason: .leftScreen)
        guard !cleanupFailed else { return }
        guard let url = URL(string: UIApplication.openSettingsURLString) else {
            status = "App settings could not open. In iPhone Settings, choose Audio Bodyguard, then Microphone."; return
        }
        let token = UUID(); settingsAttempt = token
        UIApplication.shared.open(url, options: [:]) { [weak self] opened in
            DispatchQueue.main.async {
                guard let self = self, self.settingsAttempt == token, !opened else { return }
                self.status = "App settings could not open. In iPhone Settings, choose Audio Bodyguard, then Microphone."
            }
        }
    }

    private func begin() {
        guard let token = microphone.acquire() else {
            status = "Another microphone tool is in use. Stop it before starting this check."; return
        }
        lease = token
        recapToken = recaps.begin()
        do {
            let session = AVAudioSession.sharedInstance()
            try microphone.activate(token) {
                try session.setCategory(.record, mode: .measurement, options: [])
                try session.setActive(true)
            }
            let audio = AVAudioEngine(); engine = audio
            let input = audio.inputNode, format = input.outputFormat(forBus: 0)
            guard format.sampleRate.isFinite, format.sampleRate > 0,
                  format.channelCount > 0, format.commonFormat == .pcmFormatFloat32,
                  !format.isInterleaved else {
                stop("This microphone format is unavailable. Tap Start to retry.", reason: .invalidInput); return
            }
            let slot = SoundInputMailbox(); mailbox = slot
            let rate = format.sampleRate, channels = format.channelCount
            input.installTap(onBus: 0, bufferSize: 1024, format: format) { buffer, _ in
                // Borrow channel zero only; never retain or modify framework-owned audio.
                guard buffer.format.sampleRate == rate, buffer.format.channelCount == channels,
                      buffer.format.commonFormat == .pcmFormatFloat32, !buffer.format.isInterleaved,
                      buffer.frameLength > 0, buffer.frameLength <= 65_536,
                      buffer.frameLength <= buffer.frameCapacity,
                      let data = buffer.floatChannelData?[0] else {
                    slot.rejectInput(); return
                }
                do {
                    let value = try SoundInputLevel.measure(UnsafeBufferPointer(start: data, count: Int(buffer.frameLength)))
                    slot.publish(value, at: ProcessInfo.processInfo.systemUptime)
                } catch { slot.rejectInput() }
            }
            tapped = true
            audio.prepare(); try audio.start()
            let now = ProcessInfo.processInfo.systemUptime
            guard let token = window.start(at: now) else { stop("The input clock is unavailable.", reason: .invalidInput); return }
            run = token; lastSampleAt = now; inputRoute = routeIdentity()
            details = "iOS-selected microphone · \(Int(rate)) Hz\nChannel 1 of \(channels) · measurement mode requested\nInput processing and gain can vary by phone."
            running = true; levels = []; levelText = "Waiting for microphone input"
            status = "Starting microphone…"
            let updates = Timer(timeInterval: 0.1, repeats: true) { [weak self] _ in
                self?.tick()
            }
            timer = updates
            RunLoop.main.add(updates, forMode: .common)
        } catch { stop("Microphone could not start. Close other recording apps, then tap Start to retry.", reason: .couldNotStart) }
    }

    private func tick() {
        guard running else { return }
        guard UIApplication.shared.applicationState == .active else {
            stop("Microphone stopped when you left the sound check.", reason: .leftScreen); return
        }
        guard AVAudioSession.sharedInstance().recordPermission == .granted,
              engine?.isRunning == true else {
            stop("Microphone input stopped. Check permission, then tap Start to retry.", reason: .permissionChanged); return
        }
        guard routeIdentity() == inputRoute else { routeChanged(); return }
        guard mailbox?.invalidInput != true else {
            stop("Microphone input format changed or was invalid. Tap Start to retry.", reason: .invalidInput); return
        }
        let now = ProcessInfo.processInfo.systemUptime
        if let frame = mailbox?.take(), window.offer(run: run, receivedAt: frame.receivedAt, now: now, value: frame.level) {
            lastSampleAt = frame.receivedAt
            recaps.observe(recapToken)
            let height = frame.level.rmsDbfs.map { min(1, max(0, ($0 + 60) / 60)) } ?? 0
            if levels.count == 60 { levels.removeFirst() }
            levels.append(height)
        }
        let value = window.current(at: now)
        guard window.active else {
            stop(window.endReason == .timeLimit ? "30-second check finished. Tap Start for another check."
                : "The input clock changed. Tap Start for another check.",
                 reason: window.endReason == .timeLimit ? .timeLimit : .invalidInput)
            return
        }
        guard let value = value else {
            levels = []; levelText = "No current input samples"; status = "Waiting for microphone input…"
            if now - lastSampleAt >= 3 { stop("No current microphone input. Tap Start to retry.", reason: .noSamples) }
            return
        }
        status = "Microphone samples received · up to 30 seconds"
        levelText = value.rmsDbfs.map { String(format: "%.1f dBFS", $0) } ?? "No input signal · quiet or blocked"
        if value.fullScaleSamples > 0 { levelText += "\nInput reached digital full scale" }
    }

    func routeChanged() {
        guard running, routeIdentity() != inputRoute else { return }
        stop("Microphone route changed. Tap Start to check the new input.", reason: .routeChanged)
    }
    private func routeIdentity() -> String {
        AVAudioSession.sharedInstance().currentRoute.inputs.map { $0.uid }.joined(separator: "|")
    }
    func interrupt(_ message: String, reason: SoundCheckEnd) {
        if running || requesting { stop(message, reason: reason) }
    }
    func stop(_ message: String = "Microphone stopped", reason: SoundCheckEnd = .stoppedByUser) {
        settingsAttempt = UUID()
        permissionRequest = UUID(); requesting = false; running = false
        timer?.invalidate(); timer = nil; window.stop()
        mailbox?.close(); mailbox = nil
        engine?.stop()
        if tapped { engine?.inputNode.removeTap(onBus: 0); tapped = false }
        engine = nil
        microphone.release(lease) {
            try AVAudioSession.sharedInstance().setActive(false, options: .notifyOthersOnDeactivation)
        }
        lease = nil; cleanupFailed = microphone.blocked
        recaps.finish(recapToken, end: cleanupFailed ? .cleanupFailed : reason)
        recapToken = nil
        levels = []; levelText = "No live input"
        details = "Input details appear while the check runs."
        status = cleanupFailed ? "Microphone cleanup failed. Close this app completely before trying again." : message
    }
}

struct LiveSoundCheckView: View {
    let theme: AppTheme
    @Environment(\.dismiss) private var dismiss
    @Environment(\.scenePhase) private var phase
    @StateObject private var check = LiveSoundCheck()
    @State private var help = false
    @State private var showDetails = false
    @State private var showRecaps = false
    var body: some View {
        VStack(spacing: 12) {
            HStack {
                Text("Live sound check").font(.title2.bold())
                Spacer()
                RoseButton(title: "Close", theme: theme) { check.stop("Sound check closed", reason: .closed); dismiss() }
            }.padding()
            ScrollView {
                VStack(alignment: .leading, spacing: 18) {
                    Text("Try a 30-second microphone check. Speak normally and watch the bars respond.")
                    Text("This check may pause other audio on your iPhone.").font(.caption).foregroundColor(theme.muted)
                    Text(check.status).font(.headline).accessibilityIdentifier("sound-check-status")
                    if check.permissionDenied && !check.cleanupFailed {
                        Button("Open app settings") { check.openPermissionSettings() }
                            .buttonStyle(AppButtonStyle(theme: theme))
                            .disabled(check.running || check.requesting)
                            .accessibilityIdentifier("sound-check-open-settings")
                    }
                    GeometryReader { box in
                        HStack(alignment: .bottom, spacing: 2) {
                            ForEach(0..<60, id: \.self) { index in
                                let offset = index - (60 - check.levels.count)
                                let value = offset >= 0 ? check.levels[offset] : 0
                                RoundedRectangle(cornerRadius: 2).fill(offset >= 0 ? theme.violet : Color.clear)
                                    .frame(width: max(1, (box.size.width - 118) / 60), height: max(2, box.size.height * value))
                            }
                        }.frame(height: box.size.height, alignment: .bottom)
                    }.frame(height: 120).background(theme.raised).cornerRadius(12).accessibilityHidden(true)
                    Text(check.levelText).font(.title2).accessibilityIdentifier("sound-check-level")
                    Text("Relative microphone input · not calibrated room loudness").font(.caption).foregroundColor(theme.muted)
                    Button("[?] What does this show?") {
                        check.stop("Microphone stopped while help is open.", reason: .helpOpened); help = true
                    }.buttonStyle(AppButtonStyle(theme: theme)).accessibilityIdentifier("sound-check-help")
                    Button(showDetails ? "Hide input details" : "Show input details") { showDetails.toggle() }
                        .buttonStyle(AppButtonStyle(theme: theme))
                    if showDetails { Text(check.details).font(.caption).foregroundColor(theme.muted) }
                    Button("Recent sound checks") { showRecaps = true }
                        .buttonStyle(AppButtonStyle(theme: theme))
                        .disabled(check.running || check.requesting)
                        .accessibilityIdentifier("sound-check-recaps")
                    Text("Automatic protection is not active.").foregroundColor(theme.warning)
                }.padding()
            }.accessibilityIdentifier("sound-check-scroll")
            Button(check.running || check.requesting ? "Stop sound check" : "Start sound check") {
                if check.running || check.requesting { check.stop() } else { check.start() }
            }.buttonStyle(AppButtonStyle(theme: theme, primary: true))
                .disabled(check.cleanupFailed).accessibilityIdentifier("sound-check-start-stop").padding()
        }.background(theme.background.ignoresSafeArea()).foregroundColor(theme.text)
            .sheet(isPresented: $showRecaps) { RecentSoundChecksView(theme: theme) }
            .alert("About the sound check", isPresented: $help) {
                Button("Close", role: .cancel) {}
            } message: {
                Text("The bars use real microphone samples from this phone. dBFS describes digital input relative to full scale. It is not dBA or a hearing-safety measurement. Phone gain, processing, position and input route change the result.\n\nZero input can mean a quiet signal or blocked input. This check cannot decide whether sound is safe.\n\nListening stops after 30 seconds or when you leave this screen. No audio files are saved or uploaded. Speech recognition, automatic protection and TV controls are not part of this check.")
            }
            .onChange(of: phase) { value in
                if value == .active { check.refreshPermissionGuidance() }
                else { check.interrupt("Microphone stopped when you left the sound check.", reason: .leftScreen) }
            }
            .onReceive(NotificationCenter.default.publisher(for: AVAudioSession.interruptionNotification)) { _ in
                check.interrupt("Audio interrupted. Tap Start to try again.", reason: .audioInterrupted)
            }
            .onReceive(NotificationCenter.default.publisher(for: AVAudioSession.routeChangeNotification)) { _ in check.routeChanged() }
            .onReceive(NotificationCenter.default.publisher(for: AVAudioSession.mediaServicesWereLostNotification)) { _ in
                check.interrupt("Audio services stopped. Tap Start to try again.", reason: .audioServicesChanged)
            }
            .onReceive(NotificationCenter.default.publisher(for: AVAudioSession.mediaServicesWereResetNotification)) { _ in
                check.interrupt("Audio services reset. Tap Start to try again.", reason: .audioServicesChanged)
            }
            .onDisappear { check.stop("Sound check closed", reason: .closed) }
    }
}


/// Local input observations only; kept separate from the protection/session journal.
private struct RecentSoundChecksView: View {
    let theme: AppTheme
    @Environment(\.dismiss) private var dismiss
    @State private var rows: [SoundCheckRecap] = []
    var body: some View {
        VStack(spacing: 12) {
            HStack {
                Text("Recent sound checks").font(.title2.bold())
                Spacer()
                RoseButton(title: "Close", theme: theme) { dismiss() }.accessibilityIdentifier("sound-recaps-close")
            }.padding()
            ScrollView {
                VStack(alignment: .leading, spacing: 18) {
                    Text("Up to five completed checks, most recent first. Kept in memory; cleared when this app process ends.")
                    if rows.isEmpty {
                        Text("No completed sound checks in this app session.")
                            .accessibilityIdentifier("sound-recaps-empty")
                    }
                    ForEach(rows.indices, id: \.self) { index in
                        VStack(alignment: .leading, spacing: 8) {
                            Text("Check \(index + 1) · \(rows[index].inputObserved ? "Input samples observed" : "No input samples observed")").font(.headline)
                            Text(rows[index].end.rawValue)
                        }.accessibilityElement(children: .combine)
                    }
                    Text("These are meter observations from this phone, not proof of continuous listening, sound safety or TV control. Audio and recognized words are not kept in recaps.")
                        .font(.caption).foregroundColor(theme.muted)
                }.padding()
            }.accessibilityIdentifier("sound-recaps-scroll")
            if !rows.isEmpty {
                Button("Clear recaps") { SoundCheckRecaps.shared.clear(); rows = [] }
                    .buttonStyle(AppButtonStyle(theme: theme))
                    .accessibilityIdentifier("sound-recaps-clear").padding()
            }
        }.background(theme.background.ignoresSafeArea()).foregroundColor(theme.text)
            .onAppear { rows = SoundCheckRecaps.shared.snapshot() }
    }
}
