"""Build an offline, numbered picture companion from the shared native catalog."""
import html
import json
import textwrap
from pathlib import Path
from tools.generate_setup_guides import validate
ROOT = Path(__file__).resolve().parents[1]

def esc(s): return html.escape(str(s), quote=True)
def svg(step, number, route):
    label = step['items'][step['focus']]
    title = f"Picture {number}. {step['screen']}. Highlighted: {label}."
    pieces = [f'<svg viewBox="0 0 640 420" role="img" aria-label="{esc(title)}"><title>{esc(title)}</title>', '<rect width="640" height="420" rx="22" fill="#18253c"/>']
    def rect(x,y,w,h,color): pieces.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{color}"/>')
    def text(x,y,s,color='#f8fbff',size=19): pieces.append(f'<text x="{x}" y="{y}" fill="{color}" font-size="{size}" font-family="Arial,sans-serif">{esc(s)}</text>')
    def row(x,y,w,s,selected):
        rect(x,y,w,48,'#ffffff' if selected else '#243958')
        for j,line in enumerate(textwrap.wrap(s, 25 if w<300 else 42)[:2]): text(x+12,y+21+j*19,(f'{number} → ' if selected and j==0 else '')+line,'#071321' if selected else '#f8fbff',16)
    if route['id'] in ('roku_network','roku_model') and number > 1:
        rect(18,18,604,348,'#063e97');text(36,58,'Roku • Home' if number==2 else 'Roku • Settings',size=27)
        model='System' in step['screen']
        left=['Home','Settings','Streaming Store'] if number==2 else ['Accessibility','Audio','Home screen','System','Power'] if model else ['Network','Remotes & devices','Theme','Display type','TV inputs']
        right=step['items'] if number==5 else ['About','Power','System update'] if model else ['About','Check connection','Set up connection','Bandwidth saver']
        for i,s in enumerate(left): row(36,80+i*54,272,s,(number==2 and s=='Settings') or (number==3 and s==('System' if model else 'Network')))
        if number>=3:
            for i,s in enumerate(right):row(324,80+i*54,272,s,number==4 and s=='About' or number==5 and i==step['focus'])
    elif route['id']=='philips_voice_remote' and number in (2,3):
        text(30,54,'Google TV',size=25);row(418,25,195,'Profile',number==2)
        text(30,110,'For you · Apps');rect(30,142,125,78,'#243958');rect(169,142,125,78,'#243958');rect(307,142,96,78,'#243958')
        if number==3:
            rect(415,88,195,202,'#243958');text(428,121,'Your account',size=16);row(428,150,170,'Settings',True)
    else:
        text(28,52,step['screen'][:48],size=25)
        for i,item in enumerate(step['items']):row(28,78+i*54,584,item,i==step['focus'])
    text(28,398,('TV remote: arrows + OK' if step['surface']=='tv' else 'TV + phone' if step['surface']=='both' else 'On your phone')+' · '+step['action'],color='#60d8e5',size=19)
    pieces.append('</svg>');return ''.join(pieces)

def build():
    data=validate(json.loads((ROOT/'contracts/setup_guides_v1.json').read_text()))
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
    p=ROOT/'docs/picture-guide.html';t=p.with_suffix('.html.tmp');assert not t.exists();t.write_text(''.join(out));t.replace(p)
    print(f'{len(routes)} routes / {sum(len(r["steps"]) for r in routes.values())} numbered pictures; {p.stat().st_size} bytes')
if __name__=='__main__':build()
