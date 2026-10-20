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
    private let microphone = ForegroundMicrophoneGate.shared
    private var lease: ForegroundMicrophoneGate.Lease?
    private var permissionRequest = UUID()
    private var engine: AVAudioEngine?
    private var tapped = false
    private var mailbox: SoundInputMailbox?
    private var timer: Timer?
    private var window = SoundInputWindow()
    private var run: UInt64 = 0
    private var lastSampleAt = 0.0
    private var inputRoute = ""

    func start() {
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
        case .granted: begin()
        case .denied: status = "Microphone permission denied. You can allow it in iPhone Settings."
        default:
            requesting = true; status = "Requesting microphone permission"
            permissionRequest = UUID(); let token = permissionRequest
            session.requestRecordPermission { [weak self] allowed in
                DispatchQueue.main.async {
                    guard let self = self, self.permissionRequest == token else { return }
                    self.requesting = false
                    // Permission is consent to a later explicit Start, never delayed capture.
                    self.status = allowed ? "Permission granted. Tap Start when you are ready."
                        : "Microphone permission denied. You can allow it in iPhone Settings."
                }
            }
        }
    }

    private func begin() {
        guard let token = microphone.acquire() else {
            status = "Another microphone tool is in use. Stop it before starting this check."; return
        }
        lease = token
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
                stop("This microphone format is unavailable. Tap Start to retry."); return
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
            guard let token = window.start(at: now) else { stop("The input clock is unavailable."); return }
            run = token; lastSampleAt = now; inputRoute = routeIdentity()
            details = "iOS-selected microphone · \(Int(rate)) Hz\nChannel 1 of \(channels) · measurement mode requested\nInput processing and gain can vary by phone."
            running = true; levels = []; levelText = "Waiting for microphone input"
            status = "Starting microphone…"
            let updates = Timer(timeInterval: 0.1, repeats: true) { [weak self] _ in
                self?.tick()
            }
            timer = updates
            RunLoop.main.add(updates, forMode: .common)
        } catch { stop("Microphone could not start. Close other recording apps, then tap Start to retry.") }
    }

    private func tick() {
        guard running else { return }
        guard UIApplication.shared.applicationState == .active else {
            stop("Microphone stopped when you left the sound check."); return
        }
        guard AVAudioSession.sharedInstance().recordPermission == .granted,
              engine?.isRunning == true else {
            stop("Microphone input stopped. Check permission, then tap Start to retry."); return
        }
        guard routeIdentity() == inputRoute else { routeChanged(); return }
        guard mailbox?.invalidInput != true else {
            stop("Microphone input format changed or was invalid. Tap Start to retry."); return
        }
        let now = ProcessInfo.processInfo.systemUptime
        if let frame = mailbox?.take(), window.offer(run: run, receivedAt: frame.receivedAt, now: now, value: frame.level) {
            lastSampleAt = frame.receivedAt
            let height = frame.level.rmsDbfs.map { min(1, max(0, ($0 + 60) / 60)) } ?? 0
            if levels.count == 60 { levels.removeFirst() }
            levels.append(height)
        }
        let value = window.current(at: now)
        guard window.active else {
            stop(window.endReason == .timeLimit ? "30-second check finished. Tap Start for another check."
                : "The input clock changed. Tap Start for another check.")
            return
        }
        guard let value = value else {
            levels = []; levelText = "No current input samples"; status = "Waiting for microphone input…"
            if now - lastSampleAt >= 3 { stop("No current microphone input. Tap Start to retry.") }
            return
        }
        status = "Microphone samples received · up to 30 seconds"
        levelText = value.rmsDbfs.map { String(format: "%.1f dBFS", $0) } ?? "No input signal · quiet or blocked"
        if value.fullScaleSamples > 0 { levelText += "\nInput reached digital full scale" }
    }

    func routeChanged() {
        guard running, routeIdentity() != inputRoute else { return }
        stop("Microphone route changed. Tap Start to check the new input.")
    }
    private func routeIdentity() -> String {
        AVAudioSession.sharedInstance().currentRoute.inputs.map { $0.uid }.joined(separator: "|")
    }
    func interrupt(_ message: String) {
        if running || requesting { stop(message) }
    }
    func stop(_ message: String = "Microphone stopped") {
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
    var body: some View {
        VStack(spacing: 12) {
            HStack {
                Text("Live sound check").font(.title2.bold())
                Spacer()
                RoseButton(title: "Close", theme: theme) { check.stop(); dismiss() }
            }.padding()
            ScrollView {
                VStack(alignment: .leading, spacing: 18) {
                    Text("Try a 30-second microphone check. Speak normally and watch the bars respond.")
                    Text("This check may pause other audio on your iPhone.").font(.caption).foregroundColor(theme.muted)
                    Text(check.status).font(.headline).accessibilityIdentifier("sound-check-status")
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
                        check.stop("Microphone stopped while help is open."); help = true
                    }.buttonStyle(AppButtonStyle(theme: theme)).accessibilityIdentifier("sound-check-help")
                    Button(showDetails ? "Hide input details" : "Show input details") { showDetails.toggle() }
                        .buttonStyle(AppButtonStyle(theme: theme))
                    if showDetails { Text(check.details).font(.caption).foregroundColor(theme.muted) }
                    Text("Automatic protection is not active.").foregroundColor(theme.warning)
                }.padding()
            }.accessibilityIdentifier("sound-check-scroll")
            Button(check.running || check.requesting ? "Stop sound check" : "Start sound check") {
                if check.running || check.requesting { check.stop() } else { check.start() }
            }.buttonStyle(AppButtonStyle(theme: theme, primary: true))
                .disabled(check.cleanupFailed).accessibilityIdentifier("sound-check-start-stop").padding()
        }.background(theme.background.ignoresSafeArea()).foregroundColor(theme.text)
            .alert("About the sound check", isPresented: $help) {
                Button("Close", role: .cancel) {}
            } message: {
                Text("The bars use real microphone samples from this phone. dBFS describes digital input relative to full scale. It is not dBA or a hearing-safety measurement. Phone gain, processing, position and input route change the result.\n\nZero input can mean a quiet signal or blocked input. This check cannot decide whether sound is safe.\n\nListening stops after 30 seconds or when you leave this screen. No audio files are saved or uploaded. Speech recognition, automatic protection and TV controls are not part of this check.")
            }
            .onChange(of: phase) { if $0 != .active { check.interrupt("Microphone stopped when you left the sound check.") } }
            .onReceive(NotificationCenter.default.publisher(for: AVAudioSession.interruptionNotification)) { _ in
                check.interrupt("Audio interrupted. Tap Start to try again.")
            }
            .onReceive(NotificationCenter.default.publisher(for: AVAudioSession.routeChangeNotification)) { _ in check.routeChanged() }
            .onReceive(NotificationCenter.default.publisher(for: AVAudioSession.mediaServicesWereLostNotification)) { _ in
                check.interrupt("Audio services stopped. Tap Start to try again.")
            }
            .onReceive(NotificationCenter.default.publisher(for: AVAudioSession.mediaServicesWereResetNotification)) { _ in
                check.interrupt("Audio services reset. Tap Start to try again.")
            }
            .onDisappear { check.stop("Sound check closed") }
    }
}
