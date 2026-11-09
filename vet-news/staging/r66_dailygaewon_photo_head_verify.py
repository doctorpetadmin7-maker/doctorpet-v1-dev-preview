#!/usr/bin/env python3
"""R6.6: 64 known DailyGaewon og:image URLs, HEAD status only.

This is a private review inventory of metadata, NOT photo download, publication
or publisher license grant. No DB, no cron, no claim, no production mutations.
"""
import csv,json,pathlib,urllib.request,urllib.error,urllib.parse,urllib.robotparser,time,collections
from datetime import datetime,timezone

UA="DoctorPet-private-photo-HEAD-audit/1.0 (+permission pending)"
HOST="www.dailygaewon.com"
inp=pathlib.Path("r65-inventory-64.json")
assert inp.exists(),"R65 source metadata artifact missing; no article requests allowed"
src=json.loads(inp.read_text(encoding="utf-8"))
rows=src["data"]
assert src["requested"]==64 and len(rows)==64,"not the R65 64-article inventory"
assert len({r["article_no"] for r in rows})==64
assert len({r["photo_url"] for r in rows})==64
for r in rows:
    url=r["photo_url"]
    pu=urllib.parse.urlsplit(url)
    assert r["source_id"]=="FEED_DAILYGAEWON"
    assert r["result"]=="PHOTO_URL_EXTRACTED"
    assert pu.scheme=="https" and pu.hostname==HOST
    assert pu.path.startswith("/news/thumbnail/") and pu.path.endswith(".jpg")
    assert "/"+r["article_no"]+"_" in pu.path
class OnlySameSite(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        u=urllib.parse.urlsplit(newurl)
        if u.scheme!="https" or u.hostname!=HOST:raise ValueError("REDIRECT_OFFSITE")
        return super().redirect_request(req,fp,code,msg,headers,newurl)
opener=urllib.request.build_opener(OnlySameSite)
req=urllib.request.Request(f"https://{HOST}/robots.txt",headers={"User-Agent":UA},method="GET")
try:
    with opener.open(req,timeout=14) as r:
        assert r.status==200 and "text" in r.headers.get("Content-Type","text/plain")
        robots=r.read(262145)
    assert len(robots)<=262144
    rp=urllib.robotparser.RobotFileParser();rp.parse(robots.decode("utf-8","replace").splitlines())
    assert all(rp.can_fetch(UA,r["photo_url"]) for r in rows),"Robots disallows image HEAD; abort"
except urllib.error.HTTPError as e:
    if e.code!=404:raise SystemExit("ROBOTS_CHECK_NOT_ALLOWED_"+str(e.code))
except Exception as e:raise SystemExit("ROBOTS_CHECK_FAILED_"+type(e).__name__)
out=[]
for i,r in enumerate(rows,1):
    p={"article_no":r["article_no"],"article_url":r["article_url"],
       "photo_url":r["photo_url"],"http_status":None,"content_type":"",
       "content_length":"","result":"UNKNOWN","rights":"NOT_VERIFIED","image_bytes_downloaded":0}
    try:
        q=urllib.request.Request(r["photo_url"],headers={"User-Agent":UA},method="HEAD")
        with opener.open(q,timeout=15) as f:
            p["http_status"]=f.status
            p["content_type"]=f.headers.get("Content-Type","")
            p["content_length"]=f.headers.get("Content-Length","")
            p["result"]="IMAGE_JPEG_HEAD_OK" if f.status==200 and "image/jpeg" in p["content_type"].lower() else "HEAD_NON_JPEG"
    except urllib.error.HTTPError as e:
        p["http_status"]=e.code;p["result"]="HEAD_HTTP_"+str(e.code)
    except Exception as e:p["result"]="HEAD_ERROR_"+type(e).__name__
    out.append(p)
    if i%8==0:print("R66_PROGRESS",i,"/",len(rows),flush=True)
    if i<len(rows):time.sleep(1.3)
root=pathlib.Path("r66-head64")
with root.with_suffix(".json").open("w",encoding="utf-8") as f:
    json.dump({"collected_at_utc":datetime.now(timezone.utc).isoformat(),"count":len(out),
        "summary":dict(collections.Counter(r["result"] for r in out)),"data":out},f,ensure_ascii=False,indent=2)
with root.with_suffix(".csv").open("w",encoding="utf-8-sig",newline="") as f:
    writer=csv.DictWriter(f,fieldnames=list(out[0]));writer.writeheader();writer.writerows(out)
print("R66_SUMMARY",json.dumps(dict(collections.Counter(r["result"] for r in out)),sort_keys=True),flush=True)
