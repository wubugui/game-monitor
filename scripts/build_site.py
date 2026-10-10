#!/usr/bin/env python3
"""Build the static data files for the game-monitor GitHub Pages site.

Run from anywhere:  python3 scripts/build_site.py
Pure standard library. Reads tracked_projects.md, state/*.md, reports/*.md and
writes data/*.json (fully regenerated each run, safe to run repeatedly).
See README.md "数据格式约定" for the input format contract.
"""
import json, os, re, sys, glob, shutil, hashlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
OUT = "data"
IMG_DIRS = ["covers", "frames", "sheets", "x", "images"]
DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")
ADDED_RE = re.compile(r"<!--\s*added:(\d{4}-\d{2}-\d{2})\s*-->", re.I)
WARN = []


def warn(msg):
    WARN.append(msg)


def read(p):
    with open(p, encoding="utf-8") as f:
        return f.read().replace("\r\n", "\n")


# ---------------------------------------------------------------- helpers
def parse_front_matter(text):
    """Very small YAML subset: `key: value`, `key: [a, b]`, and `key:` + `- item` lists."""
    meta = {}
    if not text.startswith("---\n"):
        return meta, text
    end = text.find("\n---", 4)
    if end < 0:
        return meta, text
    block = text[4:end]
    body = text[end + 4:].lstrip("\n")
    cur = None
    for line in block.split("\n"):
        if not line.strip() or line.strip().startswith("#"):
            continue
        m = re.match(r"^\s*-\s+(.*)$", line)
        if m and cur:
            if not isinstance(meta.get(cur), list):
                meta[cur] = []
            meta[cur].append(unquote(m.group(1)))
            continue
        m = re.match(r"^([A-Za-z_][\w-]*)\s*:\s*(.*)$", line)
        if not m:
            continue
        k, v = m.group(1).strip(), m.group(2).strip()
        cur = k
        if v.startswith("[") and v.endswith("]"):
            meta[k] = [unquote(x) for x in split_list(v[1:-1])]
        elif v == "":
            meta[k] = []
        else:
            meta[k] = unquote(v)
    return meta, body


def split_list(s):
    return [x.strip() for x in re.split(r"[,，]", s) if x.strip()]


def unquote(v):
    v = v.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "'\"":
        v = v[1:-1]
    return v


def truthy(v):
    return str(v).strip().lower() in ("true", "yes", "1", "y", "是", "⚠️", "⚠")


def norm_path(p):
    """Make a repo-relative asset path usable from the site root."""
    p = p.strip()
    if re.match(r"^(https?:)?//|^data:", p):
        return ("https:" + p) if p.startswith("//") else p
    p = re.sub(r"^(\.\./|\./)+", "", p)
    p = re.sub(r"^/?game-monitor/", "", p)
    return p.lstrip("/")


def fix_md_paths(md):
    md = re.sub(r"(!\[[^\]]*\]\()\s*([^)\s]+)", lambda m: m.group(1) + norm_path(m.group(2)), md)
    md = re.sub(r'(<img[^>]*?\ssrc=["\'])([^"\']+)', lambda m: m.group(1) + norm_path(m.group(2)), md)
    return md


def images_in(md):
    out = re.findall(r"!\[[^\]]*\]\(\s*([^)\s]+)", md)
    out += re.findall(r'<img[^>]*?\ssrc=["\']([^"\']+)', md)
    return out


def check_images(md, where):
    for p in images_in(md):
        if not re.match(r"^(https?:)?//|^data:", p) and not os.path.exists(p):
            warn(f"missing image {p} (in {where})")


def strip_md(s):
    s = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", s)
    s = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", s)
    s = re.sub(r"<[^>]+>", "", s)
    s = re.sub(r"[*_`>#]+", "", s)
    return re.sub(r"\s+", " ", s).strip()



def collect_added_dates(md):
    return set(ADDED_RE.findall(md or ""))


def change_notes_for_date(md, date, limit=3):
    """One-line notes from blocks marked <!-- added:date --> (prefer headings)."""
    if not md or not date:
        return []
    parts = ADDED_RE.split(md)
    notes = []
    for i in range(1, len(parts), 2):
        if parts[i] != date:
            continue
        chunk = parts[i + 1] if i + 1 < len(parts) else ""
        hm = re.search(r"^#{2,4}\s+(.+)$", chunk, re.M)
        if hm:
            t = strip_md(hm.group(1))
            # skip generic section labels
            if t and t not in notes and t not in ("档案", "画面", "实机截图", "更新时间线"):
                notes.append(t[:100])
        else:
            for para in re.split(r"\n\s*\n", chunk):
                t = strip_md(para)
                if len(t) >= 8 and t not in notes:
                    notes.append(t[:100])
                    break
        if len(notes) >= limit:
            break
    return notes

def clean_name(n):
    return re.sub(r"^\s*(⚠️|⚠)\s*", "", n).strip()


def core_name(n):
    """Name without bracketed notes, used to find mentions in reports."""
    n = clean_name(n)
    n = re.sub(r"[（(][^）)]*[）)]", "", n).strip()
    return n


def slug(s):
    s2 = re.sub(r"[^A-Za-z0-9_-]+", "-", s).strip("-")
    if len(s2) >= 3 and s2 == s:
        return s2
    return "p-" + hashlib.md5(s.encode()).hexdigest()[:10]


def bvid_of(s):
    m = re.search(r"(BV[0-9A-Za-z]{10})", s or "")
    return m.group(1) if m else None


def first_url(s):
    m = re.search(r"https?://[^\s)|>\]]+", s or "")
    return m.group(0) if m else ""


# ---------------------------------------------------------------- buckets
GENRE_TAGS = [
    ("恐怖", r"恐怖|惊悚|诡|鬼"),
    ("民俗/国风", r"民俗|国风|志怪|中式|修仙|武侠|东方|北宋|古风"),
    ("叙事/剧情", r"叙事|剧情|视觉小说|galgame|文字|恋爱|国 ?G|AVG"),
    ("悬疑/解谜", r"悬疑|解谜|推理|探案|谜"),
    ("互动影游", r"影游"),
    ("肉鸽/构筑", r"肉鸽|roguelike|rogue|构筑|卡牌"),
    ("动作", r"动作|ARPG|类魂|格斗|射击|FPS|平台跳跃|银河城"),
    ("RPG", r"RPG"),
    ("模拟经营", r"模拟|经营|城建|建造|种田|增量|生活"),
    ("策略", r"策略|SLG|塔防|自走棋"),
    ("多人/合作", r"合作|多人|联机"),
    ("AI 驱动", r"\bAI\b|AIGC|大模型|Agent"),
    ("工具/行业", r"工具|行业参考"),
]


def genre_tags(text):
    tags = [t for t, rx in GENRE_TAGS if re.search(rx, text or "", re.I)]
    return tags or ["其他"]


DEV_TYPES = ["个人", "小团队", "中型厂商", "大厂", "未知"]


def dev_bucket(s):
    s = (s or "").strip()
    if s.startswith("未知"):
        return "未知"
    for k, rx in [("个人", r"^个人|独立开发者|一个人"), ("小团队", r"^小团队|工作室"),
                  ("中型厂商", r"^中型|中厂"), ("大厂", r"^大厂|大型")]:
        if re.search(rx, s):
            return k
    return "未知"


STATUS_RULES = [
    ("抢先体验", r"抢先体验|EA\b"),
    ("即将发售", r"\d{1,2}-\d{1,2} ?发售|定档|即将上线|即将发售"),
    ("已发售", r"已发售|正式发售"),
    ("Demo", r"demo|试玩"),
    ("众筹中", r"众筹"),
    ("首曝", r"首曝|首支|先导"),
]


def infer_status(text):
    for k, rx in STATUS_RULES:
        if re.search(rx, text or "", re.I):
            return k
    return "开发中"


# ---------------------------------------------------------------- tracked table
def parse_tables(md):
    rows = []
    lines = md.split("\n")
    i = 0
    while i < len(lines):
        l = lines[i].strip()
        if l.startswith("|") and i + 1 < len(lines) and re.match(r"^\|?\s*:?-{2,}", lines[i + 1].strip()):
            header = [c.strip() for c in l.strip("|").split("|")]
            i += 2
            while i < len(lines) and lines[i].strip().startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                rows.append(dict(zip(header, cells)))
                i += 1
            continue
        i += 1
    return rows


def col(row, *names):
    for n in names:
        for k, v in row.items():
            if k == n or (n in k):
                if v:
                    return v
    return ""


def load_tracked():
    projects = {}
    if not os.path.exists("tracked_projects.md"):
        return projects
    for row in parse_tables(read("tracked_projects.md")):
        name = col(row, "名称", "游戏", "name")
        if not name:
            continue
        link = col(row, "链接", "B站", "url", "link")
        url = first_url(link) or link
        bv = bvid_of(link) or bvid_of(col(row, "ID", "id"))
        pid = col(row, "ID", "id") or bv or slug(clean_name(name))
        projects[pid] = dict(
            id=pid, name=clean_name(name),
            competitor=("⚠" in name) or truthy(col(row, "收藏", "\u7ade\u54c1")),
            genre=col(row, "类型", "genre"), developer=col(row, "开发者类型", "开发者", "developer"),
            found=(DATE_RE.search(col(row, "发现日期", "发现", "found")) or [None, ""])[1] if DATE_RE.search(col(row, "发现日期", "发现", "found")) else "",
            updated=(DATE_RE.search(col(row, "最后更新", "更新")).group(1) if DATE_RE.search(col(row, "最后更新", "更新")) else ""),
            status=col(row, "状态", "status"), link=url, bvid=bv,
            source=col(row, "来源", "source") or ("B站" if bv or "bilibili" in url else ("X" if "x.com" in url or "twitter" in url else "")),
            note=col(row, "备注", "note"), summary="", cover="", images=[], tags=[], intro="", entries=[])
    return projects


# ---------------------------------------------------------------- state files
def load_state(projects):
    for path in sorted(glob.glob("state/*.md")):
        meta, body = parse_front_matter(read(path))
        stem = os.path.splitext(os.path.basename(path))[0]
        pid = meta.get("id") or bvid_of(meta.get("link", "")) or stem
        name = clean_name(meta.get("name", "")) if meta.get("name") else ""
        p = projects.get(pid)
        if p is None and name:  # match by name
            for q in projects.values():
                if q["name"] == name:
                    p = q
                    break
        if p is None:
            p = dict(id=pid, name=name or stem, competitor=False, genre="", developer="", found="", updated="",
                     status="", link="", bvid=bvid_of(pid), source="", note="", summary="", cover="", images=[],
                     tags=[], intro="", entries=[])
            projects[pid] = p
        for k_src, k_dst in [("genre", "genre"), ("类型", "genre"), ("developer", "developer"), ("dev_type", "developer"),
                             ("开发者", "developer"), ("status", "status"), ("状态", "status"), ("link", "link"),
                             ("found", "found"), ("updated", "updated"), ("summary", "summary"), ("source", "source"),
                             ("cover", "cover"), ("note", "note"), ("studio", "studio"), ("platform", "platform"),
                             ("release", "release"), ("discovery_platform", "disc_platform"), ("discovery", "discovery"),
                             ("discovery_date", "discovery_date")]:
            if meta.get(k_src):
                p[k_dst] = meta[k_src] if not isinstance(meta[k_src], list) else ", ".join(meta[k_src])
        if name:
            p["name"] = name
        if "competitor" in meta or "收藏" in meta or "\u7ade\u54c1" in meta:
            p["competitor"] = truthy(meta.get("competitor", meta.get("收藏", meta.get("\u7ade\u54c1"))))
        if meta.get("tags"):
            p["tags"] = meta["tags"] if isinstance(meta["tags"], list) else split_list(meta["tags"])
        if meta.get("images"):
            imgs = meta["images"] if isinstance(meta["images"], list) else split_list(meta["images"])
            p["images"] = [norm_path(x) for x in imgs]
        if meta.get("aliases"):
            p["aliases"] = meta["aliases"] if isinstance(meta["aliases"], list) else split_list(meta["aliases"])
        if meta.get("baseline"):
            p["baseline"] = meta["baseline"] if not isinstance(meta["baseline"], list) else meta["baseline"][0]
        if meta.get("self_project") is not None:
            p["self_project"] = truthy(meta.get("self_project"))
        p["state_file"] = path
        # body: intro, then "## YYYY-MM-DD ..." history sections
        body = fix_md_paths(body)
        check_images(body, path)
        parts = re.split(r"^##\s+(.*)$", body, flags=re.M)
        intro = parts[0].strip()
        entries = []
        for h, txt in zip(parts[1::2], parts[2::2]):
            m = DATE_RE.search(h)
            if m:
                title = h.replace(m.group(1), "").strip(" -—:：|")
                entries.append(dict(date=m.group(1), title=title, md=txt.strip(), kind="state"))
            else:
                intro += "\n\n## " + h + "\n" + txt
        p["intro"] = intro.strip()
        p["entries"] = entries
        full_md = body  # already path-fixed; includes intro + ## history headings text
        p["added_dates"] = sorted(collect_added_dates(full_md))
        _fb = re.search(r"共分析 (\d+) 条文字反馈(?:和 (\d+) 条弹幕)?，好评 ([\d.]+)%、差评 ([\d.]+)%", full_md)
        if _fb:  # 玩家反馈分析（scripts/feedback_analysis.py）摘要，供列表/卡片使用
            p["feedback"] = {"n": int(_fb.group(1)), "dm": int(_fb.group(2) or 0), "pos": float(_fb.group(3)), "neg": float(_fb.group(4))}
        p["_raw_body"] = full_md  # for today_updates notes; stripped before dump


# ---------------------------------------------------------------- reports
def load_reports():
    reports = []
    for path in sorted(glob.glob("reports/*.md")):
        base = os.path.basename(path)
        m = DATE_RE.search(base)
        if not m:
            continue
        meta, body = parse_front_matter(read(path))
        body = fix_md_paths(body)
        check_images(body, path)
        rid = os.path.splitext(base)[0]
        title = meta.get("title") or ""
        if not title:
            h = re.search(r"^#\s+(.+)$", body, re.M)
            title = h.group(1).strip() if h else f"{m.group(1)} 日报"
        summary = meta.get("summary") or ""
        if not summary:
            for para in re.split(r"\n\s*\n", re.sub(r"^#.*$", "", body, flags=re.M)):
                t = strip_md(para)
                if len(t) > 15 and not para.lstrip().startswith(("|", "!")):
                    summary = t
                    break
        imgs = [norm_path(x) for x in images_in(body)]
        imgs = [x for x in imgs if re.match(r"^https?:", x) or os.path.exists(x)]
        sections = [strip_md(h) for h in re.findall(r"^##\s+(.+)$", body, re.M)]
        reports.append(dict(id=rid, date=m.group(1), title=title, summary=summary[:280],
                            images=imgs[:8], image_count=len(imgs), sections=sections,
                            new=meta.get("new", ""), updated=meta.get("updated", ""),
                            baseline=truthy(meta.get("baseline", False)) or ("初始" in title), md=body))
    reports.sort(key=lambda r: (r["date"], r["id"]), reverse=True)
    return reports


def blocks_mentioning(md, name):
    """Return markdown snippet(s) of a report that talk about `name`."""
    lines = md.split("\n")
    # 1) a heading containing the name -> whole section
    for i, l in enumerate(lines):
        hm = re.match(r"^(#{2,6})\s+(.*)$", l)
        if hm and name in hm.group(2):
            lvl = len(hm.group(1))
            j = i + 1
            while j < len(lines):
                h2 = re.match(r"^(#{1,6})\s", lines[j])
                if h2 and len(h2.group(1)) <= lvl:
                    break
                j += 1
            return "\n".join(lines[i:j]).strip()
    # 2) list items / paragraphs containing the name (with continuation lines)
    out, i = [], 0
    while i < len(lines):
        if name in lines[i] and not lines[i].lstrip().startswith("|"):
            j = i
            if not re.match(r"^\s*([-*+]|\d+\.)\s", lines[i]):  # paragraph: expand to blank lines
                while j > 0 and lines[j - 1].strip() and not lines[j - 1].startswith("#"):
                    j -= 1
            k = i + 1
            while k < len(lines) and lines[k].strip() and not re.match(r"^\s*([-*+]|\d+\.)\s|^#", lines[k]):
                k += 1
            # include images that directly follow (common: item then image line)
            while k < len(lines) and (lines[k].strip() == "" or lines[k].lstrip().startswith("![")) and k < i + 8:
                if lines[k].lstrip().startswith("!["):
                    k += 1
                    continue
                if k + 1 < len(lines) and lines[k + 1].lstrip().startswith("!["):
                    k += 1
                    continue
                break
            out.append("\n".join(lines[j:k]).strip())
            i = k
        else:
            i += 1
    return "\n\n".join(dict.fromkeys(out)).strip()



# ---------------------------------------------------------------- today updates (homepage)
def build_today_updates(plist, latest_report, latest, baseline_report, baseline_only):
    """Games NEW or UPDATED on latest_report_date for the homepage 「今日更新」.

    Sources: state `<!-- added:YYYY-MM-DD -->` markers, found date, and dated history
    entries. Competitors first. One-line change notes. Avoids flooding the home on
    the baseline day (everything is "new").
    """
    if not latest:
        return [], "还没有日报。"
    if baseline_only:
        return [], f"今日为初始基线（{latest}），全部项目见项目库；明日起首页只列当天新增/更新。"

    # names mentioned in the latest report (for same-day revision narrowing)
    mentioned = set()
    if latest_report:
        for p in latest_report.get("projects") or []:
            mentioned.add(p["id"])
        md = latest_report.get("md") or ""
        for p in plist:
            names = [p["name"], core_name(p["name"])] + p.get("aliases", [])
            if any(n and len(n) >= 2 and n in md for n in names):
                mentioned.add(p["id"])

    items = []
    for p in plist:
        found = p.get("found") or ""
        is_new = found == latest
        # state-dated history only (ignore "found" markers and baseline report mentions,
        # which would otherwise mark every project as "updated" on day one)
        hist_today = [e for e in p.get("history", []) if e.get("date") == latest and e.get("kind") == "state"]
        added_dates = set(p.get("added_dates") or [])
        added_today = latest in added_dates
        incremental = added_today and found and found < latest
        self_proj = False

        # Normal day (after baseline calendar date): new / incremental added / dated history
        if latest > baseline_report:
            if not (is_new or incremental or hist_today):
                continue
        else:
            # Same calendar day as baseline (e.g. a revision report): never dump all 100+
            # dossiers. Prefer latest-report mentions, state hist, self project; if the
            # latest report is a competitor revision, include all competitors too.
            rev_txt = ""
            if latest_report:
                rev_txt = (latest_report.get("title") or "") + " " + (latest_report.get("summary") or "")
            rev_competitors = bool(re.search("收藏|\u7ade\u54c1", rev_txt))
            # Do not use hist_today here: the revision pass stamped ## DATE 修订 on
            # nearly every dossier, which would flood the homepage again.
            keep = (
                p["id"] in mentioned
                or self_proj
                or (rev_competitors and p.get("competitor") and added_today)
            )
            if not keep:
                continue

        if latest <= baseline_report and (self_proj or p.get("competitor")):
            kind = "updated"  # same-day revision of baseline dossiers
        elif is_new:
            kind = "new"
        else:
            kind = "updated"
        notes = change_notes_for_date(p.get("_raw_body") or p.get("intro") or "", latest)
        # prefer history titles / first bullet from today
        for e in hist_today:
            t = strip_md(e.get("title") or "")
            if t and t not in notes and t not in ("修订",):
                notes.insert(0, t[:100])
            for line in (e.get("md") or "").split("\n"):
                ls = line.strip()
                if ls.startswith(("-", "*")) or ls.startswith("1."):
                    bt = strip_md(ls.lstrip("-*0123456789. "))
                    if len(bt) >= 8 and bt not in notes:
                        notes.insert(0, bt[:100])
                        break
        prefer = ("综合评价", "实际评价", "团队与靠谱", "相关视频正文", "修订")
        ranked = sorted(notes, key=lambda n: (0 if any(k in n for k in prefer) else 1, notes.index(n) if n in notes else 99))
        notes = ranked or notes
        if not notes:
            if self_proj:
                notes = ["档案有更新"]
            elif p.get("competitor") and latest <= baseline_report:
                notes = ["收藏档案修订（正文化 + 评价）"]
            elif is_new:
                notes = ["新建档"]
            elif hist_today:
                notes = [strip_md(hist_today[0].get("title") or "") or "档案有更新"]
            else:
                notes = ["档案有更新"]
        skip_labels = {"档案", "实机截图", "画面", "更新时间线", "一句话", "修订",
                       "设定/玩法/美术（据视频与商店页归纳）", "官方/代表视频简介（原文摘录）",
                       "相关视频正文摘要（正文化，免点链接）", "相关视频正文摘要", "资料来源"}
        note = next((n for n in notes if n and n not in skip_labels), None)
        # Prefer concrete evaluation headings when present
        for pref in ("综合评价", "实际评价", "团队与靠谱程度"):
            hit = next((n for n in notes if pref in n), None)
            if hit:
                note = hit
                break
        if not note or note in skip_labels:
            if self_proj:
                note = "档案有更新"
            elif p.get("competitor") and latest <= baseline_report:
                note = "收藏档案修订（正文化 + 评价）"
            elif is_new:
                note = "新建档"
            else:
                note = "档案有更新"
        items.append(dict(
            id=p["id"], name=p["name"], competitor=bool(p.get("competitor")),
            cover=p.get("cover") or "", kind=kind, note=note,
            status=p.get("status") or "", genre=p.get("genre") or "",
        ))

    banner = ""
    if latest <= baseline_report and items:
        banner = f"{latest} 与基线同日，首页只列最新日报涉及/收藏修订共 {len(items)} 项；其余见项目库。"

    items.sort(key=lambda x: (not x["competitor"], 0 if x["kind"] == "new" else 1, x["name"]))
    return items, banner


# ---------------------------------------------------------------- main
def main():
    projects = load_tracked()
    load_state(projects)
    reports = load_reports()

    for p in projects.values():
        # cover / gallery
        if p.get("cover"):
            p["cover"] = norm_path(p["cover"])
        if not p.get("cover"):
            for d in IMG_DIRS:
                for ext in ("jpg", "jpeg", "png", "webp"):
                    c = f"{d}/{p['id']}.{ext}"
                    if os.path.exists(c):
                        p["cover"] = c
                        break
                if p.get("cover"):
                    break
        if p.get("cover") and not re.match(r"^https?:", p["cover"]) and not os.path.exists(p["cover"]):
            warn(f"missing cover {p['cover']} ({p['name']})")
            p["cover"] = ""
        frames = sorted(glob.glob(f"frames/{p['id']}_*.*"))
        p["images"] = list(dict.fromkeys([x for x in p.get("images", []) if x] + frames))
        real_cover = bool(p.get("cover")) and (re.match(r"^https?:", p["cover"]) or (os.path.exists(p["cover"]) and os.path.getsize(p["cover"]) > 2000))
        real_imgs = [x for x in p["images"] if re.match(r"^https?:", x) or (os.path.exists(x) and os.path.getsize(x) > 2000)]
        if not p.get("cover") and p["images"]:
            p["cover"] = p["images"][0]
        if (not real_cover or len(real_imgs) < 4):
            p["missing_images"] = True
            warn(f"缺图: {p['id']} {p['name']} cover={'ok' if real_cover else 'NONE'} images={len(real_imgs)}")
            if not str(p["name"]).startswith("⚠️缺图"):
                p["name"] = "⚠️缺图 " + str(p["name"])
            p["note"] = "【缺图】封面或实机图不足（需≥4张），待补。" + (p.get("note") or "")
        if p.get("link") == "" and p.get("bvid"):
            p["link"] = f"https://www.bilibili.com/video/{p['bvid']}"

        # history: state entries + report mentions + first-found marker
        hist = {(e["date"], "state"): e for e in p.get("entries", [])}
        names = [p["name"], core_name(p["name"])] + p.get("aliases", [])
        names = [n for n in dict.fromkeys(names) if n and len(n) >= 2]
        for r in reports:
            snip = ""
            for n in names:
                snip = blocks_mentioning(r["md"], n)
                if snip:
                    break
            if not snip and p.get("bvid") and p["bvid"] in r["md"]:
                snip = blocks_mentioning(r["md"], p["bvid"])
            if snip and (r["date"], "state") in hist:
                hist[(r["date"], "state")].setdefault("report", r["id"])
            elif snip:
                hist[(r["date"], "report:" + r["id"])] = dict(date=r["date"], title=r["title"], md=snip,
                                                              kind="report", report=r["id"])
        if p.get("found") and not any(d == p["found"] for d, _ in hist):
            hist[(p["found"], "found")] = dict(date=p["found"], title="首次发现", md=p.get("note", ""), kind="found")
        p["history"] = sorted(hist.values(), key=lambda e: (e["date"], e["kind"] == "state"), reverse=True)
        p.pop("entries", None)
        dates = [e["date"] for e in p["history"]] + [d for d in (p.get("updated"), p.get("found")) if d]
        p["updated"] = max(dates) if dates else ""
        p["genre_tags"] = list(dict.fromkeys((p.get("tags") or []) + genre_tags(p.get("genre", "") + " " + p["name"])))
        p["dev_type"] = dev_bucket(p.get("developer", ""))
        if not p.get("status"):
            p["status"] = infer_status(" ".join([p.get("note", ""), p.get("intro", "")] +
                                                [e["md"] for e in p["history"][:2]]))
            p["status_inferred"] = True
        if not p.get("summary"):
            p["summary"] = strip_md(p.get("intro", ""))[:160] or p.get("note", "")
        p["update_count"] = len([e for e in p["history"] if e["kind"] != "found"])

    plist = sorted(projects.values(), key=lambda p: (p["updated"], p["found"], p["name"]), reverse=True)
    plist = [p for p in plist if not p.get("self_project")]

    # write output (regenerate data/ from scratch => idempotent)
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    os.makedirs(f"{OUT}/project")
    os.makedirs(f"{OUT}/report")

    def dump(path, obj):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=1, sort_keys=True)

    card_keys = ["id", "feedback", "name", "competitor", "genre", "genre_tags", "developer", "dev_type", "status",
                 "status_inferred", "found", "updated", "cover", "link", "source", "summary", "note", "update_count", "missing_images", "disc_platform", "discovery"]
    dump(f"{OUT}/projects.json", [{k: p.get(k) for k in card_keys} for p in plist])
    for p in plist:
        slim = {k: v for k, v in p.items() if not k.startswith("_")}
        dump(f"{OUT}/project/{p['id']}.json", slim)
    dump(f"{OUT}/reports.json", [{k: v for k, v in r.items() if k != "md"} for r in reports])
    for r in reports:
        mentions = [dict(id=p["id"], name=p["name"], competitor=p["competitor"], cover=p.get("cover", ""))
                    for p in plist if any(e.get("report") == r["id"] for e in p["history"])]
        dump(f"{OUT}/report/{r['id']}.json", {**r, "projects": mentions})
    baseline_report = reports[-1]["date"] if reports else ""
    latest_report_date = reports[0]["date"] if reports else ""
    baseline_only = (len(reports) <= 1) or bool(reports and reports[0].get("baseline"))
    today_updates, today_banner = build_today_updates(
        plist, reports[0] if reports else None, latest_report_date, baseline_report, baseline_only)
    _pm = {p["id"]: p for p in plist}
    for u in today_updates:
        q = _pm.get(u.get("id"), {})
        u["disc_platform"] = q.get("disc_platform", ""); u["discovery"] = q.get("discovery", "")
    meta = dict(disc_platforms=sorted({p.get("disc_platform") for p in plist if p.get("disc_platform")}),
                project_count=len(plist), competitor_count=sum(1 for p in plist if p["competitor"]),
                report_count=len(reports), latest_report=reports[0]["id"] if reports else None,
                latest_report_date=latest_report_date, baseline_report=baseline_report,
                baseline_only=baseline_only,
                today_updates=today_updates, today_banner=today_banner,
                today_new=sum(1 for x in today_updates if x["kind"] == "new"),
                today_updated=sum(1 for x in today_updates if x["kind"] == "updated"),
                data_date=max([p["updated"] for p in plist if p["updated"]] + [r["date"] for r in reports] or [""]),
                genres=sorted({g for p in plist for g in p["genre_tags"]}),
                dev_types=[d for d in DEV_TYPES if any(p["dev_type"] == d for p in plist)],
                statuses=sorted({p["status"] for p in plist}))
    dump(f"{OUT}/meta.json", meta)
    _pf = os.path.expanduser("~/private/publish_terms.re")
    if os.path.exists(_pf):
        _rx = re.compile(open(_pf, encoding="utf-8").read().strip())
        _bad = [fp for fp in glob.glob(f"{OUT}/**/*.json", recursive=True) if _rx.search(open(fp, encoding="utf-8").read())]
        if _bad:
            sys.exit("build aborted: restricted terms in " + ", ".join(_bad[:10]))
    # drop private fields from per-project dumps (already written above — scrub before was wrong order)
    if not os.path.exists(".nojekyll"):
        open(".nojekyll", "w").close()
    print(f"built: {len(plist)} projects, {len(reports)} reports -> {OUT}/")
    for w in WARN:
        print("WARN", w, file=sys.stderr)


if __name__ == "__main__":
    main()
