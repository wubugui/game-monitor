# usage: python3 enrich.py projects.json  -> fills raw/view/<bvid>.json, covers, frames for competitors
import json,subprocess,time,os,sys
from PIL import Image
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36"
os.makedirs("raw/view",exist_ok=True)
def cj(u):
  for t in range(3):
    o=subprocess.run(["curl","-s","--compressed","-b","/tmp/bili.ck","-A",UA,"-e","https://www.bilibili.com/",u],capture_output=True,text=True).stdout
    try:
      d=json.loads(o)
      if d.get("code")==0: return d["data"]
      print("code",d.get("code"),u,flush=True); 
      if d.get("code") in (-404,62002,62004): return None
    except Exception: print("nonjson",u,flush=True)
    time.sleep(8*(t+1))
def dl(url,path):
  if url.startswith("//"): url="https:"+url
  url=url.replace("http://","https://")
  subprocess.run(["curl","-s","-A",UA,"-e","https://www.bilibili.com/","-o",path,url])
P=json.load(open(sys.argv[1]))
for p in P:
  b=p["bvid"]; vf=f"raw/view/{b}.json"
  if not os.path.exists(vf):
    v=cj(f"https://api.bilibili.com/x/web-interface/wbi/view?bvid={b}"); time.sleep(1)
    tg=cj(f"https://api.bilibili.com/x/tag/archive/tags?bvid={b}") or []; time.sleep(1)
    if v: json.dump({"view":v,"tags":[t.get("tag_name") for t in tg]},open(vf,"w"),ensure_ascii=False)
  if not os.path.exists(vf): continue
  v=json.load(open(vf))["view"]
  cp=f"covers/{b}.jpg"
  if not os.path.exists(cp) or os.path.getsize(cp)<1000:
    dl(v["pic"]+"@640w_360h_1c.jpg",cp); time.sleep(0.5)
  if p.get("comp"):
    if not os.path.exists(f"frames/{b}_1.jpg"):
      s=cj(f"https://api.bilibili.com/x/player/videoshot?bvid={b}&index=1"); time.sleep(1)
      if s and s.get("image"):
        n=s["img_x_len"]*s["img_y_len"]; W,H=s["img_x_size"],s["img_y_size"]
        dl(s["image"][0],"/tmp/sprite.jpg")
        try:
          im=Image.open("/tmp/sprite.jpg"); cols=im.width//W; rows=im.height//H; tot=min(n,cols*rows)
          # frames actually used: count from index length
          used=min(tot,max(1,len(s.get("index",[]))-1)) if s.get("index") else tot
          for k,fi in enumerate([int(used*0.25),int(used*0.5),int(used*0.8)],1):
            x=(fi%cols)*W; y=(fi//cols)*H
            im.crop((x,y,x+W,y+H)).save(f"frames/{b}_{k}.jpg",quality=90)
        except Exception as e: print("sprite err",b,e)
print("enrich done")
