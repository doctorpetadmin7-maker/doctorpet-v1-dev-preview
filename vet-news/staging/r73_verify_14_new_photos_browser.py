#!/usr/bin/env python3
"""R7.3 fourteen NEW DailyGaewon image URLs only: browser GET/decode, no copy/upload."""
import json,re,os,shutil,time
from pathlib import Path
from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright
p=Path("r73-metadata/r73-new14-photos.json")
source=json.loads(p.read_text(encoding="utf-8"))
rows=source["data"]
assert len(rows)==14 and all(x["result"]=="PHOTO_URL_EXTRACTED" for x in rows)
urls=set()
for r in rows:
    u=urlsplit(r["photo_url"])
    assert int(r["article_no"]) in range(18677,18691)
    assert u.scheme=="https" and u.hostname=="www.dailygaewon.com"
    assert re.search(r"\.(jpg|jpeg|png|webp)$",u.path,re.I)
    urls.add(r["photo_url"])
assert len(urls)==14
results=[];requests=[];unexpected=[];responses={};errors=[]
with sync_playwright() as pw:
    binary=shutil.which("google-chrome") or shutil.which("chromium")
    options={"headless":True,"args":["--no-sandbox","--disable-dev-shm-usage"]}
    if binary:options["executable_path"]=binary
    browser=pw.chromium.launch(**options)
    context=browser.new_context(viewport={"width":390,"height":844},service_workers="block")
    page=context.new_page()
    def route(r):
        req=r.request
        if req.url in urls and req.method=="GET" and req.resource_type=="image":
            requests.append(req.url)
            return r.continue_()
        unexpected.append(req.url)
        return r.abort()
    page.route("**/*",route)
    page.on("response",lambda r:responses.update({r.url:(r.status,r.headers.get("content-type",""))}) if r.url in urls else None)
    page.on("requestfailed",lambda r:errors.append({"url":r.url,"reason":r.failure}) if r.url in urls else None)
    for i,r in enumerate(rows,1):
        url=r["photo_url"];no=r["article_no"];err=None
        document=("<!doctype html><meta charset='utf-8'><meta http-equiv='Content-Security-Policy' "
                  "content=\"default-src 'none'; img-src https://www.dailygaewon.com\">"
                  "<img id='photo' decoding='async' referrerpolicy='no-referrer' "
                  "loading='eager' src='"+url+"'>")
        page.set_content(document,wait_until="domcontentloaded",timeout=13000)
        try:
            page.locator("#photo").evaluate("(im)=>im.decode()",timeout=18000)
        except Exception as e:err=type(e).__name__
        st=page.locator("#photo").evaluate("(im)=>({complete:im.complete,width:im.naturalWidth,height:im.naturalHeight})")
        status,content_type=responses.get(url,(None,""))
        valid=status==200 and content_type.startswith("image/") and st["width"]>0 and st["height"]>0
        rec={"article_no":no,"image_url":url,"http":status,"mime":content_type,
             "width":st["width"],"height":st["height"],"result":"DECODE_OK" if valid else "DECODE_FAILED",
             "error":err,"publisher_permission_confirmed":False,"saved_image_bytes":0}
        results.append(rec)
        print("R73_BROWSER",i,"/14",no,rec["result"],status,st["width"],st["height"],flush=True)
        if i<len(rows):time.sleep(1.1)
    context.close();browser.close()
assert len(requests)==14 and len(set(requests))==14 and not unexpected,(len(requests),unexpected[:2])
report={"checked":len(results),"success":sum(x["result"]=="DECODE_OK" for x in results),
        "failure":sum(x["result"]=="DECODE_FAILED" for x in results),
        "results":results,"errors":errors,"unexpectedRequests":unexpected,
        "not_physical_phone":True,"publisher_permission_confirmed":False,
        "media_downloaded_for_storage":0,"public_publishing":False}
Path("r73-dailygaewon-14-image-decoding.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
print("R73_BROWSER_SUMMARY",json.dumps({"success":report["success"],"failed":report["failure"],"network":errors},ensure_ascii=False),flush=True)
if report["failure"]==0:print("PASS R73 DailyGaewon 14/14 browser decoding, no article refetch or file persistence",flush=True)
else:print("R73_BROWSER_PARTIAL",report["success"],"/14",flush=True)
