#!/usr/bin/env bash
# Rebuild site data and push. Usage: bash scripts/publish.sh "2026-10-10：新增 5 个，更新 3 个"
set -e
cd "$(dirname "$0")/.."
git pull --rebase --autostash
python3 scripts/build_site.py
paths=()
for p in tracked_projects.md state reports covers frames sheets x xhs images data .nojekyll README.md index.html assets scripts; do [ -e "$p" ] && paths+=("$p"); done
git add -A -- "${paths[@]}"
if git diff --cached --quiet; then echo "nothing to commit"; exit 0; fi
git commit -m "${1:-$(date +%F) 日报数据更新}"
git pull --rebase --autostash
git push
