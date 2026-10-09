import json,re,collections,datetime,html
rows={}
for l in open("raw/search.jsonl"):
  v=json.loads(l); b=v["bvid"]
  if b in rows: rows[b]["kw"].add(v["_kw"]); continue
  t=html.unescape(re.sub("<[^>]+>","",v["title"])); d=html.unescape(v.get("description",""))
  rows[b]=dict(bvid=b,title=t,desc=d,tag=v.get("tag",""),type=v.get("typename",""),play=v.get("play",0),author=v["author"],mid=v["mid"],date=datetime.datetime.fromtimestamp(v["pubdate"]).strftime("%Y-%m-%d"),pic=v.get("pic",""),dur=v.get("duration",""),kw={v["_kw"]})
GAMEP={"单机游戏","手机游戏","网络游戏","游戏","音游","桌游棋牌","电子竞技","GMV","Mugen","游戏赛事","游戏综合","游戏资讯"}
def names(r):
  s=r["title"]+" "+r["desc"]
  out=[]
  for m in re.finditer(r"(?:游戏名(?:称)?|相关游戏|游戏)[：:]\s*[《【]?([^\s《》【】,，。|/、！!（(]{2,20})",s): out.append(m.group(1))
  out+=re.findall(r"《([^》]{2,25})》",s)
  return [re.sub(r"\s+","",n) for n in out]
g=collections.defaultdict(list)
types=collections.Counter()
for r in rows.values():
  types[r["type"]]+=1
  ns=names(r)
  r["names"]=ns
  if ns: g[ns[0]].append(r)
json.dump({b:{**r,"kw":list(r["kw"])} for b,r in rows.items()},open("raw/rows.json","w"),ensure_ascii=False)
print(len(rows),types.most_common(15))
L=sorted(g.items(),key=lambda kv:-sum(x["play"] for x in kv[1]))
with open("raw/groups.txt","w") as f:
  for n,xs in L:
    xs.sort(key=lambda x:-x["play"])
    f.write(f"{n}\t{len(xs)}\t{sum(x['play'] for x in xs)}\t{xs[0]['type']}\t{xs[0]['bvid']}\t{xs[0]['date']}\t{xs[0]['author']}\t{xs[0]['title'][:50]}\n")
print(len(L))
