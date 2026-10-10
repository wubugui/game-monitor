#!/usr/bin/env python3
"""Backfill 来源 metadata/attribution into state/*.md (idempotent). Never invents: unknown -> 未知."""
import json, os, re, glob, datetime
os.chdir(os.path.join(os.path.dirname(__file__), '..'))
def ts(t):
    try: return datetime.datetime.fromtimestamp(int(t)).strftime('%Y-%m-%d')
    except Exception: return '未知'
def wan(n):
    try: n=int(n)
    except Exception: return str(n)
    return f'{n/10000:.1f}万' if n>=10000 else str(n)
strip=lambda s: re.sub(r'<[^>]+>','',s or '')
# --- video meta + discovery evidence
meta, kw, rel, disc, discname = {}, {}, {}, {}, {}
for l in open('raw/search.jsonl'):
    try: d=json.loads(l)
    except Exception: continue
    b=d.get('bvid')
    if not b: continue
    kw.setdefault(b, []).append(d.get('_kw'))
    meta.setdefault(b, dict(title=strip(d.get('title')), up=d.get('author'), date=ts(d.get('pubdate')), play=d.get('play')))
for l in open('raw/related.jsonl'):
    try: d=json.loads(l)
    except Exception: continue
    b=d.get('bvid'); rel.setdefault(b, d.get('_src'))
    meta.setdefault(b, dict(title=d.get('title'), up=(d.get('owner') or {}).get('name'), date=ts(d.get('pubdate')), play=(d.get('stat') or {}).get('view')))
for f in glob.glob('tmp/discover_*.json'):
    day=re.search(r'\d{4}-\d\d-\d\d',f).group(0)
    for c in json.load(open(f)).get('cands',[]):
        disc.setdefault(c['bvid'], (c.get('q'), day))
        meta.setdefault(c['bvid'], dict(title=c.get('title'), up=c.get('author'), date=ts(c.get('pub')), play=c.get('play')))
    for gname, cs in (json.load(open(f)).get('games') or {}).items():
        for c in cs:
            discname.setdefault(gname, (c.get('q'), day, c))
for f in glob.glob('tmp/comments/*_view.json'):
    b=os.path.basename(f)[:-10]
    try: d=json.load(open(f)); d=d.get('data',d)
    except Exception: continue
    if d.get('title'):
        meta[b]=dict(title=d['title'], up=(d.get('owner') or {}).get('name'), date=ts(d.get('pubdate')), play=(d.get('stat') or {}).get('view'))
# --- quote index
norm=lambda s: re.sub(r'[\s\W_]+','',s)[:24]
qidx={}
for f in glob.glob('tmp/comments/*_reply_p*.json')+glob.glob('tmp/comments/*_sub_*.json'):
    b=os.path.basename(f).split('_')[0]
    try: d=json.load(open(f))
    except Exception: continue
    def walk(rs):
        for r in rs or []:
            m=(r.get('content') or {}).get('message','')
            k=norm(m)
            if len(k)>=4: qidx.setdefault(k,(b,'评论'))
            walk(r.get('replies'))
    dd=d.get('data') or {}
    walk(dd.get('replies')); walk(dd.get('top_replies'))
for f in glob.glob('tmp/comments/*_dm.xml'):
    b=os.path.basename(f).split('_')[0]
    for m in re.findall(r'<d [^>]*>([^<]*)</d>', open(f,errors='ignore').read()):
        k=norm(m)
        if len(k)>=4: qidx.setdefault(k,(b,'弹幕'))
steamtxt=''
for f in glob.glob('raw/steam/*')+glob.glob('raw/comp/steam_*'):
    try: steamtxt+=norm(open(f,errors='ignore').read().encode().decode('unicode_escape','ignore')) if False else re.sub(r'[\s\W_]+','',open(f,errors='ignore').read())
    except Exception: pass
xhstxt=''.join(re.sub(r'[\s\W_]+','',open(f).read()) for f in glob.glob('tmp/xhs*.md')+glob.glob('xhs/*.md'))
def find_q(q):
    k=norm(q)
    if len(k)<4: return None
    if k in qidx: b,t=qidx[k]; return f'〔B站·{b}{t}〕'
    if len(k)>=8:
        for kk,(b,t) in qidx.items():
            if kk.startswith(k[:12]) and len(k)>=12 or (len(kk)>=12 and k.startswith(kk)): return f'〔B站·{b}{t}〕'
    if len(k)>=6 and k[:16] in steamtxt: return '〔Steam评测〕'
    if len(k)>=6 and k[:16] in xhstxt: return '〔小红书笔记〕'
    return None
PLAT_ORDER=['B站','小红书','X','Steam','TapTap','用户指定']
stats=dict(files=0, unknown=0, tagged=0, untagged=0)
unknown_list=[]
for path in sorted(glob.glob('state/*.md')):
    txt=open(path).read()
    m=re.match(r'---\n(.*?)\n---\n', txt, re.S)
    fm=m.group(1) if m else ''
    pid=(re.search(r'^id:\s*(.+)$',fm,re.M) or [None,os.path.basename(path)[:-3]])[1].strip()
    names=[x.strip(' "') for x in re.findall(r'^name:\s*(.+)$',fm,re.M)]+[x.strip(' "\'') for x in ((re.search(r'^aliases:\s*\[(.*)\]',fm,re.M) or [None,''])[1].split(',')) if x.strip()]
    found=(re.search(r'^found:\s*(\S+)',fm,re.M) or [None,'未知'])[1]
    link=(re.search(r'^link:\s*(\S+)',fm,re.M) or [None,''])[1]
    seed=pid if pid.startswith('BV') else (re.search(r'BV\w{10}',link) or [None])[0] if re.search(r'BV\w{10}',link) else None
    # discovery
    plat, how = '未知', '未知'
    if pid=='***': plat,how='用户指定','用户自研项目（***Story / *** 仓库）'
    elif pid=='jianguilu-yinhunjie': plat,how='B站','B站同名核验滚雪：在竞品《见诡》播放前五核验中发现其 top1 实为本作（Gluneko 实况，8.5万播放），2026-10-09 经用户确认单独建档'
    elif seed:
        mm=meta.get(seed,{})
        desc=f"种子视频「{mm.get('title','未知')}」· UP {mm.get('up','未知')} · {seed} · {mm.get('date','未知')} · 播放 {wan(mm.get('play','未知'))}"
        if seed in disc: plat,how='B站',f"B站搜索关键词「{disc[seed][0]}」（每日发现 {disc[seed][1]}）；{desc}"
        elif seed in kw:
            ks=[k for k in dict.fromkeys(kw[seed]) if k]
            plat,how='B站',f"B站搜索关键词「{'」「'.join(ks[:3]) or '未知'}」；{desc}"
        elif seed in rel: plat,how='B站',f"B站相关视频滚雪（由 {rel[seed]} 的相关推荐发现）；{desc}"
        elif any(n in discname for n in names):
            q,day,c=discname[next(n for n in names if n in discname)]
            plat,how='B站',f"B站搜索关键词「{q}」（每日发现 {day}，命中视频「{c.get('title')}」· UP {c.get('author')} · {c.get('bvid')}）；{desc}"
        else: plat,how='B站',f"途径未知（种子为 B站视频）；{desc}" if mm else '途径未知（种子为 B站视频 '+seed+'）'
    if how.startswith('未知') or how.startswith('途径未知'):
        stats['unknown']+=1; unknown_list.append(pid)
    # front matter
    def setfm(fm,k,v):
        line=f'{k}: "{v}"' if k!='discovery_platform' else f'{k}: {v}'
        return re.sub(rf'^{k}:.*$',line,fm,flags=re.M) if re.search(rf'^{k}:',fm,re.M) else fm+'\n'+line
    fm2=setfm(fm,'discovery_platform',plat); fm2=setfm(fm2,'discovery',how.replace('"',"'")); fm2=setfm(fm2,'discovery_date',found)
    body=txt[m.end():] if m else txt
    # inline tags
    out=[]; sec=''
    for line in body.split('\n'):
        if line.startswith('## '): sec=line
        if ('评价' in sec or '小红书' in sec or '玩家' in sec) and '「' in line and '〔' not in line and (line.lstrip().startswith(('-','>','*')) ):
            tags=[]
            for q in re.findall(r'「([^」]{4,})」',line):
                t=find_q(q)
                if t and t not in tags: tags.append(t)
            if not tags and '小红书' in sec: tags=['〔小红书笔记〕']
            if tags: line=line+' '+''.join(tags); stats['tagged']+=1
            else: stats['untagged']+=1
        out.append(line)
        if line.startswith('## 关注度'):
            out.append(''); out.append('〔来源：B站视频页公开计数（登录态 view/stat 接口）；UP 粉丝数来自 UP 主页；采集日见本节标题；每行视频的 BV 见文末「来源」〕')
    body='\n'.join(out)
    body=re.sub(r'\n〔来源：B站视频页公开计数[^\n]*〕\n(?=\n〔来源：B站视频页公开计数)','\n',body)
    # dedupe repeated insertion on rerun
    body=re.sub(r'(〔来源：B站视频页公开计数[^\n]*〕)(\n\n\1)+',r'\1',body)
    body=re.sub(r'\n(?:<!-- added:meta -->\n\n)?## 来源（发现与资料）\n.*?(?=\n## |\Z)','',body,flags=re.S).rstrip('\n')
    # sources list
    bvs=list(dict.fromkeys(re.findall(r'BV[0-9A-Za-z]{10}',body)))
    lines=['','<!-- added:meta -->','','## 来源（发现与资料）','',f'- **发现来源**：〔{plat}〕{how}；入库日 {found}','','**资料来源**：']
    if bvs:
        lines.append(f'- B站视频（{len(bvs)}）：')
        excl=set(re.findall(r'(BV[0-9A-Za-z]{10})[^\n]*\((?:need|no)-',body))|set(b for b in bvs if b not in meta)
        used=[b for b in bvs if b not in excl]
        lines[-1]=f'- B站视频（采用 {len(used)} 条；另 {len(bvs)-len(used)} 条为已剔除同名/弱相关或无元数据，正文已列明）：'
        bvs=used
        for b in bvs[:40]:
            mm=meta.get(b,{})
            lines.append(f"  - {mm.get('title','标题未知')} · {mm.get('up','UP未知')} · {b} · {mm.get('date','日期未知')} · 播放 {wan(mm.get('play','未知'))}")
        if len(bvs)>40: lines.append(f'  - ……另 {len(bvs)-40} 条见正文')
    if re.search(r'Tap ?Tap',body,re.I): lines.append('- TapTap：游戏页（正文中引用）')
    sa=list(dict.fromkeys(re.findall(r'store\.steampowered\.com/app/(\d+)|[Aa]pp ?[Ii][Dd][:： ]*(\d{5,})',body)))
    sa=[a or b for a,b in sa]
    if sa or 'Steam' in body: lines.append('- Steam：商店页/评测' + (f'（AppID {", ".join(sa)}）' if sa else '（正文中引用）'))
    if '小红书' in body: lines.append('- 小红书：登录态搜索笔记（标题/作者/日期/赞见正文「小红书」小节）')
    
    if pid=='***': lines.append('- GitHub：***Story / *** 提交记录（只读）')
    if len(lines)==8: lines.append('- 未知')
    body=body+'\n'+'\n'.join(lines)+'\n'
    open(path,'w').write(f'---\n{fm2.strip()}\n---\n'+body.lstrip('\n') if m else body)
    stats['files']+=1
print(stats); print('unknown:',unknown_list)
import subprocess; subprocess.run(['python3','scripts/xhs_sources.py','--write'])  # itemize 小红书/X sources
