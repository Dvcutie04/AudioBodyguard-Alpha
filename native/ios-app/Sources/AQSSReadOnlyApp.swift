import SwiftUI

@main
struct AQSSReadOnlyApp: App {
    var body: some Scene {
        WindowGroup { ReadOnlyHomeView() }
    }
}

private struct ReadOnlyHomeView: View {
    // No observation is supplied until a native source and output path qualify.
    private let coverage = AQSSSessionEvidenceView.coverage(
        nil, runtimeId: "prototype", clockDomainId: "prototype", nowMonotonic: 0
    )

    private var coverageTitle: String {
        guard coverage.state == .unknownPhysicalState, coverage.reason == "NO_OBSERVATION" else {
            return "Unknown physical state — app status unavailable"
        }
        return "Unknown physical state"
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 18) {
                Text("SIMULATION — no audio path connected")
                    .font(.headline)
                section("Coverage", detail: coverageTitle, explanation:
                    "No output observation. This screen does not monitor or protect audio.")
                section("Supported controls", detail: "Unknown", explanation:
                    "No player, route, permission, or physical observer is connected.")
                section("Captions", detail: "Not observed", explanation:
                    "No authored caption track has been discovered or selected.")
                section("Session history", detail: "No observed events", explanation:
                    "A missing history cannot establish continuous coverage.")
                section("Next step", detail: "Qualify a supported path", explanation:
                    "A supported output and independent observation path must be qualified before this app can report an active listening session.")
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(24)
        }
    }

    private func section(_ title: String, detail: String, explanation: String) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(title).font(.title2.bold())
            Text(detail).font(.headline)
            Text(explanation).font(.body)
        }
        .accessibilityElement(children: .combine)
    }
}
