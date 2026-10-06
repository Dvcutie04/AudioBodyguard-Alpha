import Foundation

/// Untrusted presentation hints only. Deliberately has no connection or authority API.
public struct TVPhotoHints {
    public let brand: String?
    public let model: String?
    public let address: String?
    public init(_ text: String) {
        guard text.utf8.count <= 8192 else { brand = nil; model = nil; address = nil; return }
        let upper = text.uppercased().replacingOccurrences(of: "(?m)^(MODEL(?: CODE| NUMBER| NO\\.?)?|IP(?:V4)?(?: ADDRESS)?)[ \\t]*[:=]?[ \\t]*\\r?\\n[ \\t]*", with: "$1: ", options: .regularExpression)
        func matches(_ pattern: String) -> [String] {
            guard let re = try? NSRegularExpression(pattern: pattern, options: [.anchorsMatchLines]) else { return [] }
            let ns = upper as NSString
            return re.matches(in: upper, range: NSRange(location: 0, length: ns.length)).map { ns.substring(with: $0.range(at: 1)) }
        }
        let brands = Set(matches("\\b(SAMSUNG|LG|SONY|TCL|HISENSE|VIZIO|PANASONIC|PHILIPS)\\b"))
        brand = brands.count == 1 ? brands.first : nil
        let models = Set(matches("^[ \\t]*MODEL(?: CODE| NUMBER| NO\\.?)?(?:[ \\t]*[:=][ \\t]*|[ \\t]+)([A-Z0-9][A-Z0-9._-]{1,39})[ \\t]*$"))
        model = models.count == 1 && models.first!.rangeOfCharacter(from: .decimalDigits) != nil ? models.first : nil
        let addresses = Set(matches("^[ \\t]*IP(?:V4)?(?: ADDRESS)?(?:[ \\t]*[:=][ \\t]*|[ \\t]+)([0-9.]+)[ \\t]*$"))
        address = addresses.count == 1 && Self.isPrivateIPv4(addresses.first!) ? addresses.first : nil
    }
    public static func isPrivateIPv4(_ value: String) -> Bool {
        let parts = value.split(separator: ".", omittingEmptySubsequences: false)
        guard parts.count == 4 else { return false }
        var octets: [Int] = []
        for part in parts {
            guard !part.isEmpty, part.count <= 3, part.allSatisfy({ $0 >= "0" && $0 <= "9" }), !(part.count > 1 && part.first == "0"), let n = Int(part), n <= 255 else { return false }
            octets.append(n)
        }
        return octets[0] == 10 || (octets[0] == 172 && (16...31).contains(octets[1])) || (octets[0] == 192 && octets[1] == 168)
    }
}
