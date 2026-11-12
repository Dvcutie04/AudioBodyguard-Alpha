// Owned, simulator-only, independent UIKit control for system Share diagnosis.
// This standalone app does not use Audio Bodyguard source, reports, identity,
// network, microphone, pairing, or physical-control implementations.
import UIKit

final class NativeShareControlViewController: UIViewController {
    private let openButton = UIButton(type: .system)

    override func viewDidLoad() {
        super.viewDidLoad()
        view.backgroundColor = .systemBackground
        openButton.setTitle("Open native Share", for: .normal)
        openButton.accessibilityIdentifier = "native-share-control-open"
        openButton.translatesAutoresizingMaskIntoConstraints = false
        openButton.addTarget(self, action: #selector(openShare), for: .touchUpInside)
        view.addSubview(openButton)
        NSLayoutConstraint.activate([
            openButton.centerXAnchor.constraint(equalTo: view.centerXAnchor),
            openButton.centerYAnchor.constraint(equalTo: view.centerYAnchor)
        ])
    }

    @objc private func openShare() {
        let sheet = UIActivityViewController(
            activityItems: ["AQSS independent owned-fixture Share control"],
            applicationActivities: nil
        )
        if let popover = sheet.popoverPresentationController {
            popover.sourceView = openButton
            popover.sourceRect = openButton.bounds
        }
        present(sheet, animated: true)
    }
}

@objc(NativeShareControlDelegate)
final class NativeShareControlDelegate: UIResponder, UIApplicationDelegate {
    var window: UIWindow?

    func application(
        _ application: UIApplication,
        didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]? = nil
    ) -> Bool {
        let window = UIWindow(frame: UIScreen.main.bounds)
        window.rootViewController = NativeShareControlViewController()
        window.makeKeyAndVisible()
        self.window = window
        return true
    }
}

UIApplicationMain(
    CommandLine.argc,
    CommandLine.unsafeArgv,
    nil,
    NSStringFromClass(NativeShareControlDelegate.self)
)
