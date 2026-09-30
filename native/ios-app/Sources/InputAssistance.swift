import AVFoundation
import Speech
import SwiftUI
import Vision
import PhotosUI
import ImageIO

/// Foreground input only. Recognition results never enter an output control path.
@MainActor
final class VoiceCheck: ObservableObject {
    @Published var status = "Microphone off"
    @Published var transcript = ""
    @Published var levels: [Double] = []
    @Published var levelText = "No microphone samples yet"
    @Published var running = false
    private let engine = AVAudioEngine()
    private var task: SFSpeechRecognitionTask?
    private var request: SFSpeechAudioBufferRecognitionRequest?
    private var generation = 0
    private var tapped = false
    private var timeout: DispatchWorkItem?

    func start() {
        stop(); transcript = ""; levels = []; levelText = "No microphone samples yet"
        generation += 1; let token = generation
        running = true; status = "Requesting microphone permission"
        AVAudioSession.sharedInstance().requestRecordPermission { [weak self] allowed in
            DispatchQueue.main.async {
                guard let self = self, self.generation == token else { return }
                guard allowed else { self.stop("Microphone permission denied. You can change this in iPhone Settings."); return }
                SFSpeechRecognizer.requestAuthorization { authorization in
                    DispatchQueue.main.async {
                        guard self.generation == token else { return }
                        guard authorization == .authorized else { self.stop("Speech permission unavailable. No audio is being captured."); return }
                        self.begin(token)
                    }
                }
            }
        }
    }
    private func begin(_ token: Int) {
        guard UIApplication.shared.applicationState == .active else { stop("Tap Start again when the app is active."); return }
        guard let recognizer = SFSpeechRecognizer(), recognizer.isAvailable, recognizer.supportsOnDeviceRecognition else {
            stop("On-device speech recognition is unavailable for this language or device. No cloud fallback is used."); return
        }
        do {
            let session = AVAudioSession.sharedInstance()
            try session.setCategory(.record, mode: .measurement, options: [])
            try session.setActive(true)
            let input = engine.inputNode
            let format = input.outputFormat(forBus: 0)
            guard format.sampleRate > 0, format.channelCount > 0 else { stop("No microphone input is available."); return }
            let req = SFSpeechAudioBufferRecognitionRequest()
            req.requiresOnDeviceRecognition = true; req.shouldReportPartialResults = true; request = req
            var lastUpdate = 0.0
            input.installTap(onBus: 0, bufferSize: 1024, format: format) { [weak self] buffer, _ in
                req.append(buffer)
                let now = ProcessInfo.processInfo.systemUptime
                guard now - lastUpdate >= 0.1, let data = buffer.floatChannelData?[0], buffer.frameLength > 0 else { return }
                lastUpdate = now
                var sum = 0.0
                for i in 0..<Int(buffer.frameLength) { let sample = Double(data[i]); sum += sample * sample }
                let db = max(-80.0, min(0.0, 20 * log10(max(0.0001, sqrt(sum / Double(buffer.frameLength))))))
                guard db.isFinite else { return }
                DispatchQueue.main.async {
                    guard let self = self, self.generation == token, self.running else { return }
                    self.levels.append((db + 80) / 80); self.levels = Array(self.levels.suffix(40))
                    self.levelText = String(format: "Microphone input: %.0f dBFS", db)
                }
            }
            tapped = true
            task = recognizer.recognitionTask(with: req) { [weak self] result, error in
                DispatchQueue.main.async {
                    guard let self = self, self.generation == token, self.running else { return }
                    if let result = result { self.transcript = String(result.bestTranscription.formattedString.suffix(500)) }
                    if result?.isFinal == true { self.stop("Finished — review the recognized words. Nothing was sent to a TV.") }
                    else if error != nil { self.stop("Speech recognition stopped. The words shown may be incomplete.") }
                }
            }
            engine.prepare(); try engine.start(); status = "Listening — on this phone, up to 30 seconds"
            let expiry = DispatchWorkItem { [weak self] in
                guard let self = self, self.generation == token else { return }
                self.stop("30-second limit reached. Tap Start to try again.")
            }
            timeout = expiry; DispatchQueue.main.asyncAfter(deadline: .now() + 30, execute: expiry)
        } catch { stop("Microphone could not start. Close other recording apps and try again.") }
    }
    func stop(_ message: String = "Microphone off") {
        generation += 1; running = false; timeout?.cancel(); timeout = nil
        engine.stop()
        if tapped { engine.inputNode.removeTap(onBus: 0); tapped = false }
        request?.endAudio(); task?.cancel(); task = nil; request = nil
        try? AVAudioSession.sharedInstance().setActive(false, options: .notifyOthersOnDeactivation)
        levels = []; levelText = "No live microphone samples"; status = message
    }
    func clear() { stop(); transcript = "" }
}

struct VoiceCheckView: View {
    let theme: AppTheme
    @Environment(\.dismiss) private var dismiss
    @Environment(\.scenePhase) private var phase
    @StateObject private var voice = VoiceCheck()
    @State private var setupVisible = false
    var body: some View {
        VStack(spacing: 12) {
            HStack { Text("Voice check").font(.title2.bold()); Spacer(); Button("Close") { voice.clear(); dismiss() }.buttonStyle(AppButtonStyle(theme: theme)) }.padding()
            ScrollView {
                VStack(alignment: .leading, spacing: 18) {
                    Text("See what your phone hears").font(.title.bold())
                    Button("Help · show voice steps") { voice.clear(); setupVisible = true }.buttonStyle(AppButtonStyle(theme: theme))
                    Text("Tap Start, then say: ‘Make the TV quieter.’ The bars show incoming sound. The text shows the words the phone thinks you said. This check does not send a command.")
                    Text(voice.status).font(.headline).accessibilityIdentifier("voice-status")
                    GeometryReader { box in
                        HStack(alignment: .center, spacing: 2) {
                            ForEach(0..<40, id: \.self) { index in
                                let offset = index - (40 - voice.levels.count)
                                let level = offset >= 0 ? voice.levels[offset] : 0
                                RoundedRectangle(cornerRadius: 2).fill(theme.violet)
                                    .frame(width: max(1, (box.size.width - 78) / 40), height: max(2, box.size.height * level))
                            }
                        }.frame(height: box.size.height)
                    }.frame(height: 120).accessibilityHidden(true)
                    Text(voice.levelText).foregroundColor(theme.muted)
                    Text("Sound-level history, oldest to newest. dBFS is a digital input level, not room loudness or a hearing-safety measurement. Bars are not frequency bands or a syllable count.").font(.caption).foregroundColor(theme.muted)
                    Text("Recent recognized words · may change").font(.headline)
                    Text(voice.transcript.isEmpty ? "No words recognized yet" : voice.transcript).accessibilityIdentifier("voice-transcript")
                    Text("Noise, accents and overlapping voices can cause missing or incorrect words. A moving meter does not prove every word or sound was understood.").foregroundColor(theme.muted)
                    Text("On-device recognition only. No audio file is saved. Closing this screen clears the words. Listening stops when you leave the app. Camera, microphone and speech features may be unavailable in browser simulators.").font(.caption).foregroundColor(theme.muted)
                }.padding()
            }
            HStack {
                Button(voice.running ? "Stop listening" : "Start voice check") { if voice.running { voice.stop() } else { voice.start() } }.buttonStyle(AppButtonStyle(theme: theme, primary: true)).accessibilityIdentifier("voice-start-stop")
                Button("Clear words") { voice.clear() }.buttonStyle(AppButtonStyle(theme: theme))
            }.padding()
        }.background(theme.background.ignoresSafeArea()).foregroundColor(theme.text)
            .sheet(isPresented: $setupVisible) { SetupGuidesView(theme: theme, initialGroup: "voice", onVoiceCheck: {}) }
            .onChange(of: phase) { if $0 == .background { voice.clear() } }
            .onReceive(NotificationCenter.default.publisher(for: AVAudioSession.interruptionNotification)) { _ in voice.stop("Audio interrupted — tap Start to try again.") }
            .onDisappear { voice.clear() }
    }
}

@MainActor
final class PhotoCheck: ObservableObject {
    @Published var hints = TVPhotoHints("")
    @Published var status = "No photo selected"
    private var generation = 0
    func clear() { generation += 1; hints = TVPhotoHints(""); status = "No photo selected" }
    func scan(_ image: UIImage) {
        clear(); status = "Reading text on this phone…"; let token = generation
        // Always normalize orientation and bound the bitmap before OCR.
        let scale = min(1, 2048 / max(image.size.width, image.size.height))
        let size = CGSize(width: max(1, image.size.width * scale), height: max(1, image.size.height * scale))
        let format = UIGraphicsImageRendererFormat(); format.scale = 1
        let small = UIGraphicsImageRenderer(size: size, format: format).image { _ in image.draw(in: CGRect(origin: .zero, size: size)) }
        guard let cg = small.cgImage else { status = "Photo could not be read. Try another picture."; return }
        DispatchQueue.global(qos: .userInitiated).async {
            let request = VNRecognizeTextRequest(); request.recognitionLevel = .accurate; request.usesLanguageCorrection = false
            do {
                try VNImageRequestHandler(cgImage: cg).perform([request])
                let lines = (request.results ?? []).prefix(100).compactMap { $0.topCandidates(1).first?.string }
                let text = lines.joined(separator: "\n")
                let hints = TVPhotoHints(text)
                DispatchQueue.main.async { [weak self] in
                    guard let self = self, self.generation == token else { return }
                    self.hints = hints
                    self.status = "Check the details below. Text recognition can make mistakes. Nothing is connected."
                }
            } catch {
                DispatchQueue.main.async { [weak self] in
                    guard let self = self, self.generation == token else { return }
                    self.status = "Could not read this picture. Try brighter light and a closer photo."
                }
            }
        }
    }
}

struct TVPhotoView: View {
    let theme: AppTheme
    @Environment(\.dismiss) private var dismiss
    @StateObject private var photo = PhotoCheck()
    @State private var gallery = false
    @State private var camera = false
    @State private var instructions = false
    @State private var setupRequest: SetupGuideRequest?
    @State private var cameraNotice = ""
    var body: some View {
        VStack {
            HStack { Text("TV photo setup").font(.title2.bold()); Spacer(); Button("Close") { photo.clear(); dismiss() }.buttonStyle(AppButtonStyle(theme: theme)) }.padding()
            ScrollView {
                VStack(alignment: .leading, spacing: 18) {
                    Image(systemName: "tv").font(.system(size: 42)).foregroundColor(theme.violet).accessibilityHidden(true)
                    Text("Find your TV details").font(.title.bold())
                    Text("Take a clear picture of the TV’s model label, or its Network / IP settings screen. Avoid including passwords. You do not need to move a heavy or wall-mounted TV: use its About screen instead.")
                    Button("Take a TV photo") {
                        guard UIImagePickerController.isSourceTypeAvailable(.camera) else { cameraNotice = "Camera unavailable here. Take a photo with your phone and choose it below."; return }
                        AVCaptureDevice.requestAccess(for: .video) { allowed in DispatchQueue.main.async {
                            if allowed { camera = true } else { cameraNotice = "Camera permission denied. Choose an existing photo or use the instructions." }
                        } }
                    }.buttonStyle(AppButtonStyle(theme: theme, primary: true))
                    Button("Choose a photo") { gallery = true }.buttonStyle(AppButtonStyle(theme: theme))
                    if !cameraNotice.isEmpty { Text(cameraNotice).foregroundColor(theme.warning) }
                    Text(photo.status).font(.headline).accessibilityIdentifier("photo-status")
                    Text("Brand: \(photo.hints.brand ?? "Not identified")")
                    Text("Model: \(photo.hints.model ?? "Not identified")")
                    Text("TV IP hint: \(photo.hints.address ?? "Not identified")")
                    Text("These are unverified hints. Only a clearly labeled, private IPv4 address is shown. We never use a photo as permission to control your TV.").font(.caption).foregroundColor(theme.muted)
                    Button("Illustrated setup guides") { setupRequest = SetupGuideRequest(group: photo.hints.brand?.lowercased() ?? "") }.buttonStyle(AppButtonStyle(theme: theme))
                    Button(instructions ? "Hide connection instructions" : "Show connection instructions") { instructions.toggle() }.buttonStyle(AppButtonStyle(theme: theme))
                    if instructions {
                        Text("1. On your TV, open Settings. Look for About, Support or Device information to find the model. Menu names differ by TV.")
                        Text("2. Look for Network, Connection or Network status, then IP settings. Photograph the row labeled IP address — not Gateway or DNS. A label on the back usually does not show the current IP address.")
                        Text("3. Put your phone and TV on the same home Wi-Fi. Avoid a guest network. An IP address can change and does not prove which TV owns it.")
                        Text("4. For Samsung, supported models use SmartThings and may ask you to approve on the TV. For Alexa or Google Home, add/link a supported TV in that app and follow its approval steps. Compatibility varies by model.")
                        Text("AQSS pairing is not available yet. This tool reads the photo and helps you prepare; it does not connect or change the TV.").font(.headline).foregroundColor(theme.warning)
                    }
                    Button("Clear photo details") { photo.clear() }.buttonStyle(AppButtonStyle(theme: theme))
                    Text("Text recognition runs on this phone. AQSS does not save or upload the picture, serial number or password. Your original photo may remain in your Photos app. Details are cleared when this screen closes.").font(.caption).foregroundColor(theme.muted)
                }.padding()
            }
        }.background(theme.background.ignoresSafeArea()).foregroundColor(theme.text)
            .sheet(item: $setupRequest) { request in SetupGuidesView(theme: theme, initialGroup: request.group) }
            .sheet(isPresented: $gallery) { LocalPhotoPicker { image in gallery = false; if let image = image { photo.scan(image) } } }
            .sheet(isPresented: $camera) { LocalCameraPicker { image in camera = false; if let image = image { photo.scan(image) } } }
            .onDisappear { photo.clear() }
    }
}

private struct LocalPhotoPicker: UIViewControllerRepresentable {
    let finished: (UIImage?) -> Void
    func makeCoordinator() -> Coordinator { Coordinator(finished) }
    func makeUIViewController(context: Context) -> PHPickerViewController {
        var config = PHPickerConfiguration(); config.filter = .images; config.selectionLimit = 1
        let picker = PHPickerViewController(configuration: config); picker.delegate = context.coordinator; return picker
    }
    func updateUIViewController(_ controller: PHPickerViewController, context: Context) {}
    final class Coordinator: NSObject, PHPickerViewControllerDelegate {
        let finished: (UIImage?) -> Void
        init(_ finished: @escaping (UIImage?) -> Void) { self.finished = finished }
        func picker(_ picker: PHPickerViewController, didFinishPicking results: [PHPickerResult]) {
            guard let provider = results.first?.itemProvider else { finished(nil); return }
            provider.loadFileRepresentation(forTypeIdentifier: "public.image") { url, _ in
                var image: UIImage?
                if let url = url, let source = CGImageSourceCreateWithURL(url as CFURL, nil), let cg = CGImageSourceCreateThumbnailAtIndex(source, 0, [kCGImageSourceCreateThumbnailFromImageAlways: true, kCGImageSourceThumbnailMaxPixelSize: 2048, kCGImageSourceCreateThumbnailWithTransform: true] as CFDictionary) { image = UIImage(cgImage: cg) }
                DispatchQueue.main.async { self.finished(image) }
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
