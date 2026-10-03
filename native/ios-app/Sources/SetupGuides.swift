import SwiftUI

struct SetupGuideRequest: Identifiable {
    let id = UUID()
    let group: String
}

/// Local, illustrative instructions. No device session, credentials or control API.
struct SetupGuidesView: View {
    private static let repeatedPictureNotes: Set<String> = [
        "Use your real device. This picture is an illustration.",
        "Finishing this guide does not connect Audio Bodyguard or activate protection.",
        "Use the numbered highlight on your real device. This illustration does not confirm a connection to Audio Bodyguard."
    ]
    let theme: AppTheme
    let initialGroup: String
    var onVoiceCheck: (() -> Void)? = nil
    var onPartOne: ((String) -> Void)? = nil
    var onFinish: ((String) -> Void)? = nil
    @Environment(\.dismiss) private var dismiss
    @Environment(\.dynamicTypeSize) private var textSize
    @State private var groupID = ""
    @State private var routeID: String?
    @State private var index = -1
    @State private var mismatch = false
    @State private var initialized = false
    @State private var detailsExpanded = false
    @StateObject private var progress = SetupProgressStore()
    @AccessibilityFocusState private var headingFocused: String?
    private var group: AQSSSetupGroup? { AQSSSetupContent.groups.first { $0.id == groupID } }
    private var route: AQSSSetupRoute? { AQSSSetupContent.routes.first { $0.id == routeID } }
    private var step: AQSSSetupStep? { guard let route = route, route.steps.indices.contains(index) else { return nil }; return route.steps[index] }
    private var key: String { "\(groupID)-\(routeID ?? "")-\(index)-\(mismatch)" }
    private var title: String { mismatch ? "My screen looks different" : step?.title ?? route?.title ?? (group == nil ? "Choose your TV or app" : "Match your model or menu") }

    var body: some View {
        VStack(spacing: 0) {
            VStack(spacing: 10) {
                HStack {
                    if let route = route, index >= 0 {
                        Text(textSize.isAccessibilitySize ? "\(index + 1) / \(route.steps.count)" : "Step \(index + 1) of \(route.steps.count)")
                            .font(.headline).accessibilityLabel("Step \(index + 1) of \(route.steps.count)").accessibilityIdentifier("setup-progress")
                    } else { Label("Illustrated setup", systemImage: "rectangle.stack").font(.headline) }
                    Spacer(minLength: 8)
                    Button { dismiss() } label: { navigationLabel("Close", icon: "xmark") }
                        .buttonStyle(AppButtonStyle(theme: theme)).accessibilityIdentifier("setup-close")
                }
                if let route = route, index >= 0 {
                    ProgressView(value: Double(index + 1), total: Double(route.steps.count)).tint(theme.accent).accessibilityHidden(true)
                }
            }.padding(16).background(theme.surface)
            GuideScrollView(screenKey: key, identifier: "setup-scroll", onStepReady: { key in headingFocused = key }) {
                VStack(alignment: .leading, spacing: 18) {
                    Text(title).font(.title.bold()).fixedSize(horizontal: false, vertical: true)
                        .accessibilityAddTraits(.isHeader).accessibilityFocused($headingFocused, equals: key)
                    if mismatch { mismatchContent }
                    else if let route = route {
                        if let step = step {
                            Label(step.surface == "tv" ? "On your TV · use the remote" : step.surface == "both" ? "Your TV + your phone" : "On your phone", systemImage: step.surface == "phone" ? "iphone" : "tv")
                                .font(.subheadline.weight(.semibold)).foregroundColor(theme.accent)
                            Text(step.instruction).font(.body.weight(.medium)).fixedSize(horizontal: false, vertical: true)
                            if route.id == "roku_network" || route.id == "roku_model" {
                                RokuMenuIllustration(step: step, number: index + 1, theme: theme)
                            } else if route.id == "philips_voice_remote" && [1, 2].contains(index) {
                                ProfileMenuIllustration(step: step, number: index + 1, theme: theme)
                            } else { SetupScreenIllustration(step: step, number: index + 1, theme: theme) }
                            if !Self.repeatedPictureNotes.contains(step.note) {
                                Text(step.note).font(.callout).foregroundColor(theme.muted)
                            }
                            control("My screen looks different", icon: "questionmark.circle", id: "setup-mismatch") { mismatch = true }
                        } else { introduction(route) }
                    } else if groupID == "tcl" {
                        Text("Which home screen is on your TCL TV?").font(.headline)
                        Text("Choose the name or menu that matches your TV. If your screen says Roku like the blue Settings photo, choose Roku TV.").foregroundColor(theme.muted)
                        platformChoice("Roku TV", subtitle: "Roku name · left menu and right panel", group: "tcl_roku", blue: true)
                        platformChoice("Google TV / Android TV", subtitle: "Google name · app tiles and a settings gear", group: "tcl_google", blue: false)
                        platformChoice("Fire TV", subtitle: "Fire TV name · Amazon account", group: "tcl_fire", blue: false)
                    }
                    else if let group = group {
                        Text(group.title).font(.title3.weight(.semibold)).foregroundColor(theme.accent)
                        Text("Match the setup screen and exact TV model before following the pictures.").foregroundColor(theme.muted)
                        ForEach(group.routes, id: \.self) { id in
                            if let route = AQSSSetupContent.routes.first(where: { $0.id == id }) {
                                control(route.title, icon: "rectangle.stack", id: "setup-route-\(id)") { routeID = id; index = -1 }
                            }
                        }
                    } else {
                        Text("Follow one picture at a time. The numbered arrow marks the next choice; TV, remote and phone symbols show which device to use.").foregroundColor(theme.muted)
                        ForEach(AQSSSetupContent.groups.filter { !["both", "neither"].contains($0.id) && !$0.id.hasPrefix("tcl_") }, id: \.id) { item in
                            control(item.title, icon: item.id == "voice" ? "mic" : ["google", "alexa"].contains(item.id) ? "house" : "tv", id: "setup-group-\(item.id)") { chooseGroup(item.id) }
                        }
                    }
                }.frame(maxWidth: 620, alignment: .leading).padding(20).frame(maxWidth: .infinity)
            }
            footer
        }.background(theme.background.ignoresSafeArea()).foregroundColor(theme.text)
            .onAppear { if !initialized { initialized = true; chooseGroup(initialGroup) } }
            .onChange(of: index) { value in
                if let route = route, route.id != "voice", route.steps.indices.contains(value) { writeProgress(route.id, value) }
            }
    }

    private func platformChoice(_ title: String, subtitle: String, group: String, blue: Bool) -> some View {
        Button { chooseGroup(group) } label: {
            HStack(spacing: 14) {
                VStack(alignment: .leading, spacing: 3) {
                    Image(systemName: "tv").font(.title2)
                    ForEach(0..<3) { n in Capsule().fill(n == 0 ? Color.white : Color.white.opacity(0.35)).frame(width: n == 0 ? 40 : 28, height: 3) }
                }.foregroundColor(.white).padding(10).background(blue ? Color.blue : theme.violet).clipShape(RoundedRectangle(cornerRadius: 8)).accessibilityHidden(true)
                VStack(alignment: .leading) { Text(title).font(.headline); Text(subtitle).font(.caption).foregroundColor(theme.muted) }
                Spacer(minLength: 0); Image(systemName: "chevron.right").accessibilityHidden(true)
            }.frame(maxWidth: .infinity, minHeight: 64, alignment: .leading)
        }.buttonStyle(AppButtonStyle(theme: theme)).accessibilityIdentifier("setup-platform-\(group)")
    }

    private func resumeIndex(_ route: AQSSSetupRoute) -> Int? { progress.resumeIndex(route.id) }
    private func writeProgress(_ id: String, _ value: Int?) { progress.record(id, value) }
    private func chooseGroup(_ id: String) {
        groupID = AQSSSetupContent.groups.contains { $0.id == id } ? id : ""
        routeID = groupID == "voice" ? "voice" : nil
        index = groupID == "voice" ? 0 : -1
        mismatch = false
        detailsExpanded = false
    }
    private func control(_ title: String, icon: String, id: String, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            HStack(alignment: .center, spacing: 12) {
                if !textSize.isAccessibilitySize { Image(systemName: icon).accessibilityHidden(true) }
                Text(title).fixedSize(horizontal: false, vertical: true)
                Spacer(minLength: 0)
                if !textSize.isAccessibilitySize { Image(systemName: "chevron.right").accessibilityHidden(true) }
            }.frame(maxWidth: .infinity, minHeight: 44, alignment: .leading)
        }.buttonStyle(AppButtonStyle(theme: theme)).accessibilityIdentifier(id)
    }
    @ViewBuilder private func navigationLabel(_ title: String, icon: String) -> some View {
        if textSize.isAccessibilitySize {
            Image(systemName: icon).font(.system(size: 28, weight: .semibold))
                .frame(minWidth: 44, minHeight: 44).accessibilityLabel(title)
        } else { Label(title, systemImage: icon) }
    }
    @ViewBuilder private func introduction(_ route: AQSSSetupRoute) -> some View {
        HStack(spacing: 20) { Image(systemName: "tv"); Image(systemName: "arrow.right"); Image(systemName: "iphone") }
            .font(.system(size: 36)).foregroundColor(theme.violet).accessibilityHidden(true)
        if route.id == "roku_network" || route.id == "roku_model" {
            control("I’m already in Settings", icon: "gearshape", id: "setup-skip-home") { index = 2 }
        }
        Text("Before you begin").font(.headline)
        Text(route.appliesTo)
        Text("\(route.steps.count) pictures · one action at a time").font(.headline).foregroundColor(theme.accent)
        Text("Use your TV maker’s app for passwords and approvals.").font(.callout)
        if let saved = resumeIndex(route) {
            Text("You stopped at picture \(saved + 1). Tap Resume guide to continue there.").foregroundColor(theme.accent)
            control("Start from the beginning", icon: "arrow.counterclockwise", id: "setup-restart") { writeProgress(route.id, nil); index = 0 }
        }
        Button { detailsExpanded.toggle() } label: {
            Label(detailsExpanded ? "Hide details" : "Details & official instructions", systemImage: detailsExpanded ? "chevron.up" : "chevron.down")
                .frame(maxWidth: .infinity, minHeight: 44, alignment: .leading)
        }.buttonStyle(AppButtonStyle(theme: theme)).accessibilityIdentifier("setup-details")
            .accessibilityValue(detailsExpanded ? "Expanded" : "Collapsed")
        if detailsExpanded {
            VStack(alignment: .leading, spacing: 14) {
                if !route.models.isEmpty {
                    Text("Documented model examples: \(route.models.joined(separator: ", "))").font(.callout)
                } else { Text("Menu-family guide · match your TV’s exact model.").font(.callout) }
                Text("Labels, layout and services can differ by country, software and language. Compare each picture with your own screen.").font(.callout)
                sources(route)
            }.foregroundColor(theme.muted).padding(.top, 12)
        }
        control("My screen looks different", icon: "questionmark.circle", id: "setup-mismatch") { mismatch = true }
    }
    @ViewBuilder private func sources(_ route: AQSSSetupRoute) -> some View {
        Text("Official instructions").font(.headline)
        ForEach(route.sources, id: \.self) { id in
            if let source = AQSSSetupContent.sources.first(where: { $0.id == id }), let url = URL(string: source.url) {
                Link(destination: url) { Label(source.title, systemImage: "arrow.up.right.square").frame(maxWidth: .infinity, alignment: .leading) }
                    .buttonStyle(AppButtonStyle(theme: theme))
            }
        }
    }
    private var mismatchContent: some View {
        VStack(alignment: .leading, spacing: 16) {
            Image(systemName: "tv.and.mediabox").font(.system(size: 40)).foregroundColor(theme.violet).accessibilityHidden(true)
            Text("Pause at this step. Check the full model, TV software and country. Look for the same menu meaning or icon in your language.")
            Text("If the option, TV or permission request is absent, use the manufacturer’s instructions below.")
            if let route = route { sources(route) }
            control("Choose another model or menu", icon: "rectangle.stack", id: "setup-other-menu") { routeID = nil; index = -1; mismatch = false }
            control("Choose another TV or app", icon: "tv", id: "setup-other-group") { chooseGroup("") }
            Text("You can close this guide at any time. Your current place is preserved while viewing this help.").foregroundColor(theme.muted)
        }
    }
    private var footer: some View {
        HStack(spacing: 12) {
            if group != nil || route != nil {
                Button { goBack() } label: { navigationLabel(mismatch ? "Return to step" : "Back", icon: "arrow.left") }
                    .buttonStyle(AppButtonStyle(theme: theme)).accessibilityIdentifier("setup-back")
            }
            if let route = route, !mismatch {
                let displayedIndex = index
                Button {
                    guard routeID == route.id, index == displayedIndex, !mismatch else { return }
                    if index == route.steps.count - 1 {
                        if ["roku_network", "roku_model"].contains(route.id) {
                            writeProgress(route.id, nil)
                            onPartOne?(route.id)
                            routeID = "roku_phone"; index = -1
                            return
                        }
                        if route.id == "voice" { onVoiceCheck?() }
                        else { onFinish?(route.id) }
                        writeProgress(route.id, nil)
                        dismiss()
                    } else if index < 0 { index = resumeIndex(route) ?? 0 }
                    else { index += 1 }
                } label: {
                    navigationLabel(index < 0 ? (resumeIndex(route) == nil ? (route.id == "roku_phone" ? "Start part two" : "Start guide") : "Resume guide") : index == route.steps.count - 1 ? (route.id == "voice" && onVoiceCheck != nil ? "Open Voice check" : ["roku_network", "roku_model"].contains(route.id) ? "Finish part one" : route.id == "roku_phone" ? "Finish part two" : "Finish guide") : "Next", icon: index == route.steps.count - 1 ? (route.id == "voice" && onVoiceCheck != nil ? "mic" : "checkmark") : "arrow.right")
                        .frame(maxWidth: .infinity, minHeight: 44)
                }.buttonStyle(AppButtonStyle(theme: theme, primary: true)).accessibilityIdentifier("setup-next")
            }
        }.padding(16).background(theme.surface)
    }
    private func goBack() {
        if mismatch { mismatch = false }
        else if index >= 0 { index -= 1 }
        else if routeID != nil { routeID = nil }
        else { groupID = groupID.hasPrefix("tcl_") ? "tcl" : "" }
    }
}

/// One decode per presented guide. Persistence never publishes a second
/// SwiftUI update after the navigation state has already changed.
private final class SetupProgressStore: ObservableObject {
    private let defaults: UserDefaults
    private var progress: AQSSSetupProgress
    init(defaults: UserDefaults = .standard) {
        self.defaults = defaults
        self.progress = AQSSSetupProgress(serialized: defaults.string(forKey: "aqssSetupProgressV1"))
    }
    func resumeIndex(_ id: String) -> Int? { progress.resumeIndex(id) }
    func record(_ id: String, _ value: Int?) {
        guard progress.record(id, value), let saved = progress.serialized() else { return }
        defaults.set(saved, forKey: "aqssSetupProgressV1")
    }
}

/// A scalable screen mock-up with a device frame, numbered target and action pictogram.
/// Text also has an accessible description; color is never the only instruction.
private struct SetupScreenIllustration: View {
    let step: AQSSSetupStep
    let number: Int
    let theme: AppTheme
    private var glyph: String {
        switch step.action {
        case "home": return "house.fill"
        case "settings": return "gearshape.fill"
        case "scan": return "camera.viewfinder"
        case "type": return "keyboard"
        case "check": return "eye"
        case "speak": return "mic.fill"
        case "stop": return "stop.fill"
        case "wait": return "hourglass"
        default: return step.surface == "tv" ? "arrow.up.and.down.and.arrow.left.and.right" : "hand.tap.fill"
        }
    }
    var body: some View {
        VStack(spacing: 10) {
            HStack { Text("Illustration").font(.caption2.weight(.semibold)); Spacer(); Image(systemName: step.surface == "phone" ? "iphone" : "tv") }.foregroundColor(theme.muted)
            if step.surface == "both" {
                HStack(spacing: 16) {
                    Image(systemName: "tv").font(.system(size: 34))
                    Image(systemName: step.action == "scan" ? "camera.viewfinder" : "arrow.right").font(.title2)
                    Image(systemName: "iphone").font(.system(size: 34))
                }.foregroundColor(theme.violet).padding(.vertical, 6)
            }
            VStack(spacing: 0) {
                if step.surface != "tv" {
                    HStack { Text("9:41"); Spacer(); Image(systemName: "wifi"); Image(systemName: "battery.100") }
                        .font(.caption2).padding(.horizontal, 16).padding(.top, 10).foregroundColor(theme.muted)
                }
                HStack {
                    Image(systemName: step.action == "settings" ? "gearshape" : step.surface == "tv" ? "tv" : "square.grid.2x2")
                    Text(step.screen).font(.headline).fixedSize(horizontal: false, vertical: true)
                    Spacer(minLength: 0)
                }.padding(14).foregroundColor(theme.text)
                Divider().overlay(theme.outline)
                VStack(spacing: 9) {
                    ForEach(Array(step.items.enumerated()), id: \.offset) { i, item in
                        HStack(alignment: .center, spacing: 8) {
                            if i == step.focus {
                                Text("\(number)").font(.caption.bold()).frame(minWidth: 26, minHeight: 26)
                                    .background(theme.controlText).foregroundColor(theme.control).clipShape(Circle())
                            } else { Image(systemName: "circle").frame(width: 26) }
                            Text(item).font(.subheadline.weight(i == step.focus ? .bold : .regular)).fixedSize(horizontal: false, vertical: true)
                            Spacer(minLength: 0)
                            Image(systemName: i == step.focus ? "arrow.left" : "chevron.right").font(.caption.bold())
                        }.padding(12).frame(maxWidth: .infinity, minHeight: 48, alignment: .leading)
                            .foregroundColor(i == step.focus ? theme.controlText : theme.muted)
                            .background(i == step.focus ? theme.control : theme.raised)
                            .clipShape(RoundedRectangle(cornerRadius: 9))
                            .overlay(RoundedRectangle(cornerRadius: 9).stroke(i == step.focus ? theme.controlBorder : theme.outline, lineWidth: i == step.focus ? 2 : 1))
                    }
                }.padding(12)
                if step.surface != "tv" { Capsule().fill(theme.muted).frame(width: 70, height: 4).padding(10) }
            }.background(theme.surface).clipShape(RoundedRectangle(cornerRadius: step.surface == "tv" ? 12 : 26))
                .overlay(RoundedRectangle(cornerRadius: step.surface == "tv" ? 12 : 26).stroke(theme.outline, lineWidth: 3))
                .padding(.horizontal, step.surface == "phone" ? 12 : 0)
            if step.surface == "tv" {
                VStack(spacing: 0) { Rectangle().fill(theme.outline).frame(width: 14, height: 12); Capsule().fill(theme.outline).frame(width: 90, height: 4) }
            }
            HStack(spacing: 20) {
                if step.surface == "tv" {
                    VStack(spacing: 6) {
                        HStack(spacing: 18) { Image(systemName: "house"); Image(systemName: "gearshape") }.font(.caption)
                        Image(systemName: "arrow.up.and.down.and.arrow.left.and.right").font(.title2)
                    }.padding(12).background(theme.raised).clipShape(RoundedRectangle(cornerRadius: 18))
                }
                Image(systemName: "arrow.right").font(.title2)
                Image(systemName: glyph).font(.system(size: 26)).frame(width: 54, height: 44).background(theme.control).foregroundColor(theme.controlText).clipShape(RoundedRectangle(cornerRadius: 14))
            }.foregroundColor(theme.violet).padding(.top, 4)
        }.padding(14).background(theme.raised.opacity(0.7)).clipShape(RoundedRectangle(cornerRadius: 22))
            .accessibilityElement(children: .ignore)
            .accessibilityLabel("Illustration \(number). \(step.surface == "tv" ? "TV screen" : step.surface == "both" ? "TV and phone" : "Phone screen"): \(step.screen). Highlighted: \(step.items[step.focus]). Action: \(step.action). \(step.instruction)")
            .accessibilityIdentifier("setup-illustration")
    }
}

/// Recreates the Roku left-menu / right-panel geometry visible in the supplied photo.
/// Background art and unknown device values are deliberately omitted.
private struct RokuMenuIllustration: View {
    let step: AQSSSetupStep
    let number: Int
    let theme: AppTheme
    private var about: Bool { number >= 4 }
    private var model: Bool { step.screen.contains("System") }
    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Picture \(number) · Roku menu layout").font(.caption).foregroundColor(theme.muted)
            if number == 1 {
                HStack(spacing: 20) {
                    Image(systemName: "appletvremote.gen1").font(.system(size: 58)).foregroundColor(theme.violet)
                    Label("Press Home", systemImage: "house.fill").padding(16).background(theme.control).foregroundColor(theme.controlText).clipShape(RoundedRectangle(cornerRadius: 12))
                }
            } else {
                VStack(alignment: .leading, spacing: 14) {
                    Text(number == 2 ? "Roku • Home" : "Roku • Settings").font(.system(size: 20, weight: .semibold))
                    HStack(alignment: .top, spacing: 12) {
                        VStack(alignment: .leading, spacing: 6) {
                            if number == 2 {
                                row("Home", selected: false)
                                row("Settings", selected: true)
                                row("Streaming Store", selected: false)
                            } else {
                                ForEach(model ? ["Accessibility", "Audio", "Home screen", "System", "Power"] : ["Network", "Remotes & devices", "Theme", "Display type", "TV inputs"], id: \.self) { item in
                                    row(item, selected: item == (model ? "System" : "Network") && !about)
                                }
                            }
                        }.frame(maxWidth: .infinity, alignment: .leading)
                        VStack(alignment: .leading, spacing: 6) {
                            if number == 5 {
                                ForEach(Array(step.items.enumerated()), id: \.offset) { i, item in row(item, selected: i == step.focus) }
                            } else if number >= 3 {
                                row("About", selected: about)
                                ForEach(model ? ["Power", "System update"] : ["Check connection", "Set up connection", "Bandwidth saver"], id: \.self) { item in row(item, selected: false) }
                            } else {
                                Image(systemName: "square.grid.2x2").font(.system(size: 40)).padding(16)
                            }
                        }.frame(maxWidth: .infinity, alignment: .leading)
                    }
                }.foregroundColor(.white).padding(16).background(Color(red: 0.02, green: 0.22, blue: 0.57)).clipShape(RoundedRectangle(cornerRadius: 12))
            }
            Label(number == 5 ? "Read the highlighted field on your TV" : number == 1 ? "Use the Home button on the remote" : "Use the remote arrows, then press Right", systemImage: number == 5 ? "eye" : "arrow.right.circle")
                .font(.caption).foregroundColor(theme.accent)
        }.padding(14).background(theme.raised).clipShape(RoundedRectangle(cornerRadius: 18))
            .accessibilityElement(children: .ignore).accessibilityLabel("Roku picture \(number). Left menu and right information panel. Highlighted: \(step.items[step.focus]). \(step.instruction)")
            .accessibilityIdentifier("setup-illustration")
    }
    private func row(_ label: String, selected: Bool) -> some View {
        HStack(alignment: .top, spacing: 3) {
            if selected { Text("\(number) →").font(.system(size: 11, weight: .bold)) }
            Text(label).font(.system(size: 13, weight: selected ? .semibold : .regular)).fixedSize(horizontal: false, vertical: true)
        }.padding(7).frame(maxWidth: .infinity, alignment: .leading)
            .foregroundColor(selected ? Color.black : Color.white)
            .background(selected ? Color.white : Color.black.opacity(0.12)).clipShape(RoundedRectangle(cornerRadius: 3))
    }
}

/// Manufacturer-documented profile location; illustrative, not firmware artwork.
private struct ProfileMenuIllustration: View {
    let step: AQSSSetupStep
    let number: Int
    let theme: AppTheme
    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            Text("Picture \(number) · upper-right profile menu").font(.caption).foregroundColor(theme.muted)
            VStack(spacing: 16) {
                HStack {
                    Text("Google TV").font(.headline)
                    Spacer()
                    Label(number == 2 ? "2 → Profile" : "Profile", systemImage: "person.crop.circle")
                        .font(.subheadline.bold()).padding(10)
                        .foregroundColor(number == 2 ? theme.controlText : theme.text)
                        .background(number == 2 ? theme.control : theme.raised)
                        .clipShape(RoundedRectangle(cornerRadius: 10))
                }
                HStack(alignment: .top, spacing: 12) {
                    VStack(alignment: .leading, spacing: 10) {
                        Text("For you · Apps").font(.caption)
                        HStack { ForEach(0..<3) { _ in RoundedRectangle(cornerRadius: 6).fill(theme.outline).frame(height: 42) } }
                        Text("TV home content").font(.caption).foregroundColor(theme.muted)
                    }.frame(maxWidth: .infinity)
                    if number == 3 {
                        VStack(alignment: .leading, spacing: 12) {
                            Text("Your account").font(.caption)
                            Label("3 → Settings", systemImage: "gearshape").font(.subheadline.bold())
                                .padding(10).foregroundColor(theme.controlText).background(theme.control)
                                .clipShape(RoundedRectangle(cornerRadius: 8))
                        }.padding(10).background(theme.raised).clipShape(RoundedRectangle(cornerRadius: 10))
                    }
                }
            }.padding(14).background(theme.surface).clipShape(RoundedRectangle(cornerRadius: 12))
            Label("Use the remote arrows, then OK", systemImage: "arrow.up.and.down.and.arrow.left.and.right").font(.caption).foregroundColor(theme.accent)
        }.padding(14).background(theme.raised).clipShape(RoundedRectangle(cornerRadius: 20))
        .accessibilityElement(children: .ignore)
        .accessibilityLabel("Picture \(number). Profile icon at upper right. Highlighted: \(step.items[step.focus]). \(step.instruction)")
        .accessibilityIdentifier("setup-illustration")
    }
}
