import re,glob,os,pickle,sys
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)),'..')); WRITE='--write' in sys.argv

def parse_notes(path='tmp/xhs_sweep_2026-10-10.md'):
  notes=[];sec='';cur=None
  for ln in open(path).read().split('\n'):
    if ln.startswith('## '): sec=ln[3:].strip(); cur=None; continue
    if ln.startswith('### '):
      t=ln[4:].strip()
      if t.startswith('其他') or ('未进详情' in t and '《' not in t) or t.startswith('民俗恐怖里') or t.startswith('中式恐怖（') or t in ('民国恐怖','国产独立里和民俗恐游直接相关') or t.startswith('独立游戏泛词'): cur=None; continue
      cur=dict(sec=sec,title=t,author='',date='',stats='',body=''); notes.append(cur); continue
    if ln.startswith('|') and not re.match(r'\|\s*(标题|笔记)\s*\||\|\s*-{3}',ln):
      c=[x.strip() for x in ln.strip('|').split('|')]
      if len(c)>=4: notes.append(dict(sec=sec,title=c[0],author=c[1],date=c[2],stats=(c[3]+' 赞' if '/' not in c[3] else c[3]+'（赞/藏/评）'),body=' '.join(c[4:]),card=True))
      continue
    if cur is not None:
      m=re.match(r'^- (?:作者[:：]\s*)?([^·\n]{1,30}?) · (.+)$',ln)
      if m and not cur['author'] and not ln.startswith('- 赞') and not ln.startswith('- 摘要') and not ln.startswith('- 封面'):
        cur['author']=m.group(1).strip()
        p=[x.strip() for x in m.group(2).split('·')]
        cur['date']=re.sub(r'^编辑于\s*','',p[0])
        for x in p[1:]:
          if '赞' in x and not cur['stats']: cur['stats']=x
      m=re.match(r'^- 赞\s*(.+)',ln)
      if m and not cur['stats']: cur['stats']='赞 '+m.group(1)
      cur['body']+=ln+'\n'
  for n in notes: n['stats']=n['stats'].replace('**','')
  return notes

notes=parse_notes()
norm=lambda s: re.sub(r'[\W_]+','',s or '').lower()
XPOSTS={'Duola Mage':[('@未知（X 中文圈公开检索，账号未记录）','2026-10-10 前后','开发者自述：无站外宣发，Steam 发售约 10 天，自称好评率 98%')]}
tot=0
for path in sorted(glob.glob('state/*.md')):
  t=open(path).read()
  name=(re.search(r'^name:\s*"?([^"\n]+)',t,re.M) or [0,''])[1].strip()
  m=re.search(r'^## 小红书.*?(?=^## |\Z)',t,re.S|re.M)
  xs=m.group(0) if m else ''
  body=t.split('## 来源（发现与资料）')[0]
  nb=norm(body); nx=norm(xs)
  key=norm(name.split('：')[0].split('（')[0])[:4]
  used=[]
  if '小红书' in body:
    for n in notes:
      nt=norm(n['title'])
      rel=key and (key in norm(n['sec']) or key in nt)
      hit=(len(nt)>=6 and nt[:10] in nb) or (xs and rel and n['author'] and norm(n['author']) in nx and len(norm(n['author']))>=2)
      if hit and (n['title'],n['author']) not in [(u['title'],u['author']) for u in used]: used.append(n)
  lines=t.split('\n'); out=[]
  for ln in lines:
    if ln.startswith('- X：帖子（正文中引用）'): continue
    if ln.startswith('- 小红书') or ln.startswith('- X 帖子') or ln.startswith('  - 〔小红书〕') or ln.startswith('  - 〔X〕'): continue
    out.append(ln)
    if ln.startswith('**资料来源**'):
      if used:
        out.append(f'- 小红书笔记（采用 {len(used)} 条，登录态只读，采集 2026-10-10；互动为 赞/藏/评，「卡」=仅搜索卡）： <!-- added:meta -->')
        for n in used:
          out.append(f"  - 〔小红书〕{n['title']} · {n['author'] or '作者未记录'} · {n['date'] or '日期未记录'} · {n['stats'] or '互动未记录'}")
      elif xs:
        out.append('- 小红书：正文提及，但未采用具体笔记（仅检索结论） <!-- added:meta -->')
      for k,v in XPOSTS.items():
        if name.startswith(k):
          out.append(f'- X 帖子（采用 {len(v)} 条）： <!-- added:meta -->')
          for a,d,s in v: out.append(f'  - 〔X〕{a} · {d} · {s}')
  new='\n'.join(out)
  if used: tot+=1; print(os.path.basename(path),name,len(used),[n['title'][:12] for n in used][:8])
  if WRITE and new!=t: open(path,'w').write(new)
print('files with xhs list',tot)
