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
