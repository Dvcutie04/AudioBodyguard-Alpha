"""Build an offline, numbered picture companion from the shared native catalog."""
import argparse
import html
import json
import textwrap
from pathlib import Path
if __package__ in (None, ""):
    from generate_setup_guides import validate
else:
    from .generate_setup_guides import validate
ROOT = Path(__file__).resolve().parents[1]
TV_SCREEN_PICTURES = {
    route['id']: {n for n, step in enumerate(route['steps'], 1)
                  if step['surface'] == 'both' and step.get('picture_surface') == 'tv'}
    for route in json.loads((ROOT/'contracts/setup_guides_v1.json').read_text())['routes']
}
TV_SCREEN_PICTURES = {key: value for key, value in TV_SCREEN_PICTURES.items() if value}

def esc(s): return html.escape(str(s), quote=True)
def svg(step, number, route):
    label = step['items'][step['focus']]
    kind = step.get('picture_surface', step['surface'])
    if kind == 'choice': label = 'Choose one: ' + ' or '.join(step['items'])
    title = f"Picture {number}. {step['screen']}. Highlighted: {label}."
    pieces = [f'<svg viewBox="0 0 640 420" role="img" aria-label="{esc(title)}"><title>{esc(title)}</title>', '<rect width="640" height="420" rx="22" fill="#18253c"/>']
    def rect(x,y,w,h,color): pieces.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{color}"/>')
    def text(x,y,s,color='#f8fbff',size=19): pieces.append(f'<text x="{x}" y="{y}" fill="{color}" font-size="{size}" font-family="Arial,sans-serif">{esc(s)}</text>')
    def row(x,y,w,s,selected,numbered=True):
        rect(x,y,w,48,'#ffffff' if selected else '#243958')
        # Wrap the numbered target as one label: its prefix also occupies space.
        # Narrow remote buttons need a shorter line than the Roku menu rows.
        label = (f'{number} → ' if selected and numbered else '') + s
        lines = textwrap.wrap(label, 17 if w<200 else 25 if w<300 else 42)
        if len(lines) > 2:
            raise ValueError('Picture row exceeds its two-line text bound')
        for j,line in enumerate(lines): text(x+12,y+21+j*19,line,'#071321' if selected else '#f8fbff',16)
    if route['id'] in ('roku_network','roku_model') and number > 1:
        rect(18,18,604,348,'#063e97');text(36,58,step['screen'],size=27)
        model=route['id']=='roku_model'
        left=['Home','Settings','Streaming Store'] if number==2 else ['Accessibility','Audio','Home screen','System','Power'] if model else ['Network','Remotes & devices','Theme','Display type','TV inputs']
        right=step['items'] if number==5 else ['About','Power','System update'] if model else ['About','Check connection','Set up connection','Bandwidth saver']
        for i,s in enumerate(left): row(36,80+i*54,272,s,(number==2 and s=='Settings') or (number==3 and s==('System' if model else 'Network')))
        if number>=3:
            for i,s in enumerate(right):row(324,80+i*54,272,s,number==4 and s=='About' or number==5 and i==step['focus'])
    elif kind == 'tv' and step['surface'] != 'tv':
        text(28,52,'On your TV: '+step['screen'][:34],size=22)
        rect(28,78,420,260,'#243958');text(48,113,'TV screen',size=19)
        row(48,142,380,label,True)
        rect(216,338,44,12,'#536c96');rect(178,350,120,7,'#536c96')
        if step['action']=='check':text(466,166,'Check the TV',size=18)
        else:
            text(458,115,'Phone camera' if step['action']=='scan' else 'Phone app',size=17)
            rect(476,140,128,192,'#243958')
            text(491,195,'Scan the' if step['action']=='scan' else 'Follow',size=18)
            text(491,221,'TV code' if step['action']=='scan' else 'TV setup',size=18)
    elif route['id']=='philips_voice_remote' and number in (2,3):
        text(30,54,'Google TV',size=25);row(418,25,195,'Profile',number==2)
        text(30,110,'For you · Apps');rect(30,142,125,78,'#243958');rect(169,142,125,78,'#243958');rect(307,142,96,78,'#243958')
        if number==3:
            rect(415,88,195,202,'#243958');text(428,121,'Your account',size=16);row(428,150,170,'Settings',True)
    elif kind == 'choice':
        text(28,52,step['screen'],size=25)
        row(28,78,584,'Choose one',True)
        for i,item in enumerate(step['items']):row(28,140+i*54,584,item,False)
    elif kind == 'remote':
        text(28,42,step['screen'],size=23)
        rect(208,60,224,308,'#536c96');rect(216,68,208,292,'#0c172c')
        buttons = label.split(' + ')
        if len(buttons) > 1:
            text(28,104,f'{number} → Hold together',size=17)
            for i,button in enumerate(buttons):row(228,132+i*74,184,button,True,False)
        else:row(228,150,184,label,True)
        text(250,337,'TV remote',size=16)
    else:
        phone = kind == 'phone'
        x,w = (92,456) if phone else (18,604)
        rect(x,18,w,342,'#536c96');rect(x+6,24,w-12,330,'#0c172c')
        text(x+18,52,('On your TV: ' if kind=='tv' else '')+step['screen'],size=22 if phone else 20)
        text(x+w-140,380,'Phone screen' if phone else 'TV screen' if kind=='tv' else 'TV + phone',size=12)
        for i,item in enumerate(step['items']):row(x+18,78+i*54,w-36,item,i==step['focus'])
        if kind == 'tv':rect(292,360,56,12,'#536c96');rect(250,372,140,6,'#536c96')
        elif phone:rect(286,344,68,4,'#536c96')
        elif kind == 'both' and len(step['items']) <= 2:
            rect(80,236,210,100,'#243958');rect(173,336,24,10,'#536c96')
            rect(420,214,82,132,'#243958');text(114,276,'TV',size=21);text(430,276,'Phone',size=14)
    text(28,398,('TV remote: arrows + OK' if step['surface']=='tv' else 'TV + phone' if step['surface']=='both' else 'On your phone')+' · '+step['action'],color='#60d8e5',size=19)
    pieces.append('</svg>');return ''.join(pieces)

def render(data):
    routes={r['id']:r for r in data['routes']};sources={s['id']:s for s in data['sources']}
    out=['<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Audio Bodyguard picture directions</title><style>body{margin:0;background:#080f20;color:#f5f8ff;font:18px/1.55 system-ui}main{max-width:1040px;margin:auto;padding:24px}a{color:#61dbe8}h1,h2,h3{line-height:1.2}nav{display:flex;flex-wrap:wrap;gap:12px}nav a,summary{padding:14px;background:#1b2943;border:1px solid #536c96;border-radius:12px}section{margin:30px 0}details{margin:14px 0}summary{cursor:pointer;font-weight:700}ol{padding:0;list-style:none}.step{padding:20px;margin:16px 0;border:1px solid #536c96;border-radius:16px;background:#111c30}svg{display:block;width:100%;max-width:680px;height:auto}.badge{color:#61dbe8}.note{color:#b8c6df;font-size:16px}button{padding:12px;font:inherit}*:focus-visible{outline:3px solid #fff}@media print{body{background:white;color:black}.step{break-inside:avoid;background:white}nav{display:none}}</style><main><h1>Follow one highlighted picture at a time</h1><p>Choose your TV brand or app, then the menu that matches your device. Complete each action on your TV or official app. The numbered white highlight marks the next choice.</p><p class="note">These are diagrams, not photographs of every firmware version. Roku Settings uses the menu arrangement in the supplied photo. Model examples are documented examples, not a claim of exact artwork or Audio Bodyguard compatibility. Account approval and remote pairing happen in the official TV/app; this companion never connects or controls a device.</p><nav aria-label="TV brands and apps">']
    groups=[g for g in data['groups'] if g['id'] not in ('both','neither') and '_' not in g['id']]
    for g in groups:out.append(f'<a href="#brand-{esc(g["id"])}">{esc(g["title"])}</a>')
    out.append('</nav>')
    for g in groups:
        out.append(f'<section id="brand-{esc(g["id"])}"><h2>{esc(g["title"])}</h2><p>Match the operating system, model, or menu name before choosing a guide.</p>')
        platforms=[p for p in data['groups'] if p['id'].startswith(g['id']+'_')]
        for platform in platforms or [g]:
            if platforms:out.append(f'<details><summary>{esc(platform["title"])}</summary>')
            out.append('<ul>')
            for id in platform['routes']:out.append(f'<li><a href="#guide-{esc(id)}">{esc(routes[id]["title"])}</a></li>')
            out.append('</ul>')
            if platforms:out.append('</details>')
        out.append('</section>')
    out.append('<h2>Picture directions</h2>')
    for r in data['routes']:
        out.append(f'<details id="guide-{esc(r["id"])}"><summary>{esc(r["title"])} · {len(r["steps"])} pictures</summary><p>{esc(r["applies_to"])}</p>')
        if r['models']:out.append('<p>Documented model examples: '+esc(', '.join(r['models']))+'</p>')
        out.append('<ol>')
        for i,s in enumerate(r['steps'],1):
            out.append(f'<li class="step"><p class="badge">Step {i} of {len(r["steps"])} · {esc(s["surface"])}</p><h3>{esc(s["title"])}</h3><p>{esc(s["instruction"])}</p>{svg(s,i,r)}<p class="note">Look for the number {i} in this picture. {esc(s["note"])}</p></li>')
        out.append('</ol><p>Official sources:</p><ul>')
        for id in r['sources']:out.append(f'<li><a href="{esc(sources[id]["url"])}">{esc(sources[id]["title"])}</a></li>')
        out.append('</ul><a href="#">Back to brands</a></details>')
    out.append('''<script>function reveal(){const el=document.getElementById(location.hash.slice(1));if(el&&el.tagName==='DETAILS'){el.open=true;el.scrollIntoView();}}addEventListener('hashchange',reveal);reveal();</script></main></html>''')
    return ''.join(out)


def build(*, check=False):
    data = validate(json.loads((ROOT/'contracts/setup_guides_v1.json').read_text(encoding='utf-8')))
    content = render(data)
    path = ROOT/'docs/picture-guide.html'
    if check:
        if not path.is_file() or path.read_bytes() != content.encode('utf-8'):
            raise SystemExit(f'Regenerate {path}')
        print('OFFLINE_PICTURE_GUIDE_CURRENT')
        return
    temporary = path.with_suffix('.html.tmp')
    assert not temporary.exists()
    temporary.write_text(content, encoding='utf-8')
    temporary.replace(path)
    print(f'{len(data["routes"])} routes / {sum(len(r["steps"]) for r in data["routes"])} numbered pictures; {path.stat().st_size} bytes')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    build(check=parser.parse_args().check)
