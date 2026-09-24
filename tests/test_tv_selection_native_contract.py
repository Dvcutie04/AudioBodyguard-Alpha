import json
from pathlib import Path

from src.edge.tv_selection_preferences import TVSelectionPreferences
from src.interface.tv_selection_native_adapter import TVSelectionNativeFeedbackAdapter


def test_native_feedback_v1_contract_fixtures(tmp_path):
    contract=json.loads(Path("contracts/tv_selection_native_feedback_v1.json").read_text())
    assert contract["schema_version"]==1
    assert contract["platforms"]==["ios","android"]
    assert contract["capability"]=="feedback_sync_only"
    for index,case in enumerate(contract["cases"]):
        store=TVSelectionPreferences(tmp_path / f"case_{index}.sqlite3")
        adapter=TVSelectionNativeFeedbackAdapter(store,platform=case["platform"],authorized_profile_id=case["authorized_profile_id"])
        assert adapter.handle(case["request"])==case["expected"]
        if not case["expected"]["ok"]:
            assert store.feedback_history(case["authorized_profile_id"])==[]


def test_swift_native_feedback_contract_is_feedback_only():
    source=Path("native/ios/Sources/AQSSNativeFeedback/NativeFeedbackContract.swift").read_text()
    assert "struct NativeFeedbackEvent: Codable" in source
    assert "struct NativeFeedbackSyncRequest: Codable" in source
    assert "struct NativeFeedbackSyncResponse: Codable" in source
    assert "protocol NativeFeedbackSyncing" in source
    assert "schemaVersion" in source
    assert "eventId" in source
    assert "recordedAt" in source
    assert "PROFILE_NOT_AUTHORIZED" in source
    assert "INVALID_FEEDBACK" in source
    assert "setVolume" not in source
    assert "execute" not in source


def test_kotlin_native_feedback_contract_matches_swift_boundary():
    source=Path("native/android/src/main/kotlin/com/aqss/nativefeedback/NativeFeedbackContract.kt").read_text()
    assert "data class NativeFeedbackEvent" in source
    assert "data class NativeFeedbackSyncRequest" in source
    assert "data class NativeFeedbackSyncResponse" in source
    assert "interface NativeFeedbackSyncing" in source
    assert "@SerialName(\"schema_version\")" in source
    assert "@SerialName(\"event_id\")" in source
    assert "@SerialName(\"recorded_at\")" in source
    assert "PROFILE_NOT_AUTHORIZED" in source
    assert "INVALID_FEEDBACK" in source
    assert "suspend fun sync" in source
    assert "setVolume" not in source
    assert "execute" not in source


def test_native_contract_build_scaffolds_are_configured():
    swift=Path("native/ios/Package.swift").read_text()
    gradle=Path("native/android/build.gradle.kts").read_text()
    settings=Path("native/android/settings.gradle.kts").read_text()
    assert "swift-tools-version" in swift
    assert "AQSSNativeFeedback" in swift
    assert ".library(" in swift
    assert "com.android.library" in gradle
    assert "org.jetbrains.kotlin.android" in gradle
    assert "org.jetbrains.kotlin.plugin.serialization" in gradle
    assert "kotlinx-serialization-json" in gradle
    assert "namespace = \"com.aqss.nativefeedback\"" in gradle
    assert "rootProject.name = \"AQSSNativeFeedback\"" in settings


def test_swift_conformance_test_reads_shared_fixture():
    source=Path("native/ios/Tests/AQSSNativeFeedbackTests/NativeFeedbackContractTests.swift").read_text()
    assert "import XCTest" in source
    assert "@testable import AQSSNativeFeedback" in source
    assert "tv_selection_native_feedback_v1.json" in source
    assert "JSONSerialization.jsonObject" in source
    assert "JSONDecoder().decode(NativeFeedbackSyncRequest.self" in source
    assert "JSONDecoder().decode(NativeFeedbackSyncResponse.self" in source
    assert "setVolume" not in source
    assert "execute" not in source


def test_kotlin_conformance_test_reads_shared_fixture():
    source=Path("native/android/src/test/kotlin/com/aqss/nativefeedback/NativeFeedbackContractTest.kt").read_text()
    assert "import kotlin.test.Test" in source
    assert "import kotlinx.serialization.json.Json" in source
    assert "tv_selection_native_feedback_v1.json" in source
    assert "Json.parseToJsonElement" in source
    assert "Json.decodeFromJsonElement<NativeFeedbackSyncRequest>" in source
    assert "Json.decodeFromJsonElement<NativeFeedbackSyncResponse>" in source
    assert "INVALID_FEEDBACK" in source
    assert "setVolume" not in source
    assert "execute" not in source


def test_ci_compiles_and_runs_both_native_contract_suites():
    workflow=Path(".github/workflows/ci.yml").read_text()
    assert "native-swift:" in workflow
    assert "runs-on: macos-14" in workflow
    assert "swift test --package-path native/ios" in workflow
    assert "native-android:" in workflow
    assert "actions/setup-java@v4" in workflow
    assert "distribution: temurin" in workflow
    assert "java-version: \"17\"" in workflow
    assert "gradle/actions/setup-gradle@v4" in workflow
    assert "gradle-version: \"8.10.2\"" in workflow
    assert "gradle -p native/android testDebugUnitTest" in workflow


def test_shared_contract_declares_generator_schema():
    contract=json.loads(Path("contracts/tv_selection_native_feedback_v1.json").read_text())
    assert contract["event_fields"]=={"schema_version":"integer","event_id":"string","profile_id":"string","device_id":"string","approved":"boolean","choice":"choice","recorded_at":"string"}
    assert contract["choices"]==["rating","keep_this_tv","never_switch_automatically"]
    assert contract["error_codes"]==["PROFILE_NOT_AUTHORIZED","INVALID_FEEDBACK"]
    assert contract["request_fields"]=={"events":"event_array"}
    assert contract["response_fields"]=={"schema_version":"integer","ok":"boolean","applied":"optional_string_array","duplicates":"optional_string_array","error":"optional_error"}


def test_native_contract_generator_check_is_clean_and_read_only(monkeypatch,capsys):
    import hashlib
    import importlib.util
    import sys
    generator=Path("tools/generate_native_feedback_contracts.py")
    spec=importlib.util.spec_from_file_location("native_feedback_generator",generator)
    assert spec is not None and spec.loader is not None
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    targets=[Path("native/ios/Sources/AQSSNativeFeedback/NativeFeedbackContract.swift"),Path("native/android/src/main/kotlin/com/aqss/nativefeedback/NativeFeedbackContract.kt")]
    before=[hashlib.sha256(target.read_bytes()).hexdigest() for target in targets]
    monkeypatch.setattr(sys,"argv",[str(generator),"--check"])
    module.main()
    after=[hashlib.sha256(target.read_bytes()).hexdigest() for target in targets]
    assert after==before
    assert capsys.readouterr().out.strip()=="NATIVE_CONTRACTS_CURRENT"


def test_ci_runs_generator_drift_check_and_actual_pytest_suite():
    workflow=Path(".github/workflows/ci.yml").read_text()
    assert "python -m pip install -r requirements.txt" in workflow
    assert "python tools/generate_native_feedback_contracts.py --check" in workflow
    assert "python -m pytest -q" in workflow
    assert "python -m unittest discover" not in workflow
