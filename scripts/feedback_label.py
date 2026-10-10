#!/usr/bin/env python3
"""LLM 抽样标注：为每个项目抽样（评论：均匀随机 + 按赞加权；弹幕：均匀随机），把未标注的条目分批交给 LLM 判断
情感(pos/neu/neg)与话题，结果缓存到 tmp/feedback_labels/<pid>.json（key=文本 sha1），日更只标新条目。
用法: python3 scripts/feedback_label.py [--only competitors|others|all] [--ids a,b] [--nu 150 --nw 100 --nd 100] [--batch 120] [--max-calls 40]"""
import sys, os, re, json, glob, random, hashlib, argparse, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import feedback_analysis as F
LD = 'tmp/feedback_labels'
TOP = list(F.TOPICS)
def h(t): return hashlib.sha1(t.encode()).hexdigest()[:16]

def sample(pid, a, nu, nw, nd, seed=20261010):
    r = random.Random(f'{seed}-{pid}')
    cs = [c for c in a['allc'] if len(c['text'].strip()) >= 2]
    U = r.sample(cs, min(nu, len(cs)))
    # 按赞加权（无放回，权重 like+1）
    pool = list(cs); W = []
    for _ in range(min(nw, len(pool))):
        tot = sum(c['like'] + 1 for c in pool); x = r.uniform(0, tot); acc = 0
        for i, c in enumerate(pool):
            acc += c['like'] + 1
            if acc >= x: W.append(pool.pop(i)); break
    D = r.sample([t for t in a['dm_all'] if t.strip()], min(nd, len([t for t in a['dm_all'] if t.strip()])))
    return U, W, D

def load(pid): return F.jl(f'{LD}/{pid}.json') or {}

PROMPT = ('你是游戏舆情标注员。下面是关于同一款游戏《{name}》的 B站评论/弹幕/Steam 评测等。逐条判断发言者对【这款游戏】的态度：'
 'pos=好评/期待/支持/夸奖；neg=批评/失望/嘲讽/劝退/质疑；neu=中性/提问/无关/玩梗看不出态度。'
 '再给 0-3 个话题代号：' + ' '.join(f'{i}={t}' for i, t in enumerate(TOP)) + '。'
 '每行严格输出「编号|pos或neu或neg|话题代号逗号分隔(可空)」，不要解释，不要漏行。\n\n')

def call(name, items):
    p = PROMPT.format(name=name) + '\n'.join(f'{i}. {F.clean(t, 150)}' for i, t in enumerate(items))
    try:
        out = subprocess.run(['/home/box/bin/freeai', 'openrouter', 'nvidia/nemotron-3-super-120b-a12b:free', p],
                             capture_output=True, text=True, timeout=600).stdout
    except Exception as e:
        return {}
    res = {}
    for i, s, t in re.findall(r'^\s*(\d+)\s*[|｜]\s*(pos|neu|neg)\s*[|｜]?\s*([\d,，\s]*)$', out, re.M):
        i = int(i)
        if i < len(items):
            res[i] = (s, [TOP[int(x)] for x in re.findall(r'\d+', t) if int(x) < len(TOP)])
    return res

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--only', default='competitors'); ap.add_argument('--ids', default='')
    ap.add_argument('--nu', type=int, default=150); ap.add_argument('--nw', type=int, default=100); ap.add_argument('--nd', type=int, default=100)
    ap.add_argument('--batch', type=int, default=120); ap.add_argument('--max-calls', type=int, default=40)
    o = ap.parse_args(); os.makedirs(LD, exist_ok=True)
    files = sorted(f for f in glob.glob('state/*.md'))
    F.OWN_BV = {os.path.basename(f)[:-3] for f in files if os.path.basename(f).startswith('BV')}
    ids = set(filter(None, o.ids.split(','))); calls = 0
    for f in files:
        pid = os.path.basename(f)[:-3]; md = open(f, encoding='utf-8').read()
        comp = bool(re.search(r'^competitor:\s*true', md, re.M))
        if ids and pid not in ids: continue
        if o.only == 'competitors' and not comp: continue
        if o.only == 'others' and comp: continue
        a = F.analyze(pid, md)
        if not a: continue
        U, W, D = sample(pid, a, o.nu, o.nw, o.nd)
        lab = load(pid)
        todo = list(dict.fromkeys([c['text'] for c in U + W] + D))
        todo = [t for t in todo if h(t) not in lab]
        name = F.front(md)[0].get('name', pid)
        for i in range(0, len(todo), o.batch):
            if calls >= o.max_calls: print('max calls reached'); break
            chunk = todo[i:i + o.batch]; res = call(name, chunk); calls += 1
            for j, (s, t) in res.items(): lab[h(chunk[j])] = {'s': s, 't': t, 'by': 'llm:nemotron-3-super', 'x': chunk[j][:80]}
            json.dump(lab, open(f'{LD}/{pid}.json', 'w'), ensure_ascii=False, indent=0)
            print(pid, f'batch {i//o.batch} labeled {len(res)}/{len(chunk)}', flush=True)
        if calls >= o.max_calls: break
    print('calls', calls)

if __name__ == '__main__': main()
