import SwiftUI

struct SetupGuideRequest: Identifiable {
    let id = UUID()
    let group: String
}

/// Local, illustrative instructions. No device session, credentials or control API.
struct SetupGuidesView: View {
    let theme: AppTheme
    let initialGroup: String
    var onVoiceCheck: (() -> Void)? = nil
    @Environment(\.dismiss) private var dismiss
    @Environment(\.dynamicTypeSize) private var textSize
    @State private var groupID = ""
    @State private var routeID: String?
    @State private var index = -1
    @State private var mismatch = false
    @State private var initialized = false
    @AccessibilityFocusState private var headingFocused: Bool
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
            ScrollView {
                VStack(alignment: .leading, spacing: 18) {
                    Text(title).font(.title.bold()).fixedSize(horizontal: false, vertical: true)
                        .accessibilityAddTraits(.isHeader).accessibilityFocused($headingFocused)
                    if mismatch { mismatchContent }
                    else if let route = route {
                        if let step = step {
                            Label(step.surface == "tv" ? "On your TV · use the remote" : step.surface == "both" ? "Your TV + your phone" : "On your phone", systemImage: step.surface == "phone" ? "iphone" : "tv")
                                .font(.subheadline.weight(.semibold)).foregroundColor(theme.accent)
                            Text(step.instruction).font(.body.weight(.medium)).fixedSize(horizontal: false, vertical: true)
                            SetupScreenIllustration(step: step, number: index + 1, theme: theme)
                            Text(step.note).font(.callout).foregroundColor(theme.muted)
                            control("My screen looks different", icon: "questionmark.circle", id: "setup-mismatch") { mismatch = true }
                        } else { introduction(route) }
                    } else if let group = group {
                        Text(group.title).font(.title3.weight(.semibold)).foregroundColor(theme.accent)
                        Text("Choose the setup screen or operating system you actually see. A brand alone does not confirm compatibility.").foregroundColor(theme.muted)
                        ForEach(group.routes, id: \.self) { id in
                            if let route = AQSSSetupContent.routes.first(where: { $0.id == id }) {
                                control(route.title, icon: "rectangle.stack", id: "setup-route-\(id)") { routeID = id; index = -1 }
                            }
                        }
                    } else {
                        Text("Follow one picture at a time. The numbered arrow marks the next choice; TV, remote and phone symbols show which device to use.").foregroundColor(theme.muted)
                        ForEach(AQSSSetupContent.groups.filter { !["both", "neither"].contains($0.id) }, id: \.id) { item in
                            control(item.title, icon: item.id == "voice" ? "mic" : ["google", "alexa"].contains(item.id) ? "house" : "tv", id: "setup-group-\(item.id)") { chooseGroup(item.id) }
                        }
                    }
                }.frame(maxWidth: 620, alignment: .leading).padding(20).frame(maxWidth: .infinity)
            }.id(key).accessibilityIdentifier("setup-scroll")
            footer
        }.background(theme.background.ignoresSafeArea()).foregroundColor(theme.text)
            .onAppear { if !initialized { initialized = true; chooseGroup(initialGroup) } }
            .onChange(of: key) { _ in DispatchQueue.main.async { headingFocused = true } }
    }

    private func chooseGroup(_ id: String) {
        groupID = AQSSSetupContent.groups.contains { $0.id == id } ? id : ""
        routeID = groupID == "voice" ? "voice" : nil
        index = groupID == "voice" ? 0 : -1
        mismatch = false
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
        Text("Before you begin").font(.headline)
        Text(route.appliesTo)
        if !route.models.isEmpty {
            Text("Documented model examples: \(route.models.joined(separator: ", "))").font(.headline)
        } else {
            Text("Menu-family guide. Your exact model is not confirmed by this preview.").foregroundColor(theme.muted)
        }
        Text("\(route.steps.count) pictures · one action at a time").font(.headline).foregroundColor(theme.accent)
        Text("Pictures are simplified illustrations. Labels, layout and services can differ by country, software and language. Compare each picture with your own screen.").foregroundColor(theme.muted)
        Text("Complete account approvals in the official app or on your TV. This guide never asks for a password and does not connect Audio Bodyguard.").font(.callout)
        sources(route)
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
            Text("If the option, TV or permission request is absent, use the manufacturer’s instructions below. Do not assume a successful pairing.")
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
                Button {
                    if index == route.steps.count - 1 {
                        if route.id == "voice" { onVoiceCheck?() }
                        dismiss()
                    } else { index += 1 }
                } label: {
                    navigationLabel(index < 0 ? "Start guide" : index == route.steps.count - 1 ? (route.id == "voice" && onVoiceCheck != nil ? "Open Voice check" : "Finish guide") : "Next", icon: index == route.steps.count - 1 ? (route.id == "voice" && onVoiceCheck != nil ? "mic" : "checkmark") : "arrow.right")
                        .frame(maxWidth: .infinity, minHeight: 44)
                }.buttonStyle(AppButtonStyle(theme: theme, primary: true)).accessibilityIdentifier("setup-next")
            }
        }.padding(16).background(theme.surface)
    }
    private func goBack() {
        if mismatch { mismatch = false }
        else if index >= 0 { index -= 1 }
        else if routeID != nil { routeID = nil }
        else { groupID = "" }
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
