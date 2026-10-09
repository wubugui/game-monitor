import json,subprocess,urllib.parse,time,re,datetime,os,sys
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36"
base=["独立游戏","国产独立游戏","国产单机","独立开发者","个人开发 游戏","一个人做游戏","游戏开发日志","devlog 游戏","首曝PV 游戏","实机PV","实机演示 独立游戏","demo 试玩 游戏","试玩版 国产","Steam新品节","愿望单 游戏","摩点众筹 游戏","抢先体验 国产","定档 独立游戏","发售 独立游戏","上线 steam 国产"]
genres=["肉鸽","塔防","自走棋","搜打撤","卡牌构筑","模拟经营","种田","城建","动作游戏","类魂","动作冒险","平台跳跃","银河城","解谜游戏","叙事游戏","视觉小说","galgame","文字冒险","互动影游","恐怖游戏","中式恐怖","民俗恐怖","志怪","修仙游戏","武侠游戏","国风游戏","家庭 游戏 叙事","生存游戏","合作游戏","多人联机 独立","沙盒游戏","策略游戏","SLG 独立","射击游戏 独立","FPS 独立","赛车游戏 独立","音游 独立","像素游戏","AI游戏","AIGC 游戏","大模型NPC","AI NPC"]
kws=base[:]
for g in genres:
  kws.append(g+" 独立游戏"); 
for g in ["肉鸽","模拟经营","动作","解谜","恐怖","修仙","国风","像素","卡牌","策略","生存","视觉小说","互动影游","AI"]:
  kws.append(g+" 首曝"); kws.append(g+" demo")
kws+=["手机游戏 新游","手游 首曝","手游 PV","二次元 新游","二次元手游 首曝","二次元 测试","大厂 新游","网易 新游","腾讯 新游","米哈游 新游","鹰角 新游","叠纸 新游","库洛 新游","莉莉丝 新游","3A 国产","国产3A 实机","新游 定档","新游 公测","新游 预约","主机游戏 新作","PV首曝 新游","游戏 先导PV","TGS 2026 国产","东京电玩展 国产","开放世界 新游","MMO 新游","中式悬疑 游戏","悬疑解谜 新游","互动影游 新作","恐怖游戏 新作"]
kws=list(dict.fromkeys(kws))
print(len(kws),flush=True)
now=int(time.time()); b30=now-30*86400; b60=now-60*86400
out=open("raw/search.jsonl","a")
done=set()
if os.path.exists("raw/done.txt"): done=set(open("raw/done.txt").read().split("\n"))
dn=open("raw/done.txt","a")
def get(u):
  for t in range(3):
    o=subprocess.run(["curl","-s","--compressed","-b","/tmp/bili.ck","-A",UA,"-e","https://search.bilibili.com/",u],capture_output=True,text=True).stdout
    try:
      d=json.loads(o)
      if d.get("code")==0: return d
      print("code",d.get("code"),flush=True)
    except Exception: print("nonjson",o[:60].replace("\n"," "),flush=True)
    time.sleep(10*(t+1))
  return None
for kw in kws:
  for order,pages,flt in [("pubdate",4,""),("click",2,"&pubtime_begin_s=%d&pubtime_end_s=%d"%(b30,now))]:
    for p in range(1,pages+1):
      key=f"{kw}|{order}|{p}"
      if key in done: continue
      u=f"https://api.bilibili.com/x/web-interface/search/type?search_type=video&keyword={urllib.parse.quote(kw)}&order={order}&page={p}{flt}"
      d=get(u); time.sleep(1.1)
      if not d: continue
      res=d["data"].get("result") or []
      stop=False
      for v in res:
        if v["pubdate"]<b60: stop=True; continue
        v["_kw"]=kw; out.write(json.dumps(v,ensure_ascii=False)+"\n")
      out.flush(); dn.write(key+"\n"); dn.flush()
      if order=="pubdate" and (stop and all(v["pubdate"]<b60 for v in res[-5:])): break
      if len(res)<20: break
print("DONE",flush=True)
