#!/usr/bin/env python3
"""玩家反馈分析：从全部已采集原始数据生成每个项目的「玩家反馈分析」小节。
用法: python3 scripts/feedback_analysis.py [--only competitors|others|all] [--ids a,b] [--date YYYY-MM-DD] [--dry]
数据: tmp/comments (B站评论/楼中楼/弹幕 XML+protobuf 分段), tmp/x/steam + raw/comp (Steam 评测),
      state/*.md 中已带来源标签的非 B站 原话（X / 小红书 / Steam 等）。
幂等：分析块被 <!-- feedback:start/end --> 包裹，重复运行会替换；原文列表折叠进 <details>（只折叠一次）。
高亮：新块前放 <!-- added:DATE -->，块后重放插入点原有的 marker，旧内容高亮范围不变。"""
import re, os, sys, json, glob, collections, argparse, math
import jieba, jieba.analyse
jieba.setLogLevel(60)
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
CM = 'tmp/comments'

# ---------------- data loaders ----------------
def jl(p):
    try: return json.load(open(p, encoding='utf-8'))
    except Exception: return None

def varint(b, i):
    r = s = 0
    while True:
        c = b[i]; i += 1; r |= (c & 0x7f) << s; s += 7
        if c < 0x80: return r, i

def pb_fields(b):
    i = 0; n = len(b)
    while i < n:
        k, i = varint(b, i); f, t = k >> 3, k & 7
        if t == 0: v, i = varint(b, i)
        elif t == 2:
            l, i = varint(b, i); v = b[i:i+l]; i += l
        elif t == 1: v = b[i:i+8]; i += 8
        elif t == 5: v = b[i:i+4]; i += 4
        else: return
        yield f, t, v

def load_dm(bv):
    out = {}
    for p in sorted(glob.glob(f'{CM}/{bv}_dmseg_*.bin')):
        try:
            for f, t, v in pb_fields(open(p, 'rb').read()):
                if f != 1 or t != 2: continue
                e = {}
                for f2, t2, v2 in pb_fields(v):
                    if f2 == 1: e['id'] = v2
                    elif f2 == 2: e['ms'] = v2
                    elif f2 == 7: e['txt'] = v2.decode('utf-8', 'ignore')
                if 'txt' in e: out[e.get('id', len(out))] = (e.get('ms', 0) / 1000, e['txt'])
        except Exception: pass
    x = f'{CM}/{bv}_dm.xml'
    if os.path.exists(x):
        for p, t in re.findall(r'<d p="([^"]*)">([^<]*)</d>', open(x, encoding='utf-8', errors='ignore').read()):
            a = p.split(','); k = a[7] if len(a) > 7 else len(out)
            try: k = int(k)
            except Exception: pass
            out.setdefault(k, (float(a[0]), t))
    return list(out.values())

def load_bili(bv):
    cs = {}
    def add(r, kind):
        try:
            t = r['content']['message'].strip()
            cs[r['rpid']] = dict(text=t, like=int(r.get('like') or 0), src=f'B站·{bv}{kind}', kind='bili')
        except Exception: pass
    for p in glob.glob(f'{CM}/{bv}_reply_p*.json'):
        d = jl(p) or {}
        dd = d.get('data') or {}
        for r in (dd.get('replies') or []) + (dd.get('top_replies') or []):
            add(r, '评论')
            for s in r.get('replies') or []: add(s, '楼中楼')
    for p in glob.glob(f'{CM}/{bv}_sub_*_p*.json'):
        d = jl(p) or {}
        for r in ((d.get('data') or {}).get('replies') or []): add(r, '楼中楼')
    view = (jl(f'{CM}/{bv}_view.json') or {}).get('data') or {}
    return list(cs.values()), load_dm(bv), view

def steam_reviews(appids, slug):
    out = {}; files = []
    if slug: files.append(f'tmp/x/steam/{slug}.json')
    for a in appids:
        files += glob.glob(f'raw/comp/steam_{a}_reviews*.json')
    for p in files:
        d = jl(p)
        if not d: continue
        rev = d.get('rev', d)
        if 'app' in d and appids:
            try:
                app = list(d['app'].values())[0]
                if str(app.get('steam_appid')) not in appids: continue
            except Exception: pass
        for r in rev.get('reviews') or []:
            t = (r.get('review') or '').strip()
            if not t: continue
            out[r.get('recommendationid', t[:40])] = dict(text=t, like=int(r.get('votes_up') or 0),
                src='Steam评测', kind='steam', up=bool(r.get('voted_up')), lang=r.get('language', ''))
    return list(out.values())

QRE = re.compile(r'「([^」\n]{4,600})」([^〔\n]{0,40})〔([^〕\n]{1,80})〕')
def md_quotes(body):
    out = []
    for t, mid, tag in QRE.findall(body):
        if tag.startswith('B站') or 'B站' in tag[:4]: continue
        m = re.search(r'(\d+)\s*赞', mid)
        kind = 'xhs' if '小红书' in tag else 'x' if re.match(r'X|推特|@', tag) or 'X' in tag[:3] else 'steam' if 'Steam' in tag else 'other'
        out.append(dict(text=t, like=int(m.group(1)) if m else 0, src=tag, kind=kind))
    seen = set(); res = []
    for q in out:
        if q['text'] in seen: continue
        seen.add(q['text']); res.append(q)
    return res

# ---------------- classification ----------------
POS = '好玩 喜欢 期待 好评 不错 很棒 牛 厉害 神作 惊艳 优秀 精致 好看 舒服 支持 买了 已购 入了 冲 爱了 感动 绝了 可以的 有意思 有趣 用心 良心 推荐 好耶 吊打 真香 佳作 惊喜 赞 加油 想玩 美 氛围好 太强 顶 给力 漂亮 满分 好听 上头 必买 愿望单 已关注 关注了 还行 好爽 可以啊 顺眼 开心 想要 等不及 好帅 帅 可爱 喜欢这 心动 牛逼 nb 666 太好了 好棒 有味道 有感觉 质量高 高质量 good great love amazing beautiful'.split()
NEG = '垃圾 难玩 失望 无聊 劝退 差评 退款 退了 抄袭 缝合 粗糙 拉胯 拉跨 一般 不行 烂 割韭菜 圈钱 骗 恶心 难看 卡顿 闪退 bug BUG 太贵 不值 尬 敷衍 弃了 弃坑 没意思 摆烂 跑路 换皮 ai味 AI味 广告 别买 坑 雷 毁了 退钱 下头 劣质 失败 不好玩 不推荐 逆天 依托 答辩 算了 差远 不如 没兴趣 一般般 太吵 换皮 又是 不会又 毫无 无感 难绷 绷不住 糊弄 劣 丑 太丑 难受 恶心 不想玩 骗钱 失败 吐槽 槽点 吃相 不期待 毫无吸引 bad boring refund trash'.split()
NEGATORS = '不 没 别 无'
TOPICS = collections.OrderedDict([
 ('画面美术', '画面 美术 画风 建模 立绘 场景 光影 贴图 风格 好看 原画 像素 2D 3D 帧 画质 UI 镜头'.split()),
 ('剧情叙事', '剧情 故事 叙事 结局 世界观 角色 主角 设定 台词 文案 伏笔 演出 人设 线索 推理'.split()),
 ('氛围恐怖', '恐怖 吓 害怕 氛围 诡异 阴森 怕 jump 惊悚 毛骨悚然 渗人 瘆 鬼 心理恐怖 胆小'.split()),
 ('玩法系统', '玩法 操作 解谜 谜题 战斗 手感 机制 难度 关卡 探索 系统 打击 节奏 引导 存档 地图 肉鸽 卡牌'.split()),
 ('优化Bug', '优化 bug BUG 卡顿 闪退 掉帧 配置 帧数 崩溃 显卡 加载 报错 黑屏'.split()),
 ('价格售卖', '价格 定价 多少钱 元 打折 免费 贵 便宜 史低 首发 售价 涨价 dlc DLC 内购'.split()),
 ('AI争议', 'AI ai Ai 人工智能 生成 AIGC 机器 ai味 AI味'.split()),
 ('对比其他', '像 抄 借鉴 致敬 黑神话 纸嫁衣 港诡 烟火 三伏 女鬼桥 寂静岭 生化 港 灵笼 原神 类似 同类 比'.split()),
 ('催更期待', '什么时候 啥时候 发售 上线 期待 催 等 愿望单 demo Demo DEMO 试玩 跳票 正式版 更新'.split()),
 ('题材民俗', '民俗 中式 中国 国产 传统 道士 风水 祭祀 纸人 冥婚 鬼节 香火 符 湘西 民国 中元 阴阳 志怪 神话'.split()),
 ('配音音乐', '配音 声优 音乐 音效 BGM bgm 配乐 声音 CV'.split()),
 ('开发团队', '制作人 开发者 团队 工作室 独立 个人开发 一个人 厂商 发行 官方 制作组'.split()),
])
def sentiment(c):
    if c.get('kind') == 'steam' and 'up' in c: return 'pos' if c['up'] else 'neg'
    t = re.sub(r'^回复 @[^:：]{1,30}\s*[:：]', '', c['text']); low = t.lower()
    p = sum(1 for w in POS if w in t)
    n = sum(1 for w in NEG if w.lower() in low)
    # negated positives: 不好玩/不期待/没意思 already in NEG; 不错 is positive
    for w in ('不好看', '不期待', '不喜欢', '不推荐', '不值得', '不好'):
        if w in t: n += 1; p = max(0, p - 1)
    if re.search(r'[？?]{1,}$', t) and p == n == 0: return 'neu'
    if p > n: return 'pos'
    if n > p: return 'neg'
    return 'neu'

def topics(t):
    return [k for k, ws in TOPICS.items() if any(w in t for w in ws)]

STOP = set('这个 那个 就是 什么 怎么 一个 没有 不是 可以 感觉 还是 真的 但是 因为 所以 自己 他们 我们 你们 现在 已经 还有 这种 这么 那么 如果 然后 其实 有点 一下 时候 知道 觉得 为什么 应该 可能 东西 一样 还是 视频 up UP 回复 doge 笑哭 哈哈 哈哈哈 哈哈哈哈 一点 不会 不能 出来 看看 只是 这样 而且 就是 起来 还要 没有 不要 一直 这是 看到 啥 吗 呢 吧 啊 嗯 呃 the and to of is a it game this'.split())
def keywords(texts, k=15):
    txt = '\n'.join(re.sub(r'\[[^\]]{1,8}\]|回复 @\S+ ?:', ' ', t) for t in texts)
    if not txt.strip(): return []
    c = collections.Counter(w for w in jieba.lcut(txt) if len(w) >= 2 and w not in STOP and not re.fullmatch(r'[\W\d_]+', w))
    return c.most_common(k)

def bar(pct, w=20):
    n = round(pct / 100 * w); return '█' * n + '░' * (w - n)

def mmss(s): s = int(s); return f'{s//60:02d}:{s%60:02d}'

def clean(t, n=160):
    t = re.sub(r'\s+', ' ', t).strip()
    t = t.replace('|', '｜')
    return t if len(t) <= n else t[:n] + '…'

def is_cjk(t): return len(re.findall(r'[\u4e00-\u9fff]', t)) >= max(2, len(t) * 0.15)

# ---------------- project mapping ----------------
def front(md):
    h = md.split('\n---', 1)[0]
    return {k: v.strip() for k, v in re.findall(r'^(\w+):[ \t]*(.*)$', h, re.M)}, (md.split('\n---', 1)[1] if '\n---' in md else md)

def project_bvs(pid, body, own_bv_ids):
    bvs = []
    if pid.startswith('BV'): bvs.append(pid)
    for line in body.split('\n'):
        if re.search(r'相关推荐发现|种子视频|滚雪|对照|同类参考', line): continue
        for b in re.findall(r'BV[0-9A-Za-z]{10}', line):
            if b in own_bv_ids and b != pid: continue  # 另一个项目的主视频
            if b not in bvs and os.path.exists(f'{CM}/{b}_view.json'): bvs.append(b)
    return bvs

# ---------------- analysis ----------------
SENT_ZH = {'pos': '好评', 'neu': '中性', 'neg': '差评'}
AUD = {'题材民俗': '中式民俗/志怪题材爱好者', '氛围恐怖': '恐怖氛围向玩家（含「云玩家」）', '剧情叙事': '重剧情、爱考据的叙事向玩家',
       '玩法系统': '在意手感与机制的核心玩家', '画面美术': '看美术和画风下单的视觉党', 'AI争议': '对 AI 内容敏感的玩家',
       '价格售卖': '价格敏感的 Steam 玩家', '催更期待': '已加愿望单、在等消息的潜在买家', '对比其他': '玩过同类作品、习惯拿来对比的老玩家',
       '优化Bug': '已上手实际游玩的玩家', '配音音乐': '在意视听演出的玩家', '开发团队': '关注开发者本身的支持型观众'}
FD = {'题材民俗': '民俗题材本身就是这批观众的买点，《***》的民国川东、背尸、喊魂、伏煞设定可以更早、更具体地亮出来',
      '氛围恐怖': '观众买的是「怕」的体验，《***》无战斗、靠规矩与撤退的设计要在 PV 里直接演出压迫感',
      '剧情叙事': '叙事向观众会深挖设定，***与***的身份反转是《***》最该提前埋钩子的点',
      '玩法系统': '玩家会盯手感和机制，《***》的解谜与「准备—临场操作—撤退」循环需要实机片段证明，不能只靠美术',
      '画面美术': '第一眼美术决定点击，《***》的 45° 等距画面需要高质量关键帧做封面',
      'AI争议': 'AI 话题会被放大审视，《***》若有 AI 参与的素材要提前想好口径，避免成为评论区主战场',
      '价格售卖': '定价讨论多，说明《***》上线时价格与体量说明要写清楚',
      '优化Bug': '技术问题直接拉低口碑，《***》Demo（Electron 壳）发布前要优先保证稳定',
      '催更期待': '催更多说明早曝光能积累等待人群，《***》可以考虑更早开愿望单',
      '对比其他': '观众习惯拿名作对标，《***》需要一句话讲清和同类的差异',
      '配音音乐': '视听演出被单独讨论，《***》的音效与川渝方言配音可以作为差异点',
      '开发团队': '观众愿意支持开发者本人，《***》作为个人项目可以多做开发日志'}

def analyze(pid, md):
    fm, body = front(md)
    own = OWN_BV
    bvs = project_bvs(pid, body, own)
    cs, dms, views = [], {}, {}
    for b in bvs:
        c, d, v = load_bili(b); cs += c; dms[b] = d; views[b] = v
    appids = set(re.findall(r'store\.steampowered\.com/app/(\d+)', md))
    slug = pid[2:] if pid.startswith('x-') else None
    st = steam_reviews(appids, slug)
    mq = md_quotes(body)
    # drop md-quoted Steam lines if raw Steam present (avoid double count)
    if st: mq = [q for q in mq if q['kind'] != 'steam']
    allc = cs + st + mq
    ndm = sum(len(v) for v in dms.values())
    if not allc and ndm == 0: return None
    for c in allc:
        c['s'] = sentiment(c); c['t'] = topics(c['text'])
    for b, d in dms.items():
        pass
    dm_all = [t for v in dms.values() for _, t in v]
    dm_s = collections.Counter(sentiment({'text': t}) for t in dm_all)
    return dict(pid=pid, fm=fm, bvs=bvs, cs=cs, st=st, mq=mq, allc=allc, dms=dms, dm_all=dm_all, dm_s=dm_s, views=views)

def pct(a, n): return 0 if not n else round(100 * a / n, 1)

def pick(cands, k, used, minlen=6, maxlen=200):
    out = []
    for c in sorted(cands, key=lambda c: -c['like']):
        t = c['text']
        if len(t) < minlen or c['text'] in used: continue
        if re.fullmatch(r'(\[[^\]]+\]|\s|[哈啊草w6]+)+', t): continue
        out.append(c); used.add(t)
        if len(out) >= k: break
    return out

TRC = 'tmp/feedback_tr.json'
_tr = None
def translate(t):
    global _tr
    if _tr is None: _tr = jl(TRC) or {}
    if t in _tr: return _tr[t]
    import subprocess
    try:
        r = subprocess.run(['/home/box/bin/freeai', 'openrouter', 'nvidia/nemotron-3-super-120b-a12b:free',
            '把下面这条游戏玩家评论忠实翻译成简体中文，只输出译文：\n' + t], capture_output=True, text=True, timeout=180)
        z = r.stdout.strip()
        if z and is_cjk(z) and len(z) < len(t) * 3 + 50:
            _tr[t] = z; json.dump(_tr, open(TRC, 'w'), ensure_ascii=False, indent=0); return z
    except Exception: pass
    return None

def qfmt(c):
    if not is_cjk(c['text']) and not c.get('zh') and len(re.findall(r'[A-Za-z\u3040-\u30ff\uac00-\ud7af]', c['text'])) > 5:
        c['zh'] = translate(clean(c['text'], 220))
    t = clean(c['text'], 220)
    if not is_cjk(t) and c.get('zh'):
        t = f"{c['zh']}（原文：{t}）"
    elif not is_cjk(t) and c['kind'] == 'steam':
        t = f"（外文评测，未译）{t}"
    like = f"（{c['like']}赞）" if c['like'] else ''
    return f"- 「{t}」{like} 〔{c['src']}〕"

def render(a, date):
    allc, n = a['allc'], len(a['allc'])
    src = collections.Counter()
    for c in a['cs']: src['B站楼中楼' if '楼中楼' in c['src'] else 'B站评论'] += 1
    for c in a['st']: src['Steam评测'] += 1
    for c in a['mq']: src[{'xhs': '小红书', 'x': 'X 回复/提及', 'steam': 'Steam评测(档案摘录)', 'other': '其他来源'}[c['kind']]] += 1
    ndm = len(a['dm_all'])
    sc = collections.Counter(c['s'] for c in allc)
    tc = collections.Counter(t for c in allc for t in c['t'])
    L = []
    # ---- summary
    tops = [t for t, _ in tc.most_common(4)]
    pp, ng = pct(sc['pos'], n), pct(sc['neg'], n)
    tone = '整体偏正面' if pp >= ng * 1.8 and pp >= 20 else '整体偏负面' if ng > pp else '褒贬并存、以中性讨论为主'
    used = set()
    toplike = pick(allc, 1, used)
    negq = pick([c for c in allc if c['s'] == 'neg'], 1, used, 8)
    posq = pick([c for c in allc if c['s'] == 'pos'], 1, used, 8)
    S = []
    S.append(f"共分析 {n} 条文字反馈" + (f"和 {ndm} 条弹幕" if ndm else '') + f"，好评 {pp}%、差评 {ng}%，{tone}。")
    if tops: S.append(f"讨论最集中的是{'、'.join(tops[:3])}" + (f"；点赞最高的一条说「{clean(toplike[0]['text'], 60)}」（{toplike[0]['like']} 赞）" if toplike and toplike[0]['like'] else '') + '。')
    if posq: S.append(f"喜欢的点主要是：「{clean(posq[0]['text'], 50)}」。")
    if negq: S.append(f"不满集中在{'、'.join([t for t, _ in collections.Counter(t for c in allc if c['s']=='neg' for t in c['t']).most_common(2)]) or '零散问题'}，例如「{clean(negq[0]['text'], 50)}」。")
    aud = [AUD[t] for t in tops[:2] if t in AUD]
    if aud: S.append(f"从讨论内容看，受众主要是{'和'.join(aud)}。")
    fdk = [t for t in tops if t in FD][:1]
    if fdk: S.append(f"对《***》的启示：{FD[fdk[0]]}。")
    if n < 30: S.append(f"样本只有 {n} 条，以上判断仅供参考。")
    L.append('#### 总结\n\n' + ''.join(S[:6]) + '\n')
    # ---- samples
    L.append('#### 统计分布\n')
    L.append('**样本量（全部已采集数据）**\n\n| 来源 | 条数 |\n|---|---:|')
    for k, v in src.most_common(): L.append(f'| {k} | {v} |')
    if ndm: L.append(f'| B站弹幕 | {ndm} |')
    if a['bvs']: L.append(f"\n涉及 B站视频 {len(a['bvs'])} 个：" + '、'.join(a['bvs'][:12]) + ('…' if len(a['bvs']) > 12 else ''))
    L.append('\n**情感分布（文字反馈，规则词典分类；Steam 按推荐/不推荐）**\n\n| 倾向 | 条数 | 占比 | |\n|---|---:|---:|---|')
    for k in ('pos', 'neu', 'neg'): L.append(f"| {SENT_ZH[k]} | {sc[k]} | {pct(sc[k], n)}% | `{bar(pct(sc[k], n))}` |")
    if ndm:
        d = a['dm_s']; L.append(f"\n弹幕情感：好评 {pct(d['pos'], ndm)}% · 中性 {pct(d['neu'], ndm)}% · 差评 {pct(d['neg'], ndm)}%")
    # likes weighted
    W = collections.Counter(); 
    for c in allc: W[c['s']] += c['like'] + 1
    wt = sum(W.values())
    L.append(f"\n**按点赞加权**（每条权重 = 赞数+1）：好评 {pct(W['pos'], wt)}% · 中性 {pct(W['neu'], wt)}% · 差评 {pct(W['neg'], wt)}%")
    L.append('\n**话题分布**（一条可属多个话题；未命中任何话题的 ' + str(sum(1 for c in allc if not c['t'])) + ' 条不计）\n\n| 话题 | 条数 | 占比 | | 其中差评 |\n|---|---:|---:|---|---:|')
    for t, v in tc.most_common():
        negv = sum(1 for c in allc if t in c['t'] and c['s'] == 'neg')
        L.append(f"| {t} | {v} | {pct(v, n)}% | `{bar(pct(v, n))}` | {pct(negv, v)}% |")
    kw = keywords([c['text'] for c in allc])
    if kw: L.append('\n**评论高频词**：' + ' · '.join(f'{w}({c})' for w, c in kw))
    dkw = collections.Counter(t.strip() for t in a['dm_all'] if 2 <= len(t.strip()) <= 20).most_common(12)
    if dkw: L.append('\n**弹幕高频句**：' + ' · '.join(f'「{clean(w, 20)}」×{c}' for w, c in dkw))
    # danmaku peaks
    pk = []
    for b, d in sorted(a['dms'].items(), key=lambda kv: -len(kv[1]))[:3]:
        if len(d) < 30: continue
        bins = collections.defaultdict(list)
        for s, t in d: bins[int(s // 10)].append(t)
        avg = len(d) / max(1, len(bins))
        for k, ts in sorted(bins.items(), key=lambda kv: -len(kv[1]))[:3]:
            sm = '」「'.join(clean(x, 18) for x, _ in collections.Counter(x.strip() for x in ts).most_common(3))
            title = clean((a['views'].get(b) or {}).get('title', ''), 26)
            pk.append(f"| {b} {title} | {mmss(k*10)}–{mmss(k*10+10)} | {len(ts)}（均值 {avg:.1f}） | 「{sm}」 |")
    if pk: L.append('\n**弹幕密度峰值**（10 秒分桶，弹幕最多的 3 个视频各取前 3 峰）\n\n| 视频 | 时间段 | 弹幕数 | 当时在说 |\n|---|---|---:|---|\n' + '\n'.join(pk))
    tl = sorted(allc, key=lambda c: -c['like'])[:5]
    if tl and tl[0]['like']:
        L.append('\n**最高赞反馈说了什么**\n\n| 赞 | 倾向 | 话题 | 内容 | 来源 |\n|---:|---|---|---|---|')
        for c in tl:
            if not c['like']: break
            L.append(f"| {c['like']} | {SENT_ZH[c['s']]} | {'/'.join(c['t'][:2]) or '—'} | {clean(c['text'], 70)} | {c['src']} |")
    # ---- representative quotes
    L.append('\n#### 代表性评论\n')
    used = set()
    groups = [('好评', [c for c in allc if c['s'] == 'pos']), ('差评 / 反对意见', [c for c in allc if c['s'] == 'neg'])]
    for t, _ in tc.most_common(4): groups.append((f'话题：{t}', [c for c in allc if t in c['t']]))
    nonbili = [c for c in allc if c['kind'] != 'bili']
    if nonbili: groups.append(('B站以外（X / 小红书 / Steam）', nonbili))
    for g, cands in groups:
        q = pick(cands, 3, used)
        if not q: continue
        L.append(f'**{g}**\n'); L += [qfmt(c) for c in q]; L.append('')
    L.append(f"> 分类方法：情感与话题为规则词典自动分类（`scripts/feedback_analysis.py`），反讽、梗和外文可能误判，比例看趋势即可。数据截至 {date}。")
    return '\n'.join(L)

REV_H = re.compile(r'^## (?!综合)[^\n]*(实际评价|玩家评价|评价原话|评论原话|玩家口碑)[^\n]*$', re.M)
MK = re.compile(r'<!--\s*added:(\d{4}-\d{2}-\d{2}|meta)\s*-->', re.I)

def last_marker(s):
    m = MK.findall(s); return m[-1] if m else 'meta'

def apply(path, a, date, dry=False):
    md = open(path, encoding='utf-8').read()
    md = re.sub(r'\n?<!-- feedback:start -->.*?<!-- feedback:end -->\n?', '\n', md, flags=re.S)
    block = render(a, date)
    m = REV_H.search(md)
    if m:
        ins = m.end(); head = ''
    else:
        m2 = re.search(r'^## (团队|综合评价)', md, re.M)
        ins = m2.start() if m2 else len(md); head = '## 玩家反馈\n'
    prev = last_marker(md[:ins])
    sec = (f"\n<!-- feedback:start -->\n{head}<!-- added:{date} -->\n\n### 玩家反馈分析\n\n{block}\n\n<!-- added:{prev} -->\n<!-- feedback:end -->\n")
    new = md[:ins] + sec + md[ins:]
    # collapse raw quotes (once)
    if m and '<details><summary>全部原文' not in new:
        s0 = new.index('<!-- feedback:end -->') + len('<!-- feedback:end -->')
        nx = re.search(r'^## ', new[s0:], re.M); s1 = s0 + nx.start() if nx else len(new)
        raw = new[s0:s1]
        nq = len(re.findall(r'^\s*[-*] ', raw, re.M))
        if nq >= 3:
            last = last_marker(new[:s1])
            wrapped = (f"\n<!-- added:meta -->\n<details><summary>全部原文（{nq} 条）</summary>\n\n<!-- added:{prev} -->\n{raw.strip()}\n\n<!-- added:meta -->\n</details>\n\n<!-- added:{last} -->\n\n")
            new = new[:s0] + wrapped + new[s1:]
    if not dry: open(path, 'w', encoding='utf-8').write(new)
    return new

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--only', default='all'); ap.add_argument('--ids', default='')
    ap.add_argument('--date', default=__import__('datetime').date.today().isoformat()); ap.add_argument('--dry', action='store_true')
    ap.add_argument('--stats', default='tmp/feedback_stats.json')
    o = ap.parse_args()
    files = sorted(f for f in glob.glob('state/*.md') if '***' not in f)
    global OWN_BV; OWN_BV = {os.path.basename(f)[:-3] for f in files if os.path.basename(f).startswith('BV')}
    ids = set(filter(None, o.ids.split(',')))
    stats = jl(o.stats) or {}
    for f in files:
        pid = os.path.basename(f)[:-3]
        md = open(f, encoding='utf-8').read()
        comp = bool(re.search(r'^competitor:\s*true', md, re.M))
        if ids and pid not in ids: continue
        if o.only == 'competitors' and not comp: continue
        if o.only == 'others' and comp: continue
        a = analyze(pid, md)
        if not a:
            stats[pid] = dict(comp=comp, n=0, dm=0, note='无任何玩家反馈数据'); print(pid, 'NO DATA'); continue
        apply(f, a, o.date, o.dry)
        sc = collections.Counter(c['s'] for c in a['allc'])
        stats[pid] = dict(comp=comp, n=len(a['allc']), bili=len(a['cs']), steam=len(a['st']), md=len(a['mq']),
                          dm=len(a['dm_all']), bvs=len(a['bvs']), pos=sc['pos'], neu=sc['neu'], neg=sc['neg'])
        print(pid, stats[pid], flush=True)
    json.dump(stats, open(o.stats, 'w'), ensure_ascii=False, indent=1)

if __name__ == '__main__':
    main()
