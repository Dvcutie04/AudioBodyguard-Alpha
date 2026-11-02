import Foundation

/// Presentation only. A phone label does not identify, pair or authorize a TV.
public enum AQSSSetupPhone: String, CaseIterable, Sendable {
    case iphone, pixel, galaxy, android
    public var label: String {
        switch self {
        case .iphone: return "iPhone"
        case .pixel: return "Google Pixel"
        case .galaxy: return "Samsung Galaxy"
        case .android: return "Android"
        }
    }
    public static func androidManufacturer(_ value: String) -> Self {
        switch value.lowercased() {
        case "samsung": return .galaxy
        case "google": return .pixel
        default: return .android
        }
    }
}

public enum AQSSSetupPresentation {
    /// Keep documented shared app labels. Specialize only actual phone surfaces.
    public static func step(_ original: AQSSSetupStep, phone: AQSSSetupPhone) -> AQSSSetupStep {
        guard original.surface == "phone" else { return original }
        let store = phone == .iphone ? "App Store" : "Google Play"
        var screen = original.screen
        var instruction = original.instruction
        var items = original.items
        if screen == "App Store or Google Play" {
            screen = "\(phone.label) • \(store)"
            instruction = instruction.replacingOccurrences(of: "App Store or Google Play", with: store)
            if phone == .iphone { items = items.map { $0 == "Install" ? "Get" : $0 } }
        } else if screen == "Phone apps" { screen = "\(phone.label) • Apps" }
        else if screen == "Phone • Wi-Fi" { screen = "\(phone.label) • Wi-Fi" }
        return AQSSSetupStep(title: original.title, instruction: instruction, surface: original.surface,
                             screen: screen, items: items, focus: original.focus, action: original.action,
                             note: original.note, pictureSurface: original.pictureSurface)
    }
}
