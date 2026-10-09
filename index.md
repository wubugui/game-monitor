---
title: 游戏项目监控日报
---

# 游戏项目监控日报

每天整理 B 站和 X 上的游戏项目：竞品专区、B 站全部游戏、AI 新玩法、海外动态。只报告新项目和有更新的项目。

## 日报

{% assign reports = site.pages | where_exp: "p", "p.path contains 'reports/'" | sort: "path" | reverse %}
{% for r in reports %}- [{{ r.title | default: r.path }}]({{ r.url | relative_url }})
{% endfor %}

## 项目数据库

- [全部跟踪项目](tracked_projects.html)
