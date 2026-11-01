"""Generate identical, local-only illustrated setup catalogs for both phones."""
import argparse
from datetime import date
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
HOSTS = {'www.samsung.com', 'www.lg.com', 'www.sony.com', 'support.tcl.com',
         'www.tcl.com', 'us.tcl.com', 'ca-en.tcl.com',
         'support.roku.com', 'image.roku.com', 'assets.hisense-usa.com',
         'www.vizio.com', 'support.google.com', 'www.amazon.com',
         'digprjsurvey.amazon.com', 'github.com', 'www.usa.philips.com', 'support.apple.com'}
ACTIONS = {'home', 'settings', 'select', 'tap', 'scan', 'type', 'check', 'speak', 'stop', 'wait', 'hold'}
PICTURE_SURFACES = {'tv', 'phone', 'both', 'remote', 'choice'}


def validate(data):
    if set(data) != {'schema_version', 'mode', 'reviewed_at', 'sources', 'groups', 'routes'} or data['schema_version'] != 1 or data['mode'] != 'illustrated_guidance_only':
        raise ValueError('invalid guidance contract')
    if type(data['reviewed_at']) is not str or date.fromisoformat(data['reviewed_at']).isoformat() != data['reviewed_at']:
        raise ValueError('review date required')
    def text(value, limit=600):
        if not isinstance(value, str) or not value.strip() or len(value) > limit or any(ord(c) < 32 for c in value):
            raise ValueError('invalid bounded text')
    def ids(items):
        if not isinstance(items, list) or not 1 <= len(items) <= 80:
            raise ValueError('invalid catalog size')
        result = set()
        for item in items:
            key = item.get('id')
            if not isinstance(key, str) or not re.fullmatch('[a-z][a-z0-9_]*', key) or key in result:
                raise ValueError('invalid or duplicate identifier')
            result.add(key)
        return result
    source_ids = ids(data['sources']); route_ids = ids(data['routes']); ids(data['groups'])
    for source in data['sources']:
        if set(source) != {'id', 'title', 'url'}:
            raise ValueError('invalid source')
        text(source['title']); text(source['url'])
        url = urlsplit(source['url'])
        if url.scheme != 'https' or url.hostname not in HOSTS or url.username or url.password or url.port not in (None, 443):
            raise ValueError('official HTTPS source required')
    for group in data['groups']:
        if set(group) - {'phone_route'} != {'id', 'title', 'routes', 'primary_routes'}:
            raise ValueError('invalid group')
        text(group['title'])
        if not group['routes'] or not set(group['routes']) <= route_ids or len(group['routes']) != len(set(group['routes'])):
            raise ValueError('unknown or duplicate guide')
        primary = group['primary_routes']
        if not isinstance(primary, list) or not 1 <= len(primary) <= 3 or len(primary) != len(set(primary)) or not set(primary) <= set(group['routes']):
            raise ValueError('bounded primary guides required')
        if 'phone_route' in group and (not isinstance(group['phone_route'], str) or group['phone_route'] not in group['routes']):
            raise ValueError('phone companion must belong to its TV group')
    for route in data['routes']:
        if set(route) - {'progress_version', 'pairing_route'} != {'id', 'title', 'applies_to', 'models', 'sources', 'steps'}:
            raise ValueError('presentation fields only')
        if type(route.get('progress_version', 1)) is not int or not 1 <= route.get('progress_version', 1) <= 999:
            raise ValueError('bounded guide progress version required')
        if 'pairing_route' in route and (not isinstance(route['pairing_route'], str) or route['pairing_route'] not in route_ids or route['pairing_route'] == route['id']):
            raise ValueError('known separate pairing guide required')
        text(route['title']); text(route['applies_to'])
        if not isinstance(route['models'], list) or len(route['models']) > 16:
            raise ValueError('invalid model evidence')
        for model in route['models']: text(model, 80)
        if not route['sources'] or not set(route['sources']) <= source_ids:
            raise ValueError('source evidence required')
        if not isinstance(route['steps'], list) or not 4 <= len(route['steps']) <= 30:
            raise ValueError('bounded chronological steps required')
        for step in route['steps']:
            if set(step) - {'picture_surface'} != {'title', 'instruction', 'surface', 'screen', 'items', 'focus', 'action', 'note'}:
                raise ValueError('presentation steps only')
            for key in ('title', 'instruction', 'screen', 'note'): text(step[key])
            if step['surface'] not in {'tv', 'phone', 'both'} or step['action'] not in ACTIONS:
                raise ValueError('unknown picture action')
            if not isinstance(step.get('picture_surface', step['surface']), str) or step.get('picture_surface', step['surface']) not in PICTURE_SURFACES:
                raise ValueError('unknown picture surface')
            if not isinstance(step['items'], list) or not 1 <= len(step['items']) <= 5:
                raise ValueError('bounded screen rows required')
            for item in step['items']: text(item, 100)
            if type(step['focus']) is not int or not 0 <= step['focus'] < len(step['items']):
                raise ValueError('highlight must identify one visible action')
            if step.get('picture_surface') == 'choice' and (len(step['items']) < 2 or step['action'] != 'check'):
                raise ValueError('a choice picture must review two or more options')
    by_id = {route['id']: route for route in data['routes']}
    for group in data['groups']:
        if 'phone_route' in group:
            companion = by_id[group['phone_route']]
            if any(step['surface'] != 'phone' for step in companion['steps']):
                raise ValueError('phone companion must contain phone steps only')
            if companion.get('pairing_route') not in group['routes']:
                raise ValueError('phone companion must return to pairing in its TV group')
    return data


def sources(data):
    q = lambda s: json.dumps(s, ensure_ascii=False)
    kq = lambda s: q(s).replace('$', r'\$')
    fields = ('title', 'instruction', 'surface', 'screen', 'items', 'focus', 'action', 'note')
    swift = ['// Generated by tools/generate_setup_guides.py. Do not edit.',
             'public struct AQSSSetupSource: Equatable, Sendable { public let id, title, url: String }',
             'public struct AQSSSetupGroup: Equatable, Sendable { public let id, title: String; public let routes, primaryRoutes: [String]; public var phoneRoute: String? = nil }',
             'public struct AQSSSetupStep: Equatable, Sendable { public let title, instruction, surface, screen: String; public let items: [String]; public let focus: Int; public let action, note: String; public var pictureSurface: String = ""; public var pictureKind: String { pictureSurface.isEmpty ? surface : pictureSurface }; public var focusLabel: String { pictureKind == "choice" ? items.joined(separator: " or ") : items[focus] } }',
             'public struct AQSSSetupRoute: Equatable, Sendable { public let id, title, appliesTo: String; public let models, sources: [String]; public let steps: [AQSSSetupStep]; public var progressVersion: Int = 1; public var pairingRoute: String? = nil; public var bookmarkID: String { progressVersion == 1 ? id : "\\(id)@v\\(progressVersion)" } }',
             'public enum AQSSSetupContent {', '    public static let reviewedAt = '+q(data['reviewed_at']),
             '    public static let sources: [AQSSSetupSource] = [']
    kotlin = ['// Generated by tools/generate_setup_guides.py. Do not edit.', 'package com.aqss.nativefeedback',
              'data class SetupSource(val id: String, val title: String, val url: String)',
              'data class SetupGroup(val id: String, val title: String, val routes: List<String>, val primaryRoutes: List<String>, val phoneRoute: String? = null)',
              'data class SetupStep(val title: String, val instruction: String, val surface: String, val screen: String, val items: List<String>, val focus: Int, val action: String, val note: String, val pictureSurface: String = surface) { val pictureKind get() = pictureSurface; val focusLabel get() = if (pictureKind == "choice") items.joinToString(" or ") else items[focus] }',
              'data class SetupRoute(val id: String, val title: String, val appliesTo: String, val models: List<String>, val sources: List<String>, val steps: List<SetupStep>, val progressVersion: Int = 1, val pairingRoute: String? = null) { val bookmarkID get() = if (progressVersion == 1) id else "$id@v$progressVersion" }',
              'object SetupContent {', '    const val reviewedAt = '+q(data['reviewed_at']),
              '    val sources: List<SetupSource> = listOf(']
    for source in data['sources']:
        swift += ['        AQSSSetupSource(' + ', '.join(k+': '+q(source[k]) for k in ('id','title','url')) + '),']
        kotlin += ['        SetupSource(' + ', '.join(kq(source[k]) for k in ('id','title','url')) + '),']
    swift += ['    ]', '    public static let groups: [AQSSSetupGroup] = [']
    kotlin += ['    )', '    val groups: List<SetupGroup> = listOf(']
    for group in data['groups']:
        swift += [f"        AQSSSetupGroup(id: {q(group['id'])}, title: {q(group['title'])}, routes: {q(group['routes'])}, primaryRoutes: {q(group['primary_routes'])}, phoneRoute: {q(group['phone_route']) if group.get('phone_route') else 'nil'}),"]
        kotlin += [f"        SetupGroup({kq(group['id'])}, {kq(group['title'])}, listOf({', '.join(kq(x) for x in group['routes'])}), listOf({', '.join(kq(x) for x in group['primary_routes'])}), {kq(group['phone_route']) if group.get('phone_route') else 'null'}),"]
    swift += ['    ]', '    public static let routes: [AQSSSetupRoute] = [']
    kotlin += ['    )', '    val routes: List<SetupRoute> = listOf(']
    for route in data['routes']:
        swift += [f"        AQSSSetupRoute(id: {q(route['id'])}, title: {q(route['title'])}, appliesTo: {q(route['applies_to'])}, models: {q(route['models'])}, sources: {q(route['sources'])}, steps: ["]
        kotlin += [f"        SetupRoute({kq(route['id'])}, {kq(route['title'])}, {kq(route['applies_to'])}, listOf({', '.join(kq(x) for x in route['models'])}), listOf({', '.join(kq(x) for x in route['sources'])}), listOf("]
        for step in route['steps']:
            swift += ['            AQSSSetupStep(' + ', '.join(k+': '+q(step[k]) for k in fields) + ', pictureSurface: '+q(step.get('picture_surface', step['surface']))+'),']
            args = [str(step[k]) if k == 'focus' else 'listOf('+', '.join(kq(x) for x in step[k])+')' if k == 'items' else kq(step[k]) for k in fields]
            kotlin += ['            SetupStep(' + ', '.join(args) + ', '+kq(step.get('picture_surface', step['surface']))+'),']
        swift += [f"        ], progressVersion: {route.get('progress_version', 1)}, pairingRoute: {q(route['pairing_route']) if route.get('pairing_route') else 'nil'}),"]
        kotlin += [f"        ), {route.get('progress_version', 1)}, {kq(route['pairing_route']) if route.get('pairing_route') else 'null'}),"]
    swift += ['    ]', '}', '']; kotlin += ['    )', '}', '']
    return {ROOT/'native/ios/Sources/AQSSNativeFeedback/SetupContent.swift': '\n'.join(swift), ROOT/'native/android/src/main/kotlin/com/aqss/nativefeedback/SetupContent.kt': '\n'.join(kotlin)}


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--check', action='store_true'); args = parser.parse_args()
    data = validate(json.loads((ROOT/'contracts/setup_guides_v1.json').read_text()))
    for path, content in sources(data).items():
        if args.check:
            if not path.exists() or path.read_text() != content: raise SystemExit(f'Regenerate {path}')
        else: path.write_text(content)


if __name__ == '__main__': main()
