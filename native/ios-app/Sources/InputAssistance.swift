import AVFoundation
import AVKit
import Speech
import SwiftUI
import Vision
import PhotosUI
import ImageIO
import Darwin

/// A per-run ingress closes before endAudio, so late tap callbacks cannot append.
/// Framework speech buffering and append latency are not application-controlled bounds.
private final class VoiceAudioInput {
    let request: SFSpeechAudioBufferRecognitionRequest
    private let summaries: SoundInputMailbox
    private let rate: Double
    private let channels: AVAudioChannelCount
    private let lock = NSLock()
    private var open = true
    init(request: SFSpeechAudioBufferRecognitionRequest, summaries: SoundInputMailbox,
         format: AVAudioFormat) {
        self.request = request; self.summaries = summaries
        rate = format.sampleRate; channels = format.channelCount
    }
    func receive(_ buffer: AVAudioPCMBuffer) {
        // Contention drops this buffer rather than waiting on app-owned state.
        guard lock.try() else { return }
        defer { lock.unlock() }
        guard open else { return }
        guard buffer.format.sampleRate == rate, buffer.format.channelCount == channels,
              buffer.format.commonFormat == .pcmFormatFloat32, !buffer.format.isInterleaved,
              buffer.frameLength > 0, buffer.frameLength <= 65_536,
              buffer.frameLength <= buffer.frameCapacity,
              let data = buffer.floatChannelData?[0] else {
            summaries.rejectInput(); return
        }
        do {
            let value = try SoundInputLevel.measure(UnsafeBufferPointer(start: data, count: Int(buffer.frameLength)))
            request.append(buffer)
            summaries.publish(value, at: ProcessInfo.processInfo.systemUptime)
        } catch { summaries.rejectInput() }
    }
    func close() {
        summaries.close()
        lock.lock(); defer { lock.unlock() }
        guard open else { return }
        open = false; request.endAudio()
    }
}

/// Foreground input only. Recognition results never enter an output control path.
@MainActor
final class VoiceCheck: ObservableObject {
    @Published private(set) var status = "Microphone off"
    @Published private(set) var transcript = ""
    @Published private(set) var levels: [Double] = []
    @Published private(set) var levelText = "No live microphone samples"
    @Published private(set) var running = false
    @Published private(set) var requesting = false
    @Published private(set) var cleanupFailed = false
    @Published private(set) var permissionSettingsAvailable = false
    private let microphone = ForegroundMicrophoneGate.shared
    private var lease: ForegroundMicrophoneGate.Lease?
    private var permissionRequest = UUID()
    private var settingsAttempt = UUID()
    private var permissionGuidance = false
    private var engine: AVAudioEngine?
    private var task: SFSpeechRecognitionTask?
    private var recognizer: SFSpeechRecognizer?
    private var ingress: VoiceAudioInput?
    private var summaries: SoundInputMailbox?
    private var words: VoiceResultMailbox?
    private var tapped = false
    private var timer: Timer?
    private var window = SoundInputWindow()
    private var run: UInt64 = 0
    private var lastSampleAt = 0.0
    private var inputRoute = ""
    // This fixture has authored buttons, not a TV or third-party player adapter.
    @Published private(set) var demoIntroAvailable = true
    @Published private(set) var demoRecapAvailable = true
    @Published private(set) var demoMessage = "Test player ready — nothing connected"
    private var demoGeneration = 1
    private let voiceSkipGate = OwnedVoiceSkipGate()
    private var voiceSkipRunID: String?
    // A silent, bundled eight-second H.264 fixture; never a remote player.
    let localPlayer = AVPlayer()
    @Published private(set) var localVideoVisible = false
    @Published private(set) var localVideoStatus = "Local video not prepared"
    private var localMode: OwnedSkipAction?
    private var localBusy = false
    private var localEpoch = 0

    /// Prepare the specific authored intro (0-2s) or recap (4-6s) segment.
    /// This does not grant TV authority or synthesize a voice result.
    func prepareLocalVideo(_ action: OwnedSkipAction) {
        guard !running, !requesting, !localBusy else { return }
        guard let url = Bundle.main.url(forResource: "voice_skip_sample", withExtension: "mp4") else {
            localVideoStatus = "Local video unavailable: bundled clip missing"; return
        }
        localEpoch += 1; let epoch = localEpoch
        localMode = nil; localBusy = true
        demoIntroAvailable = false; demoRecapAvailable = false; demoGeneration += 1
        localVideoStatus = "Local video: preparing segment"
        localPlayer.pause()
        localPlayer.replaceCurrentItem(with: AVPlayerItem(url: url))
        localVideoVisible = true
        let entry = action == .intro ? 0.0 : 4.0
        localPlayer.seek(to: CMTime(seconds: entry, preferredTimescale: 600),
                         toleranceBefore: .zero, toleranceAfter: .zero) { [weak self] finished in
            Task { @MainActor [weak self] in
                guard let self = self, self.localEpoch == epoch else { return }
                let observed = self.localPlayer.currentTime().seconds
                self.localBusy = false
                guard finished, observed.isFinite, abs(observed - entry) < 0.3 else {
                    self.localVideoStatus = "Local video unavailable: entry not observed"
                    return
                }
                self.localMode = action
                self.demoIntroAvailable = action == .intro
                self.demoRecapAvailable = action == .recap
                self.demoGeneration += 1
                self.localVideoStatus = action == .intro
                    ? "Local video: intro ready at 0s" : "Local video: recap ready at 4s"
            }
        }
    }

    private func requestLocalVideoSkip(_ action: OwnedSkipAction) -> Bool {
        guard !localBusy, localMode == action else { return false }
        localEpoch += 1; let epoch = localEpoch
        localMode = nil; localBusy = true
        demoIntroAvailable = false; demoRecapAvailable = false; demoGeneration += 1
        demoMessage = action == .intro ? "Test player: Skip Intro button activated"
                                       : "Test player: Skip Recap button activated"
        localVideoStatus = "Local video: transition requested, awaiting player readback"
        let target = action == .intro ? 2.0 : 6.0
        localPlayer.seek(to: CMTime(seconds: target, preferredTimescale: 600),
                         toleranceBefore: .zero, toleranceAfter: .zero) { [weak self] finished in
            Task { @MainActor [weak self] in
                guard let self = self, self.localEpoch == epoch else { return }
                self.localBusy = false
                let observed = self.localPlayer.currentTime().seconds
                guard finished, observed.isFinite, abs(observed - target) < 0.3 else {
                    self.localVideoStatus = "Local video: requested but position NOT verified"
                    return
                }
                // Read back the actual AVPlayer time, rather than trusting button state.
                self.localVideoStatus = action == .intro
                    ? "Local video observed: intro ends at 2s"
                    : "Local video observed: recap ends at 6s"
            }
        }
        return true // REQUESTED, never verified until the asynchronous player readback.
    }

    private func closeLocalVideo() {
        localEpoch += 1; localMode = nil; localBusy = false
        localPlayer.pause(); localPlayer.replaceCurrentItem(with: nil)
        localVideoVisible = false; localVideoStatus = "Local video not prepared"
    }

    private var demoSnapshot: OwnedSkipSnapshot {
        OwnedSkipSnapshot(playerID: "owned-test-player", playbackSessionID: "voice-demo",
                          contentID: "test-episode", generation: demoGeneration,
                          introVisible: demoIntroAvailable, introEnabled: demoIntroAvailable,
                          recapVisible: demoRecapAvailable, recapEnabled: demoRecapAvailable)
    }

    /// Shared callback used by the two visible buttons and admitted final voice intent.
    @discardableResult func pressDemo(_ action: OwnedSkipAction) -> Bool {
        if localVideoVisible { return requestLocalVideoSkip(action) }
        switch action {
        case .intro where demoIntroAvailable:
            demoIntroAvailable = false; demoGeneration += 1
            demoMessage = "Test player: Skip Intro button activated"
            return true
        case .recap where demoRecapAvailable:
            demoRecapAvailable = false; demoGeneration += 1
            demoMessage = "Test player: Skip Recap button activated"
            return true
        default: return false
        }
    }

    func resetDemo() {
        guard !running, !requesting else { return }
        demoIntroAvailable = true; demoRecapAvailable = true
        demoGeneration += 1
        demoMessage = "Test player ready — nothing connected"
        closeLocalVideo()
    }

    private func handleFinalSkipCommand(_ text: String?) -> String {
        guard let runID = voiceSkipRunID else {
            return "Finished — no supported test-player command. Nothing sent to a TV."
        }
        // The final recognizer event uses the same one-shot gate exercised in Swift native tests.
        let decision = voiceSkipGate.requestFinal(text, runID: runID, observed: demoSnapshot,
            permitted: AVAudioSession.sharedInstance().recordPermission == .granted,
            foreground: UIApplication.shared.applicationState == .active,
            pressOwnedButton: { action in self.pressDemo(action) })
        switch decision {
        case .requested: return "Test-player Skip button requested. No TV command sent."
        case .callFailed: return "Test-player button unavailable. No TV command sent."
        case .unavailable: return "Skip target changed or was unavailable. No TV command sent."
        }
    }

    func start() {
        settingsAttempt = UUID()
        guard !running, !requesting, !cleanupFailed,
              UIApplication.shared.applicationState == .active else { return }
        guard microphone.available else {
            cleanupFailed = microphone.blocked
            status = microphone.blocked ? "Microphone cleanup failed. Close this app completely before trying again."
                : "Another microphone tool is in use. Stop it before starting this check."
            return
        }
        switch AVAudioSession.sharedInstance().recordPermission {
        case .denied:
            permissionGuidance = true; refreshPermissionGuidance(); return
        case .granted: break
        case .undetermined:
            permissionGuidance = true; permissionSettingsAvailable = false
            requesting = true; status = "Requesting microphone permission"
            permissionRequest = UUID(); let token = permissionRequest
            AVAudioSession.sharedInstance().requestRecordPermission { [weak self] _ in
                DispatchQueue.main.async {
                    guard let self = self, self.permissionRequest == token else { return }
                    self.requesting = false
                    self.refreshPermissionGuidance()
                }
            }
            return
        @unknown default:
            permissionGuidance = true; refreshPermissionGuidance(); return
        }
        switch SFSpeechRecognizer.authorizationStatus() {
        case .authorized:
            permissionGuidance = false; permissionSettingsAvailable = false; begin()
        case .notDetermined:
            permissionGuidance = true; permissionSettingsAvailable = false
            requesting = true; status = "Requesting speech permission"
            permissionRequest = UUID(); let token = permissionRequest
            SFSpeechRecognizer.requestAuthorization { [weak self] _ in
                DispatchQueue.main.async {
                    guard let self = self, self.permissionRequest == token else { return }
                    self.requesting = false
                    self.refreshPermissionGuidance()
                }
            }
        default:
            permissionGuidance = true; refreshPermissionGuidance()
        }
    }

    func refreshPermissionGuidance() {
        guard permissionGuidance else { return }
        settingsAttempt = UUID()
        var canOpenSettings = false
        let message: String
        switch AVAudioSession.sharedInstance().recordPermission {
        case .denied:
            canOpenSettings = true
            message = "Microphone permission denied. In app settings, check Microphone."
        case .undetermined:
            message = "Microphone off. Tap Start to choose permission."
        case .granted:
            switch SFSpeechRecognizer.authorizationStatus() {
            case .denied:
                canOpenSettings = true
                message = "Speech permission denied. In app settings, check Speech Recognition."
            case .restricted:
                message = "Speech recognition is restricted on this iPhone. No audio is being captured."
            case .notDetermined:
                message = "Microphone permission granted. Tap Start to choose speech permission."
            case .authorized:
                message = "Permissions granted. Tap Start when you are ready."
            @unknown default:
                message = "Speech permission is unavailable. No audio is being captured."
            }
        @unknown default:
            message = "Microphone permission is unavailable. No audio is being captured."
        }
        permissionSettingsAvailable = canOpenSettings
        guard !running, !requesting, !cleanupFailed else { return }
        status = message
    }

    func openPermissionSettings() {
        guard permissionSettingsAvailable, !running, !requesting, !cleanupFailed,
              UIApplication.shared.applicationState == .active else { return }
        let mic = AVAudioSession.sharedInstance().recordPermission
        guard mic == .denied || (mic == .granted && SFSpeechRecognizer.authorizationStatus() == .denied) else {
            refreshPermissionGuidance(); return
        }
        clear()
        guard !cleanupFailed else { return }
        let fallback = "App settings could not open. In iPhone Settings, choose Audio Bodyguard, then check Microphone and Speech Recognition."
        guard let url = URL(string: UIApplication.openSettingsURLString) else { status = fallback; return }
        let token = UUID(); settingsAttempt = token
        UIApplication.shared.open(url, options: [:]) { [weak self] opened in
            DispatchQueue.main.async {
                guard let self = self, self.settingsAttempt == token, !opened else { return }
                self.status = fallback
            }
        }
    }
    private func begin() {
        guard let speech = SFSpeechRecognizer(), speech.isAvailable, speech.supportsOnDeviceRecognition else {
            status = "On-device speech recognition is unavailable for this language or device. No cloud fallback is used."; return
        }
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
            guard format.sampleRate.isFinite, format.sampleRate > 0, format.channelCount > 0,
                  format.commonFormat == .pcmFormatFloat32, !format.isInterleaved else {
                stop("This microphone format is unavailable. Tap Start to retry."); return
            }
            let slot = SoundInputMailbox(), updates = VoiceResultMailbox()
            summaries = slot; words = updates
            let request = SFSpeechAudioBufferRecognitionRequest()
            request.requiresOnDeviceRecognition = true; request.shouldReportPartialResults = true
            let inputRun = VoiceAudioInput(request: request, summaries: slot, format: format)
            ingress = inputRun; recognizer = speech
            input.installTap(onBus: 0, bufferSize: 1024, format: format) { buffer, _ in inputRun.receive(buffer) }
            tapped = true
            task = speech.recognitionTask(with: request) { result, error in
                updates.publish(text: result?.bestTranscription.formattedString,
                                final: result?.isFinal == true, failed: error != nil)
            }
            audio.prepare(); try audio.start()
            let now = ProcessInfo.processInfo.systemUptime
            guard let token = window.start(at: now) else { stop("The input clock is unavailable."); return }
            run = token; lastSampleAt = now; inputRoute = routeIdentity()
            let skipRun = UUID().uuidString
            guard voiceSkipGate.start(runID: skipRun, player: demoSnapshot) else {
                stop("Test-player session could not start. Tap Start to retry."); return
            }
            voiceSkipRunID = skipRun
            transcript = ""; levels = []; levelText = "Waiting for microphone input"
            running = true; status = "Starting on-device voice check…"
            let updatesTimer = Timer(timeInterval: 0.1, repeats: true) { [weak self] _ in self?.tick() }
            timer = updatesTimer; RunLoop.main.add(updatesTimer, forMode: .common)
        } catch { stop("Microphone could not start. Close other recording apps, then tap Start to retry.") }
    }
    private func tick() {
        guard running else { return }
        guard UIApplication.shared.applicationState == .active else {
            clear("Microphone stopped when you left the voice check."); return
        }
        // Keep the existing check order, but describe only the failed check.
        // Availability or engine loss does not establish a permission change.
        guard AVAudioSession.sharedInstance().recordPermission == .granted else {
            stop("Microphone access is unavailable. Check app permissions, then tap Start. Words may be incomplete."); return
        }
        guard SFSpeechRecognizer.authorizationStatus() == .authorized else {
            stop("Speech access is unavailable. Check app permissions, then tap Start. Words may be incomplete."); return
        }
        guard recognizer?.isAvailable == true else {
            stop("Speech recognition is unavailable right now. Try Live sound check for microphone levels. Words may be incomplete."); return
        }
        guard engine?.isRunning == true else {
            stop("Voice input stopped. Tap Start to try again. Words may be incomplete."); return
        }
        guard routeIdentity() == inputRoute else { routeChanged(); return }
        guard summaries?.invalidInput != true else {
            stop("Microphone input format changed or was invalid. Tap Start to retry."); return
        }
        let now = ProcessInfo.processInfo.systemUptime
        if let frame = summaries?.take(), window.offer(run: run, receivedAt: frame.receivedAt, now: now, value: frame.level) {
            lastSampleAt = frame.receivedAt
            if levels.count == 40 { levels.removeFirst() }
            levels.append(frame.level.rmsDbfs.map { min(1, max(0, ($0 + 60) / 60)) } ?? 0)
        }
        let level = window.current(at: now)
        guard window.active else {
            stop(window.endReason == .timeLimit ? "30-second limit reached. Tap Start to try again."
                : "The input clock changed. Tap Start to try again."); return
        }
        if let update = words?.take() {
            if let text = update.text { transcript = text }
            if update.failed { stop("Speech recognition stopped. Tap Start to try again. Words may be incomplete."); return }
            if update.final { stop(handleFinalSkipCommand(update.text)); return }
        }
        guard let level = level else {
            levels = []; levelText = "No current microphone samples"; status = "Waiting for microphone input…"
            if now - lastSampleAt >= 3 { stop("No current microphone input. Tap Start to retry.") }
            return
        }
        levelText = level.rmsDbfs.map { String(format: "Microphone input: %.1f dBFS", $0) }
            ?? "No input signal · quiet or blocked"
        if level.fullScaleSamples > 0 { levelText += "\nInput reached digital full scale" }
        status = "Listening — on this phone, up to 30 seconds"
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
    func stop(_ message: String = "Microphone off") {
        settingsAttempt = UUID()
        permissionRequest = UUID(); requesting = false; running = false
        timer?.invalidate(); timer = nil; window.stop()
        voiceSkipGate.stop(); voiceSkipRunID = nil
        words?.close(); words = nil
        ingress?.close(); ingress = nil; summaries = nil
        engine?.stop()
        if tapped { engine?.inputNode.removeTap(onBus: 0); tapped = false }
        engine = nil; task?.cancel(); task = nil; recognizer = nil
        microphone.release(lease) {
            try AVAudioSession.sharedInstance().setActive(false, options: .notifyOthersOnDeactivation)
        }
        lease = nil; cleanupFailed = microphone.blocked
        levels = []; levelText = "No live microphone samples"
        status = cleanupFailed ? "Microphone cleanup failed. Close this app completely before trying again." : message
    }
    func clear(_ message: String = "Microphone off") {
        stop(message); transcript = ""; resetDemo()
    }
}

struct VoiceCheckView: View {
    let theme: AppTheme
    @Environment(\.dismiss) private var dismiss
    @Environment(\.scenePhase) private var phase
    @StateObject private var voice = VoiceCheck()
    @State private var setupVisible = false
    @State private var voiceHelp = false
    @State private var localVideoHelp = false
    var body: some View {
        VStack(spacing: 12) {
            HStack { Text("Voice check").font(.title2.bold()); Spacer(); RoseButton(title: "Close", theme: theme) { voice.clear(); dismiss() } }.padding()
            ScrollView {
                VStack(alignment: .leading, spacing: 18) {
                    Text("See what your phone hears").font(.title.bold())

                    Text("Tap Start, then say “Audio Bodyguard, skip intro” or “Audio Bodyguard, skip recap.”")
                    Text("This check may pause other audio on your iPhone.").font(.caption).foregroundColor(theme.muted)
                    Text(voice.status).font(.headline).accessibilityIdentifier("voice-status")
                    if voice.permissionSettingsAvailable && !voice.cleanupFailed {
                        Button("Open app settings") { voice.openPermissionSettings() }
                            .buttonStyle(AppButtonStyle(theme: theme))
                            .disabled(voice.running || voice.requesting)
                            .accessibilityIdentifier("voice-open-settings")
                    }
                    GeometryReader { box in
                        HStack(alignment: .center, spacing: 2) {
                            ForEach(0..<40, id: \.self) { index in
                                let offset = index - (40 - voice.levels.count)
                                let level = offset >= 0 ? voice.levels[offset] : 0
                                RoundedRectangle(cornerRadius: 2).fill(offset >= 0 ? theme.violet : Color.clear)
                                    .frame(width: max(1, (box.size.width - 78) / 40), height: max(2, box.size.height * level))
                            }
                        }.frame(height: box.size.height)
                    }.frame(height: 120).accessibilityHidden(true)
                    Text(voice.levelText).foregroundColor(theme.muted)
                    Text("Digital input levels over time (dBFS).").font(.caption).foregroundColor(theme.muted)
                    Text("Recent recognized words · may change").font(.headline)
                    Text(voice.transcript.isEmpty ? "No words recognized yet" : voice.transcript).accessibilityIdentifier("voice-transcript")
                    Text("Test player — this app only").font(.headline)
                    Text("These are test-player buttons in Audio Bodyguard only. No TV or streaming app is controlled.")
                        .font(.caption).foregroundColor(theme.muted)
                    HStack {
                        Button("Skip Intro") { voice.pressDemo(.intro) }
                            .buttonStyle(AppButtonStyle(theme: theme))
                            .disabled(!voice.demoIntroAvailable)
                            .accessibilityIdentifier("voice-demo-skip-intro")
                        Button("Skip Recap") { voice.pressDemo(.recap) }
                            .buttonStyle(AppButtonStyle(theme: theme))
                            .disabled(!voice.demoRecapAvailable)
                            .accessibilityIdentifier("voice-demo-skip-recap")
                    }
                    Text(voice.demoMessage).accessibilityIdentifier("voice-demo-result")
                    QuestionDisclosure(title: "Local video trial", theme: theme,
                                       isExpanded: $localVideoHelp, identifier: "voice-local-video-help") {
                        Text("An eight-second silent test clip with separate intro and recap sections. No TV or streaming player is controlled.")
                            .font(.caption).foregroundColor(theme.muted)
                        HStack {
                            Button("Prepare intro video") { voice.prepareLocalVideo(.intro) }
                                .buttonStyle(AppButtonStyle(theme: theme))
                                .disabled(voice.running || voice.requesting)
                                .accessibilityIdentifier("voice-local-prepare-intro")
                            Button("Prepare recap video") { voice.prepareLocalVideo(.recap) }
                                .buttonStyle(AppButtonStyle(theme: theme))
                                .disabled(voice.running || voice.requesting)
                                .accessibilityIdentifier("voice-local-prepare-recap")
                        }
                        Text(voice.localVideoStatus).accessibilityIdentifier("voice-local-video-status")
                        if voice.localVideoVisible {
                            VideoPlayer(player: voice.localPlayer).frame(height: 110)
                                .accessibilityIdentifier("voice-local-video-preview")
                        }
                    }
                    Button("Reset test player") { voice.resetDemo() }
                        .buttonStyle(AppButtonStyle(theme: theme))
                        .disabled(voice.running || voice.requesting)
                        .accessibilityIdentifier("voice-demo-reset")
                    QuestionDisclosure(title: "Voice help", theme: theme, isExpanded: $voiceHelp, identifier: "voice-help") {
                        Text("A final recognized command can activate an available test-player button once. Check the result; no TV command is sent. Listening stops when you leave.")
                        Button("Jump to voice steps") { voice.clear(); setupVisible = true }.buttonStyle(AppButtonStyle(theme: theme))
                        Button("Clear words") { voice.clear() }.buttonStyle(AppButtonStyle(theme: theme))
                    }
                }.padding()
            }
            HStack {
                Button(voice.running || voice.requesting ? "Stop listening" : "Start voice check") {
                    if voice.running || voice.requesting { voice.stop() } else { voice.start() }
                }.buttonStyle(AppButtonStyle(theme: theme, primary: true)).disabled(voice.cleanupFailed).accessibilityIdentifier("voice-start-stop")
            }.padding()
        }.background(theme.background.ignoresSafeArea()).foregroundColor(theme.text)
            .sheet(isPresented: $setupVisible) { SetupGuidesView(theme: theme, initialGroup: "voice", onVoiceCheck: {}) }
            .onChange(of: phase) {
                if $0 == .active { voice.refreshPermissionGuidance() }
                else { voice.clear("Microphone stopped when you left the voice check.") }
            }
            .onReceive(NotificationCenter.default.publisher(for: AVAudioSession.interruptionNotification)) { _ in voice.interrupt("Audio interrupted — tap Start to try again.") }
            .onReceive(NotificationCenter.default.publisher(for: AVAudioSession.routeChangeNotification)) { _ in voice.routeChanged() }
            .onReceive(NotificationCenter.default.publisher(for: AVAudioSession.mediaServicesWereLostNotification)) { _ in
                voice.interrupt("Audio services stopped. Tap Start to try again.")
            }
            .onReceive(NotificationCenter.default.publisher(for: AVAudioSession.mediaServicesWereResetNotification)) { _ in
                voice.interrupt("Audio services reset. Tap Start to try again.")
            }
            .onDisappear { voice.clear() }
    }
}

/// Retained by import/decoder and Vision closures, never by the result view.
/// Every closure extends this lifetime through its own return and cleanup.
final class PhotoReadWork: @unchecked Sendable {
    private let lease: PhotoWorkSlot.Lease
    init(_ lease: PhotoWorkSlot.Lease) { self.lease = lease }
    deinit { PhotoWorkSlot.process.release(lease) }
}

@MainActor
final class PhotoCheck: ObservableObject {
    @Published var hints = TVPhotoHints("")
    @Published var status = "No photo selected"
    private var workObservation: PhotoWorkSlot.Observation?
    private var waitingForPhotoWork = false
    private let run = PhotoReviewRun(now: {
        var timebase = mach_timebase_info_data_t()
        guard mach_timebase_info(&timebase) == KERN_SUCCESS, timebase.denom != 0 else { return .nan }
        return Double(mach_continuous_time()) * Double(timebase.numer) / Double(timebase.denom) / 1_000_000_000
    })
    private var timer: Timer?
    private var readingToken: PhotoReviewRun.Token?
    private func stopWatchdog() { timer?.invalidate(); timer = nil; readingToken = nil }
    private func resetDetails() { waitingForPhotoWork = false; hints = TVPhotoHints(""); status = "No photo selected" }
    func observeWork() {
        workObservation?.close()
        workObservation = PhotoWorkSlot.process.observe { [weak self] in
            DispatchQueue.main.async { [weak self] in self?.refreshPhotoAvailability() }
        }
        refreshPhotoAvailability()
    }
    func stopObservingWork() { workObservation?.close(); workObservation = nil }
    private func showBusy() {
        waitingForPhotoWork = true
        status = "The previous photo is still finishing. Try again shortly."
        refreshPhotoAvailability()
    }
    private func refreshPhotoAvailability() {
        guard workObservation != nil, waitingForPhotoWork, !PhotoWorkSlot.process.occupied else { return }
        waitingForPhotoWork = false
        status = "The previous photo has finished. Choose a photo."
    }
    func clear() { stopWatchdog(); run.clear(); resetDetails() }
    func select() -> PhotoReviewRun.Token? {
        guard !PhotoWorkSlot.process.occupied else {
            showBusy(); return nil
        }
        stopWatchdog(); resetDetails(); return run.select()
    }
    func isSelecting(_ token: PhotoReviewRun.Token) -> Bool { run.isSelecting(token) }
    func cancelSelection(_ token: PhotoReviewRun.Token) {
        guard run.isSelecting(token), run.cancel(token) else { return }
        stopWatchdog(); resetDetails()
    }
    private func showEnd(_ token: PhotoReviewRun.Token) {
        guard let reason = run.endReason(token) else { return }
        stopWatchdog(); hints = TVPhotoHints("")
        status = reason == .timeLimit ? "Photo review timed out. Choose the picture again."
            : "Photo review ended. Choose the picture again."
    }
    func checkDeadline() {
        if let token = readingToken, !run.isReading(token) { showEnd(token) }
    }
    func beginReading(_ token: PhotoReviewRun.Token) -> PhotoReadWork? {
        guard run.isSelecting(token) else { return nil }
        guard let lease = PhotoWorkSlot.process.acquire() else {
            _ = run.cancel(token); stopWatchdog(); hints = TVPhotoHints("")
            showBusy(); return nil
        }
        let work = PhotoReadWork(lease)
        guard run.beginReading(token) else { showEnd(token); return nil }
        status = "Reading text on this phone…"
        stopWatchdog(); readingToken = token
        let watch = Timer(timeInterval: 0.25, repeats: true) { [weak self] _ in
            DispatchQueue.main.async { [weak self] in self?.checkDeadline() }
        }
        timer = watch; RunLoop.main.add(watch, forMode: .common)
        return work
    }
    private func canRead(_ token: PhotoReviewRun.Token) -> Bool {
        guard run.isReading(token) else { showEnd(token); return false }
        return true
    }
    private func finish(_ token: PhotoReviewRun.Token, hints: TVPhotoHints = TVPhotoHints(""), message: String) {
        guard run.complete(token) else { showEnd(token); return }
        waitingForPhotoWork = false; stopWatchdog(); self.hints = hints; status = message
    }
    func unreadable(_ token: PhotoReviewRun.Token) {
        finish(token, message: "Photo could not be read. Try another picture.")
    }
    func scan(_ image: UIImage, for token: PhotoReviewRun.Token, work: PhotoReadWork) {
        defer { withExtendedLifetime(work) {} }
        // The accepted selection already owns its import/recognition window.
        guard canRead(token) else { return }
        let scale = min(1, 2048 / max(image.size.width, image.size.height))
        let size = CGSize(width: max(1, image.size.width * scale), height: max(1, image.size.height * scale))
        let format = UIGraphicsImageRendererFormat(); format.scale = 1
        let small = UIGraphicsImageRenderer(size: size, format: format).image { _ in image.draw(in: CGRect(origin: .zero, size: size)) }
        guard canRead(token) else { return }
        guard let cg = small.cgImage else { unreadable(token); return }
        DispatchQueue.global(qos: .userInitiated).async {
            defer { withExtendedLifetime(work) {} }
            autoreleasepool {
                let request = VNRecognizeTextRequest(); request.recognitionLevel = .accurate; request.usesLanguageCorrection = false
                do {
                    try VNImageRequestHandler(cgImage: cg).perform([request])
                    let text = boundedTVPhotoText((request.results ?? []).lazy.map { $0.topCandidates(1).first?.string })
                    let hints = TVPhotoHints(text ?? "")
                    let message: String
                    if text == nil {
                        message = "Photo text could not be reviewed. Choose a closer photo of the model or IP address row."
                    } else if hints.brand == nil && hints.model == nil && hints.address == nil {
                        message = "No TV details found. Try a closer photo of the model label or IP address row."
                    } else {
                        message = "Check the details below. Text recognition can make mistakes. Nothing is connected."
                    }
                    DispatchQueue.main.async { [weak self] in
                        self?.finish(token, hints: hints, message: message)
                    }
                } catch {
                    DispatchQueue.main.async { [weak self] in
                        self?.finish(token, message: "Could not read this picture. Try brighter light and a closer photo.")
                    }
                }
            }
        }
    }
}

private struct PhotoPickerRequest: Identifiable {
    let id = UUID()
    let token: PhotoReviewRun.Token
    let camera: Bool
}

struct TVPhotoView: View {
    let theme: AppTheme
    var onUseBrand: ((String) -> Void)? = nil
    @Environment(\.dismiss) private var dismiss
    @Environment(\.scenePhase) private var phase
    @StateObject private var photo = PhotoCheck()
    @State private var pickerRequest: PhotoPickerRequest?
    @State private var instructions = false
    @State private var detailsExpanded = false
    @State private var setupRequest: SetupGuideRequest?
    @State private var showsVizioAddressPictures = false
    @State private var networkCheckVisible = false
    @State private var checkDraft: AQSSLocalTVTarget?
    @State private var cameraNotice = ""
    private var suggestedChoice: AQSSTutorialChoice? {
        guard let brand = photo.hints.brand?.lowercased() else { return nil }
        return AQSSTutorialContent.choices["chooseTV"]?.first { $0.id == brand }
    }
    var body: some View {
        VStack {
            HStack { Text("TV photo setup").font(.title2.bold()); Spacer(); RoseButton(title: "Close", theme: theme) { photo.clear(); dismiss() } }.padding()
            ScrollView {
                VStack(alignment: .leading, spacing: 18) {
                    Image(systemName: "tv").font(.system(size: 42)).foregroundColor(theme.violet).accessibilityHidden(true)
                    Text("Find your TV details").font(.title.bold())
                    Text("Photograph your TV’s model label, About screen, or IP address row. Keep passwords out of the picture.")
                    Button("Take a TV photo") { choosePhoto(camera: true) }.buttonStyle(AppButtonStyle(theme: theme, primary: true))
                    Button("Choose a photo") { choosePhoto(camera: false) }.buttonStyle(AppButtonStyle(theme: theme))
                    if !cameraNotice.isEmpty { Text(cameraNotice).foregroundColor(theme.warning) }
                    Text(photo.status).font(.headline).accessibilityIdentifier("photo-status")
                    if let brand = photo.hints.brand { Text("Brand: " + brand).font(.headline) }
                    if let choice = suggestedChoice, let onUseBrand = onUseBrand {
                        Button("Use \(choice.title) and continue") { onUseBrand(choice.id); photo.clear(); dismiss() }
                            .buttonStyle(AppButtonStyle(theme: theme, primary: true))
                            .accessibilityIdentifier("photo-use-brand")
                    }
                    if onUseBrand == nil, let target = photo.hints.vizioCheckTarget {
                        Text("Address read from photo: \(target.address)").monospacedDigit()
                        Text("Compare this address with your VIZIO TV’s network screen.")
                        Button("Use address in VIZIO check") {
                            guard phase == .active, !networkCheckVisible else { return }
                            checkDraft = target
                            networkCheckVisible = true
                        }.buttonStyle(AppButtonStyle(theme: theme, primary: true))
                            .accessibilityIdentifier("photo-use-vizio-address")
                    }
                    if detailsExpanded {
                        Text("Model: \(photo.hints.model ?? "Not identified")")
                        Text("TV IP hint: \(photo.hints.address ?? "Not identified")")
                    }
                    Text("Check the suggested details on your TV. A photo does not connect it. Choosing another picture clears these details.").font(.caption).foregroundColor(theme.muted)
                    Button(instructions ? "? Hide photo help" : "? Photo help") { instructions.toggle() }.buttonStyle(AppButtonStyle(theme: theme)).accessibilityIdentifier("photo-help")
                    if instructions {
                        if onUseBrand == nil && TVCheckPictureGuide.Context.photoSetup.route != nil {
                            Button("VIZIO V505M-K09 address pictures") { showsVizioAddressPictures = true }
                                .buttonStyle(AppButtonStyle(theme: theme))
                        }
                        Text("1. On your TV, open Settings. Look for About, Support or Device information to find the model. Menu names differ by TV.")
                        Text("2. Look for Network, Connection or Network status, then IP settings. Photograph the row labeled IP address — not Gateway or DNS. A label on the back usually does not show the current IP address.")
                        Text("3. Put your phone and TV on the same home Wi-Fi. Avoid a guest network. An IP address can change and does not prove which TV owns it.")
                        Text("4. For Samsung, supported models use SmartThings and may ask you to approve on the TV. For Alexa or Google Home, add/link a supported TV in that app and follow its approval steps. Compatibility varies by model.")
                    }
                    if instructions {
                        Button(detailsExpanded ? "Hide photo details" : "Show photo details") { detailsExpanded.toggle() }.buttonStyle(AppButtonStyle(theme: theme))
                        Button("Jump to illustrated setup guides") { setupRequest = SetupGuideRequest(group: photo.hints.brand?.lowercased() ?? "") }.buttonStyle(AppButtonStyle(theme: theme))
                        Button("Clear photo details") { photo.clear() }.buttonStyle(AppButtonStyle(theme: theme))
                        Text("Text recognition stays on this phone. Details clear on close. Your original photo remains in Photos.").font(.caption).foregroundColor(theme.muted)
                    }
                }.padding()
            }.accessibilityIdentifier("photo-review-scroll")
        }.background(theme.background.ignoresSafeArea()).foregroundColor(theme.text)
            .sheet(item: $setupRequest) { request in SetupGuidesView(theme: theme, initialGroup: request.group) }
            .sheet(isPresented: $showsVizioAddressPictures) {
                if TVCheckPictureGuide.Context.photoSetup.route != nil {
                    TVCheckPictureGuide(theme: theme, context: .photoSetup) {
                        showsVizioAddressPictures = false
                    }
                }
            }
            .sheet(isPresented: $networkCheckVisible, onDismiss: { checkDraft = nil }) {
                TVNetworkCheckView(theme: theme, takePhotoTarget: {
                    defer { checkDraft = nil }
                    return checkDraft
                })
            }
            .sheet(item: $pickerRequest) { request in
                Group {
                    if request.camera { LocalCameraPicker { finishPhoto($0, request: request) } }
                    else { LocalPhotoPicker(beginImport: { beginPhotoImport(request) }) { image, work in finishPhoto(image, request: request, work: work) } }
                }.onDisappear { photo.cancelSelection(request.token) }
            }
            .onAppear { photo.observeWork() }
            .onDisappear { photo.stopObservingWork(); photo.clear() }
            .onChange(of: phase) { value in
                if value == .active { photo.checkDeadline(); photo.observeWork() }
                else { checkDraft = nil; photo.stopObservingWork() }
            }
    }
    private func choosePhoto(camera: Bool) {
        guard let token = photo.select() else { return }
        cameraNotice = ""
        guard camera else { pickerRequest = PhotoPickerRequest(token: token, camera: false); return }
        guard UIImagePickerController.isSourceTypeAvailable(.camera) else {
            photo.cancelSelection(token)
            cameraNotice = "Camera unavailable here. Take a photo with your phone and choose it below."; return
        }
        AVCaptureDevice.requestAccess(for: .video) { allowed in DispatchQueue.main.async {
            guard photo.isSelecting(token) else { return }
            if allowed { pickerRequest = PhotoPickerRequest(token: token, camera: true) }
            else {
                photo.cancelSelection(token)
                cameraNotice = "Camera permission denied. Choose an existing photo or use the instructions."
            }
        } }
    }
    private func beginPhotoImport(_ request: PhotoPickerRequest) -> PhotoReadWork? {
        guard pickerRequest?.id == request.id, photo.isSelecting(request.token) else { return nil }
        let work = photo.beginReading(request.token)
        // Dismiss before provider loading: retry remains visible if it stalls.
        pickerRequest = nil; return work
    }
    private func finishPhoto(_ image: UIImage?, request: PhotoPickerRequest, work: PhotoReadWork? = nil) {
        var read = work
        if photo.isSelecting(request.token) {
            // The camera supplies an image here. Gallery loading has already
            // accepted its selection and dismissed the picker before this call.
            guard pickerRequest?.id == request.id else { photo.cancelSelection(request.token); return }
            guard image != nil else { pickerRequest = nil; photo.cancelSelection(request.token); return }
            read = beginPhotoImport(request)
        }
        guard let read = read else { return }
        defer { withExtendedLifetime(read) {} }
        if let image = image { photo.scan(image, for: request.token, work: read) }
        else { photo.unreadable(request.token) }
    }
}

private struct LocalPhotoPicker: UIViewControllerRepresentable {
    let beginImport: () -> PhotoReadWork?
    let finished: (UIImage?, PhotoReadWork?) -> Void
    func makeCoordinator() -> Coordinator { Coordinator(beginImport, finished) }
    func makeUIViewController(context: Context) -> PHPickerViewController {
        var config = PHPickerConfiguration(); config.filter = .images; config.selectionLimit = 1
        let picker = PHPickerViewController(configuration: config); picker.delegate = context.coordinator; return picker
    }
    func updateUIViewController(_ controller: PHPickerViewController, context: Context) {}
    final class Coordinator: NSObject, PHPickerViewControllerDelegate {
        let finished: (UIImage?, PhotoReadWork?) -> Void
        let beginImport: () -> PhotoReadWork?
        init(_ beginImport: @escaping () -> PhotoReadWork?, _ finished: @escaping (UIImage?, PhotoReadWork?) -> Void) {
            self.beginImport = beginImport; self.finished = finished
        }
        func picker(_ picker: PHPickerViewController, didFinishPicking results: [PHPickerResult]) {
            guard let provider = results.first?.itemProvider else { finished(nil, nil); return }
            guard let work = beginImport() else { return }
            provider.loadFileRepresentation(forTypeIdentifier: "public.image") { url, _ in
                defer { withExtendedLifetime(work) {} }
                var image: UIImage?
                autoreleasepool {
                    if let url = url, let source = CGImageSourceCreateWithURL(url as CFURL, nil), let cg = CGImageSourceCreateThumbnailAtIndex(source, 0, [kCGImageSourceCreateThumbnailFromImageAlways: true, kCGImageSourceThumbnailMaxPixelSize: 2048, kCGImageSourceCreateThumbnailWithTransform: true] as CFDictionary) { image = UIImage(cgImage: cg) }
                }
                let importedImage = image
                DispatchQueue.main.async { self.finished(importedImage, work) }
            }
        }
    }
}
private struct LocalCameraPicker: UIViewControllerRepresentable {
    let finished: (UIImage?) -> Void
    func makeCoordinator() -> Coordinator { Coordinator(finished) }
    func makeUIViewController(context: Context) -> UIImagePickerController {
        let picker = UIImagePickerController(); picker.sourceType = .camera; picker.delegate = context.coordinator; return picker
    }
    func updateUIViewController(_ controller: UIImagePickerController, context: Context) {}
    final class Coordinator: NSObject, UIImagePickerControllerDelegate, UINavigationControllerDelegate {
        let finished: (UIImage?) -> Void
        init(_ finished: @escaping (UIImage?) -> Void) { self.finished = finished }
        func imagePickerControllerDidCancel(_ picker: UIImagePickerController) { finished(nil) }
        func imagePickerController(_ picker: UIImagePickerController, didFinishPickingMediaWithInfo info: [UIImagePickerController.InfoKey: Any]) { finished(info[.originalImage] as? UIImage) }
    }
}
