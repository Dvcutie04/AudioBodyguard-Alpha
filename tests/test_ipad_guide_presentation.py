"""Source guards only; native screenshots remain required for layout approval."""
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "native/ios-app/Sources/SetupGuides.swift"


def test_ipad_guides_request_page_sizing_without_changing_iphone_or_old_ios():
    source = SOURCE.read_text(encoding="utf-8")
    start = source.index("    var body: some View {")
    end = source.index("    private var guideContent: some View {", start)
    presentation = source[start:end]
    assert "if #available(iOS 18.0, *), UIDevice.current.userInterfaceIdiom == .pad" in presentation
    assert "guideContent.presentationSizing(.page)" in presentation
    assert "} else {\n            guideContent\n        }" in presentation
    # Native presentation sizing follows the hosting window. Do not replace it
    # with main-screen dimensions, scaled text, or a custom modal controller.
    for forbidden in ("UIScreen", ".frame(", ".scaleEffect(", "UIHostingController", ".fullScreenCover"):
        assert forbidden not in presentation


def test_page_sizing_preserves_scroll_and_navigation_ownership():
    source = SOURCE.read_text(encoding="utf-8")
    assert source.count("guideContent.presentationSizing(.page)") == 1
    assert '@State private var history: [Location] = []' in source
    assert '@StateObject private var progress = SetupProgressStore()' in source
    assert 'GuideScrollView(screenKey: key, identifier: "setup-scroll"' in source
    assert '.accessibilityIdentifier("setup-close")' in source
    assert '.accessibilityIdentifier("setup-back")' in source
    assert '.accessibilityIdentifier("setup-next")' in source
    assert 'guard let previous = history.popLast() else { dismiss(); return }' in source
    assert 'if !initialized {' in source


NETWORK = Path(__file__).resolve().parents[1] / "native/ios-app/Sources/TVNetworkCheck.swift"


def test_ipad_network_check_and_inline_vizio_helpers_use_page_sizing():
    source = NETWORK.read_text(encoding="utf-8")
    start = source.index("struct TVNetworkCheckView: View")
    presentation = source[start:source.index("    private var checkContent: some View", start)]
    assert "if #available(iOS 18.0, *), UIDevice.current.userInterfaceIdiom == .pad" in presentation
    assert "checkPresentation.presentationSizing(.page)" in presentation
    assert "} else {\n            checkPresentation\n        }" in presentation
    assert "if let guideContext = guideContext" in presentation
    assert "TVCheckPictureGuide(theme: theme, context: guideContext)" in presentation
    assert "check.stop(clear: true)" in presentation
    for forbidden in ("UIScreen", ".frame(", ".scaleEffect(", "UIHostingController", ".fullScreenCover"):
        assert forbidden not in presentation


def test_network_page_ownership_retains_address_route_and_back_navigation():
    source = NETWORK.read_text(encoding="utf-8")
    assert source.count("checkPresentation.presentationSizing(.page)") == 1
    assert "@StateObject private var check = TVNetworkCheck()" in source
    assert "@State private var guideContext: TVCheckPictureGuide.Context?" in source
    assert "TVCheckPictureGuide(theme: theme, context: guideContext) { self.guideContext = nil }" in source
    assert 'GuideScrollView(screenKey: screenKey, identifier: prefix + "-scroll"' in source
    assert 'accessibilityIdentifier(prefix + "-back")' in source
    assert 'accessibilityIdentifier(prefix + "-next")' in source
    back = source.split("private func back() {", 1)[1]
    assert "if mismatch {\n            mismatch = false" in back
    assert "index = recovery.origin\n            mismatch = true" in back
    assert "else if index >= 0 {\n            index -= 1" in back
