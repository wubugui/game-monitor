import json,subprocess,time,sys
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36"
bvs=sys.argv[1:]
out=open("raw/related.jsonl","a")
for b in bvs:
  o=subprocess.run(["curl","-s","--compressed","-b","/tmp/bili.ck","-A",UA,"-e","https://www.bilibili.com/",f"https://api.bilibili.com/x/web-interface/archive/related?bvid={b}"],capture_output=True,text=True).stdout
  try:
    d=json.loads(o)
    for v in d.get("data") or []: v["_src"]=b; out.write(json.dumps(v,ensure_ascii=False)+"\n")
    print(b,len(d.get("data") or []),flush=True)
  except Exception: print("err",b,flush=True)
  time.sleep(2.5)
