import SwiftUI
import UIKit

private struct FeaturePictureGuide: Decodable {
    struct Step: Decodable {
        let picture: String
        let title: String
        let detail: String
    }

    let title: String
    let steps: [Step]

    static let directory = "feature-pictures"
    static let catalog: [String: Self] = {
        guard let url = Bundle.main.url(forResource: "guides", withExtension: "json", subdirectory: directory),
              let data = try? Data(contentsOf: url),
              let guides = try? JSONDecoder().decode([String: Self].self, from: data) else { return [:] }
        return guides
    }()
}

/// The sheet leaves the current page and the user's setup choices in place.
struct FeaturePictureGuideButton: View {
    let topic: String
    let theme: AppTheme
    @State private var showing = false

    var body: some View {
        if let guide = FeaturePictureGuide.catalog[topic] {
            Button { showing = true } label: {
                Label("Picture guide", systemImage: "photo.on.rectangle")
            }
            .buttonStyle(AppButtonStyle(theme: theme))
            .accessibilityHint(guide.title)
            .accessibilityIdentifier("picture-guide-" + topic)
            .sheet(isPresented: $showing) {
                VStack(alignment: .leading, spacing: 0) {
                    Button { showing = false } label: {
                        Label("Back", systemImage: "arrow.left")
                    }
                    .buttonStyle(AppButtonStyle(theme: theme))
                    .accessibilityIdentifier("picture-guide-back").padding(12)
                    ScrollView {
                        VStack(alignment: .leading, spacing: 24) {
                            Text(guide.title).font(.title.bold()).accessibilityAddTraits(.isHeader)
                            ForEach(guide.steps.indices, id: \.self) { index in
                                let step = guide.steps[index]
                                VStack(alignment: .leading, spacing: 8) {
                                    Text("\(index + 1). \(step.title)")
                                        .font(.title3.bold()).accessibilityAddTraits(.isHeader)
                                    if let url = Bundle.main.url(forResource: step.picture, withExtension: "png",
                                                                 subdirectory: FeaturePictureGuide.directory),
                                       let image = UIImage(contentsOfFile: url.path) {
                                        Image(uiImage: image).resizable().scaledToFit()
                                            .frame(maxWidth: 440).clipShape(RoundedRectangle(cornerRadius: 12))
                                            .accessibilityHidden(true)
                                    }
                                    Text(step.detail).font(.body)
                                }
                            }
                        }
                        .fixedSize(horizontal: false, vertical: true)
                        .frame(maxWidth: 600, alignment: .leading).padding(20)
                        .frame(maxWidth: .infinity, alignment: .center)
                    }
                    .accessibilityIdentifier("picture-guide-steps")
                }
                .frame(maxWidth: .infinity, alignment: .leading)
                .foregroundColor(theme.text).background(theme.background.ignoresSafeArea())
            }
        }
    }
}

/// Always visible beside the task. The caption supplies the same instruction to VoiceOver.
struct FeaturePictureStep: View {
    let picture: String
    let caption: String
    let theme: AppTheme

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            if let url = Bundle.main.url(forResource: picture, withExtension: "png",
                                         subdirectory: FeaturePictureGuide.directory),
               let image = UIImage(contentsOfFile: url.path) {
                Image(uiImage: image).resizable().scaledToFit()
                    .frame(maxWidth: 440).clipShape(RoundedRectangle(cornerRadius: 12))
                    .accessibilityHidden(true)
            }
            Text(caption).font(.callout).fixedSize(horizontal: false, vertical: true)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .foregroundColor(theme.text)
        .accessibilityIdentifier("task-picture-" + picture)
    }
}
