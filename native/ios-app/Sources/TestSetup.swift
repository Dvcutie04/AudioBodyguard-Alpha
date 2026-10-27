import Foundation
import SwiftUI

/// Temporary manual notes; no audio session, discovery or measurement work.
struct TestSetupView: View {
    let theme: AppTheme
    @Environment(\.dismiss) private var dismiss
    @State private var notes: [TestSetupField: String] = [:]
    @State private var reviewed: TestSetupReportSnapshot?
    @State private var error: String?
    @FocusState private var focused: TestSetupField?
    private var hasNotes: Bool { notes.values.contains { !$0.isEmpty } }

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(alignment: .center, spacing: 12) {
                Text(reviewed == nil ? "Test setup" : "Review setup report")
                    .font(.title2.bold()).fixedSize(horizontal: false, vertical: true)
                    .accessibilityAddTraits(.isHeader).accessibilityIdentifier("test-setup-heading")
                Spacer(minLength: 0)
                RoseButton(title: "Back", theme: theme, compact: true) {
                    focused = nil
                    if reviewed != nil { reviewed = nil } else { dismiss() }
                }.accessibilityIdentifier("test-setup-back")
            }
            if let report = reviewed {
                ScrollView {
                    Text(report.text).font(.body).fixedSize(horizontal: false, vertical: true)
                        .frame(maxWidth: .infinity, alignment: .leading).textSelection(.enabled)
                        .accessibilityIdentifier("test-setup-preview")
                }.accessibilityIdentifier("test-setup-report-scroll")
                Text(TestSetupReportSnapshot.notice).font(.subheadline)
                    .fixedSize(horizontal: false, vertical: true).accessibilityIdentifier("test-setup-notice")
                ReviewedTextShareButton(text: report.text, theme: theme,
                    title: "Share setup report", identifier: "test-setup-share")
            } else {
                ScrollView {
                    VStack(alignment: .leading, spacing: 16) {
                        Text("Record the two-phone test arrangement. These are your notes, not verified measurements.")
                            .fixedSize(horizontal: false, vertical: true)
                        Text("Every answer is optional. Leave blank for Unknown. Brief technical details only.")
                            .font(.subheadline).fixedSize(horizontal: false, vertical: true)
                        ForEach(TestSetupField.allCases, id: \.self) { field in
                            VStack(alignment: .leading, spacing: 6) {
                                Text(field.title).font(.headline).fixedSize(horizontal: false, vertical: true)
                                TextField(field.hint, text: Binding(
                                    get: { notes[field] ?? "" },
                                    set: { notes[field] = TestSetupReportSnapshot.limitInput($0); error = nil }))
                                    .textInputAutocapitalization(.never).disableAutocorrection(true)
                                    .submitLabel(.done).focused($focused, equals: field)
                                    .onSubmit { focused = nil }
                                    .padding(12).frame(minHeight: 44)
                                    .background(theme.raised).clipShape(RoundedRectangle(cornerRadius: 12))
                                    .overlay(RoundedRectangle(cornerRadius: 12).stroke(theme.outline, lineWidth: 1))
                                    .accessibilityLabel(field.title).accessibilityIdentifier("test-setup-" + field.rawValue)
                            }
                        }
                        Text("Notes are temporary. Closing this worksheet clears them.")
                            .font(.subheadline).fixedSize(horizontal: false, vertical: true)
                        if let message = error {
                            Text(message).foregroundColor(theme.warning).fixedSize(horizontal: false, vertical: true)
                        }
                    }.frame(maxWidth: .infinity, alignment: .leading)
                }.accessibilityIdentifier("test-setup-form")
                Button { focused = nil; notes.removeAll(); error = nil } label: {
                    Text("Clear notes").frame(maxWidth: .infinity, minHeight: 44)
                }.buttonStyle(AppButtonStyle(theme: theme)).disabled(!hasNotes)
                    .accessibilityIdentifier("test-setup-clear")
                Button(action: review) {
                    Text("Review setup report").frame(maxWidth: .infinity, minHeight: 44)
                }.buttonStyle(AppButtonStyle(theme: theme, primary: true))
                    .accessibilityIdentifier("test-setup-review")
            }
        }
        .padding(20).frame(maxWidth: 680, maxHeight: .infinity)
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .foregroundColor(theme.text).accentColor(theme.accent)
        .background(theme.background.ignoresSafeArea())
    }

    private func review() {
        focused = nil
        let milliseconds = Date().timeIntervalSince1970 * 1000
        guard milliseconds.isFinite, milliseconds >= 0, milliseconds < Double(Int64.max) else {
            error = "Check this phone’s date and the notes, then try again."; return
        }
        do {
            reviewed = try TestSetupReportSnapshot.capture(buildDetails: installedAppBuildDetails(),
                notes: notes, reviewedAtMillis: Int64(milliseconds))
            error = nil
        } catch {
            self.error = "Check this phone’s date and the notes, then try again."
        }
    }
}
