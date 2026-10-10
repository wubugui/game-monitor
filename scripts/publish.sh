#!/usr/bin/env bash
# Rebuild site data and push. Usage: bash scripts/publish.sh "2026-10-10：新增 5 个，更新 3 个"
set -e
cd "$(dirname "$0")/.."
git pull --rebase --autostash
python3 scripts/build_site.py
missing=$(python3 - <<'PY'
import re,glob,os
for f in sorted(glob.glob('state/*.md')):
  if '***' in f: continue
  h=open(f,encoding='utf-8').read().split('\n---',1)[0]
  c=(re.search(r'^cover:[ \t]*(\S*)',h,re.M) or [None,''])[1]
  seg=h.split('images:',1)[1] if 'images:' in h else ''
  im=[i for i in re.findall(r'(\S+\.(?:jpg|jpeg|png|webp))',seg) if os.path.exists(i) and os.path.getsize(i)>2000]
  ok=bool(c) and os.path.exists(c) and os.path.getsize(c)>2000
  if not ok or len(im)<4: print(f"  {os.path.basename(f)[:-3]}  cover={'ok' if ok else 'NONE'}  images={len(im)}")
PY
)
if [ -n "$missing" ]; then
  echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!" >&2
  echo "!!! 缺图警告：以下条目没有封面或实机图不足 4 张 !!!" >&2
  echo "$missing" >&2
  echo "!!! 规则：每个条目必须有图，请补齐后再发布 !!!" >&2
  echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!" >&2
fi
paths=()
for p in tracked_projects.md state reports covers frames sheets x xhs images data .nojekyll README.md index.html assets scripts; do [ -e "$p" ] && paths+=("$p"); done
git add -A -- "${paths[@]}"
if git diff --cached --quiet; then echo "nothing to commit"; exit 0; fi
git commit -m "${1:-$(date +%F) 日报数据更新}"
git pull --rebase --autostash
git push
