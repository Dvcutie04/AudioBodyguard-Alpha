"""Generate presentation-only tutorial text for both native shells."""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGETS = {
    "overview": {"welcome", "trends", "appearance"},
    "connection": {"chooseTV", "chooseHome", "connectionPlan", "connectionCheck", "featureExample", "guideFinish"},
    "home": {"coverage", "capability", "captions", "history", "hint", "handoff"},
    "options": {"options", "volume", "captionOption", "sound", "equalizer", "defaults"},
    "advanced": {"advanced", "route", "physical", "background", "privacy", "handoffOption"},
    "checklist": {"checkHardware", "checkQualification", "checkPermission", "checkRoute", "checkRuntime", "checkEvidence"},
}


def validate(data):
    if set(data) != {"schema_version", "mode", "topics", "choices", "connection_stages", "feature_catalog", "onboarding"} or data["schema_version"] != 1 or data["mode"] != "read_only_guidance":
        raise ValueError("invalid presentation-only tutorial contract")
    stages = data["connection_stages"]
    if not isinstance(stages, list) or len(stages) != 2:
        raise ValueError("two connection stages required")
    used_targets = set()
    for number, stage in enumerate(stages, 1):
        if type(stage) is not dict or set(stage) != {"number", "title", "detail", "targets"} or type(stage["number"]) is not int or stage["number"] != number:
            raise ValueError("ordered presentation-only connection stages required")
        if any(type(stage[key]) is not str or not stage[key].strip() or len(stage[key]) > 160 for key in ("title", "detail")):
            raise ValueError("invalid connection stage text")
        if not isinstance(stage["targets"], list) or not stage["targets"] or any(type(target) is not str or target not in TARGETS["connection"] or target in used_targets for target in stage["targets"]) or len(stage["targets"]) != len(set(stage["targets"])):
            raise ValueError("invalid connection stage targets")
        used_targets.update(stage["targets"])
    catalog = data["feature_catalog"]
    if type(catalog) is not dict or set(catalog) != {"title", "note", "items"}:
        raise ValueError("presentation-only feature catalog required")
    if any(type(catalog[key]) is not str or not catalog[key].strip() or len(catalog[key]) > 320 for key in ("title", "note")) or type(catalog["items"]) is not list or not 1 <= len(catalog["items"]) <= 24:
        raise ValueError("invalid bounded feature catalog")
    feature_ids = set()
    for feature in catalog["items"]:
        if type(feature) is not dict or set(feature) != {"id", "title", "detail", "availability"} or any(type(value) is not str or not value.strip() or len(value) > 160 for value in feature.values()):
            raise ValueError("presentation-only feature descriptions required")
        if not feature["id"].isidentifier() or feature["id"] in feature_ids or feature["availability"] not in {"planned", "preview"}:
            raise ValueError("invalid feature identity or availability")
        feature_ids.add(feature["id"])
    presentation = data["onboarding"]
    if type(presentation) is not dict or set(presentation) != {"featured_ids", "notice", "start_label", "more_features_label", "help_label", "picture_continue_routes"}:
        raise ValueError("presentation-only onboarding required")
    featured = presentation["featured_ids"]
    if type(featured) is not list or len(featured) != 3 or any(type(value) is not str or value not in feature_ids for value in featured) or len(set(featured)) != 3:
        raise ValueError("three distinct known featured descriptions required")
    for key in ("notice", "start_label", "more_features_label", "help_label"):
        if type(presentation[key]) is not str or not presentation[key].strip() or len(presentation[key]) > 80:
            raise ValueError("invalid brief onboarding text")
    routes = presentation["picture_continue_routes"]
    setup = json.loads((ROOT / "contracts/setup_guides_v1.json").read_text())
    helpers = {"samsung_model_new", "samsung_model_old", "lg_model_new", "lg_model_mid", "lg_model_2020", "lg_model_old", "identify", "voice", "roku_network", "roku_model", "philips_voice_remote"}
    eligible = {route["id"] for route in setup["routes"] if route["id"] not in helpers}
    if type(routes) is not list or not routes or any(type(value) is not str or value not in eligible for value in routes) or len(set(routes)) != len(routes):
        raise ValueError("known pairing picture routes required for local continuation")
    if not isinstance(data["choices"], dict) or set(data["choices"]) != {"chooseTV", "chooseHome"}:
        raise ValueError("invalid guide choice groups")
    for choices in data["choices"].values():
        if not isinstance(choices, list) or not 1 <= len(choices) <= 16:
            raise ValueError("invalid choice count")
        ids = set()
        for choice in choices:
            if set(choice) != {"id", "title", "icon", "detail"} or any(not isinstance(v, str) or not v.strip() or len(v) > 320 for v in choice.values()):
                raise ValueError("presentation-only choices required")
            if not choice["id"].isidentifier() or choice["id"] in ids or choice["icon"] not in {"tv", "speaker", "house", "questionmark.circle"}:
                raise ValueError("ambiguous choice or unsupported local icon")
            ids.add(choice["id"])
    topics = data["topics"]
    if not isinstance(topics, list) or not 1 <= len(topics) <= 12:
        raise ValueError("invalid tutorial topics")
    ids = set()
    for topic in topics:
        if set(topic) != {"id", "title", "steps"} or topic["id"] in ids:
            raise ValueError("invalid or duplicate tutorial topic")
        ids.add(topic["id"])
        if not isinstance(topic["id"], str) or not topic["id"].isidentifier():
            raise ValueError("invalid topic identifier")
        if not isinstance(topic["title"], str) or not topic["title"].strip():
            raise ValueError("missing topic title")
        if not isinstance(topic["steps"], list) or not 1 <= len(topic["steps"]) <= 8:
            raise ValueError("invalid tutorial step count")
        for step in topic["steps"]:
            if set(step) != {"target", "area", "title", "explanation", "example"}:
                raise ValueError("tutorial steps may contain only presentation fields")
            if step["area"] not in TARGETS or step["target"] not in TARGETS[step["area"]]:
                raise ValueError("unknown tutorial area or target")
            if any(not isinstance(step[k], str) or not step[k].strip() or len(step[k]) > 320 for k in ("title", "explanation")) or type(step["example"]) is not str or len(step["example"]) > 320:
                raise ValueError("invalid tutorial text")
            if topic["id"] == "getting_started" and step["target"] == "welcome":
                if step["example"]:
                    raise ValueError("welcome uses the feature catalog instead of an example")
            elif not step["example"].startswith("Example:"):
                raise ValueError("tutorial example must be labeled")
    return data


def sources(data):
    q = lambda value: json.dumps(value, ensure_ascii=False)
    keys = ("target", "area", "title", "explanation", "example")
    swift = ["// Generated by tools/generate_tutorial_content.py. Do not edit.",
             "public struct AQSSTutorialStep: Equatable, Sendable {"]
    swift += [f"    public let {key}: String" for key in keys]
    swift += ["}", "public struct AQSSTutorialTopic: Equatable, Sendable {", "    public let id: String", "    public let title: String", "    public let steps: [AQSSTutorialStep]", "}", "public enum AQSSTutorialContent {", "    public static let topics: [AQSSTutorialTopic] = ["]
    kotlin = ["// Generated by tools/generate_tutorial_content.py. Do not edit.", "package com.aqss.nativefeedback", "data class TutorialStep(" + ", ".join(f"val {key}: String" for key in keys) + ")", "data class TutorialTopic(val id: String, val title: String, val steps: List<TutorialStep>)", "object TutorialContent {", "    val topics: List<TutorialTopic> = listOf("]
    for topic in data["topics"]:
        swift += [f"        AQSSTutorialTopic(id: {q(topic['id'])}, title: {q(topic['title'])}, steps: ["]
        kotlin += [f"        TutorialTopic({q(topic['id'])}, {q(topic['title'])}, listOf("]
        for step in topic["steps"]:
            swift += ["            AQSSTutorialStep(" + ", ".join(f"{k}: {q(step[k])}" for k in keys) + "),"]
            kotlin += ["            TutorialStep(" + ", ".join(q(step[k]).replace("$", r"\$") for k in keys) + "),"]
        swift += ["        ]),"]
        kotlin += ["        )),"]
    swift += ["    ]", "    public static let choices: [String: [AQSSTutorialChoice]] = ["]
    kotlin += ["    )", "    val choices: Map<String, List<TutorialChoice>> = mapOf("]
    for group, choices in data["choices"].items():
        swift += [f"        {q(group)}: ["]
        kotlin += [f"        {q(group)} to listOf("]
        for choice in choices:
            swift += ["            AQSSTutorialChoice(" + ", ".join(f"{k}: {q(choice[k])}" for k in ("id", "title", "icon", "detail")) + "),"]
            kotlin += ["            TutorialChoice(" + ", ".join(q(choice[k]).replace("$", r"\$") for k in ("id", "title", "icon", "detail")) + "),"]
        swift += ["        ],"]
        kotlin += ["        ),"]
    swift += ["    ]", "    public static let connectionStages: [AQSSConnectionStage] = ["]
    kotlin += ["    )", "    val connectionStages: List<ConnectionStage> = listOf("]
    for stage in data["connection_stages"]:
        targets = ", ".join(q(target) for target in stage["targets"])
        swift += [f"        AQSSConnectionStage(number: {stage['number']}, title: {q(stage['title'])}, detail: {q(stage['detail'])}, targets: [{targets}]),"]
        kotlin += [f"        ConnectionStage({stage['number']}, {q(stage['title'])}, {q(stage['detail'])}, listOf({targets})),"]
    catalog = data["feature_catalog"]
    swift += ["    ]", f"    public static let featureTitle = {q(catalog['title'])}", f"    public static let featureNote = {q(catalog['note'])}", "    public static let features: [AQSSTutorialFeature] = ["]
    kotlin += ["    )", f"    const val featureTitle = {q(catalog['title'])}", f"    const val featureNote = {q(catalog['note'])}", "    val features: List<TutorialFeature> = listOf("]
    for feature in catalog["items"]:
        keys = ("id", "title", "detail", "availability")
        swift += ["        AQSSTutorialFeature(" + ", ".join(f"{key}: {q(feature[key])}" for key in keys) + "),"]
        kotlin += ["        TutorialFeature(" + ", ".join(q(feature[key]).replace("$", r"\$") for key in keys) + "),"]
    presentation = data["onboarding"]
    swift += ["    ]", "    public static let featuredIDs: [String] = [" + ", ".join(q(value) for value in presentation["featured_ids"]) + "]", "    public static let pictureContinueRoutes: [String] = [" + ", ".join(q(value) for value in presentation["picture_continue_routes"]) + "]"]
    kotlin += ["    )", "    val featuredIDs: List<String> = listOf(" + ", ".join(q(value) for value in presentation["featured_ids"]) + ")", "    val pictureContinueRoutes: List<String> = listOf(" + ", ".join(q(value) for value in presentation["picture_continue_routes"]) + ")"]
    for key, name in (("notice", "previewNotice"), ("start_label", "startLabel"), ("more_features_label", "moreFeaturesLabel"), ("help_label", "helpLabel")):
        swift += [f"    public static let {name} = {q(presentation[key])}"]
        kotlin += [f"    const val {name} = {q(presentation[key])}"]
    swift += ["}", "public struct AQSSTutorialChoice: Equatable, Sendable {", "    public let id, title, icon, detail: String", "}", "public struct AQSSConnectionStage: Equatable, Sendable {", "    public let number: Int", "    public let title, detail: String", "    public let targets: [String]", "}", "public struct AQSSTutorialFeature: Equatable, Sendable {", "    public let id, title, detail, availability: String", "}", ""]
    kotlin += ["}", "data class TutorialChoice(val id: String, val title: String, val icon: String, val detail: String)", "data class ConnectionStage(val number: Int, val title: String, val detail: String, val targets: List<String>)", "data class TutorialFeature(val id: String, val title: String, val detail: String, val availability: String)", ""]
    return {
        ROOT / "native/ios/Sources/AQSSNativeFeedback/TutorialContent.swift": "\n".join(swift),
        ROOT / "native/android/src/main/kotlin/com/aqss/nativefeedback/TutorialContent.kt": "\n".join(kotlin),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    data = validate(json.loads((ROOT / "contracts/tutorial_v1.json").read_text()))
    for path, content in sources(data).items():
        if args.check:
            if not path.exists() or path.read_text() != content:
                raise SystemExit(f"Regenerate tutorial content: {path.relative_to(ROOT)}")
        else:
            path.write_text(content)


if __name__ == "__main__":
    main()
