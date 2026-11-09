#!/usr/bin/env python3
"""R7.4: only previously stored 13 DailyVet + 2 HappyPet thumbnail URLs.
No article requests, source collector claims, image file storage, or public write.
"""
import json,time,shutil
from pathlib import Path
from playwright.sync_api import sync_playwright
ROWS=json.loads("[{\"source\":\"V\",\"article_no\":\"303041\",\"photo_url\":\"https://cdn.dailyvet.co.kr/wp-content/uploads/2026/11/04235548/20261104icada_pjo0.jpg\"},{\"source\":\"V\",\"article_no\":\"303084\",\"photo_url\":\"https://cdn.dailyvet.co.kr/wp-content/uploads/2026/11/05014304/261104wild.jpeg\"},{\"source\":\"V\",\"article_no\":\"303208\",\"photo_url\":\"https://cdn.dailyvet.co.kr/wp-content/uploads/2026/11/06003803/261105vetstem_now1.jpg\"},{\"source\":\"V\",\"article_no\":\"303214\",\"photo_url\":\"https://cdn.dailyvet.co.kr/wp-content/uploads/2025/05/07215535/250507pkp_pgp_profile3.jpg\"},{\"source\":\"V\",\"article_no\":\"303219\",\"photo_url\":\"https://cdn.dailyvet.co.kr/wp-content/uploads/2026/11/06011322/261105bvd_boeh_bovela.jpg\"},{\"source\":\"V\",\"article_no\":\"303263\",\"photo_url\":\"https://cdn.dailyvet.co.kr/wp-content/uploads/2026/11/06045614/20261101fasava2.jpg\"},{\"source\":\"V\",\"article_no\":\"303321\",\"photo_url\":\"https://cdn.dailyvet.co.kr/wp-content/uploads/2026/11/06190802/261106invets.png\"},{\"source\":\"V\",\"article_no\":\"303324\",\"photo_url\":\"https://cdn.dailyvet.co.kr/wp-content/uploads/2026/11/06204047/261106jbnu_scholarship1.jpeg\"},{\"source\":\"V\",\"article_no\":\"303335\",\"photo_url\":\"https://cdn.dailyvet.co.kr/wp-content/uploads/2026/11/06224211/20261031fasava_jerzy_gawor1.jpg\"},{\"source\":\"V\",\"article_no\":\"303349\",\"photo_url\":\"https://cdn.dailyvet.co.kr/wp-content/uploads/2026/11/06230704/261106welfare_forum3.jpg\"},{\"source\":\"V\",\"article_no\":\"303359\",\"photo_url\":\"https://cdn.dailyvet.co.kr/wp-content/uploads/2026/11/06232814/20261101fasava_jmb1.jpg\"},{\"source\":\"V\",\"article_no\":\"303370\",\"photo_url\":\"https://cdn.dailyvet.co.kr/wp-content/uploads/2026/11/07001435/20261101fasava_royalcanin4_David-Cai.jpg\"},{\"source\":\"V\",\"article_no\":\"303402\",\"photo_url\":\"https://cdn.dailyvet.co.kr/wp-content/uploads/2026/11/07003517/20261104plusvet_vetching_snu.jpg\"},{\"source\":\"H\",\"article_no\":\"6344154\",\"photo_url\":\"https://i3n.news1.kr/system/photos/2026/11/5/8198868/high.jpg\"},{\"source\":\"H\",\"article_no\":\"6344921\",\"photo_url\":\"https://i3n.news1.kr/system/photos/2026/11/6/8199776/high.jpg\"}]")
assert len(ROWS)==15 and len({r["photo_url"] for r in ROWS})==15
URLS={x["photo_url"] for x in ROWS}
unexpected=[];requested=[];responses={};request_failures=[];records=[]
with sync_playwright() as pw:
    executable=shutil.which("google-chrome") or shutil.which("chromium")
    opts={"headless":True,"args":["--no-sandbox","--disable-dev-shm-usage"]}
    if executable:opts["executable_path"]=executable
    browser=pw.chromium.launch(**opts)
    context=browser.new_context(viewport={"width":390,"height":844},service_workers="block")
    page=context.new_page()
    def route(route):
        request=route.request
        if request.method=="GET" and request.url in URLS and request.resource_type=="image":
            requested.append(request.url);route.continue_()
        else:
            unexpected.append(request.url);route.abort()
    page.route("**/*",route)
    page.on("response",lambda r:responses.update({r.url:{"http":r.status,"type":r.headers.get("content-type","")}}) if r.url in URLS else None)
    page.on("requestfailed",lambda r:request_failures.append({"url":r.url,"reason":r.failure}) if r.url in URLS else None)
    for n,rec in enumerate(ROWS,1):
        url=rec["photo_url"]
        doc=("<!doctype html><meta charset='utf-8'><meta http-equiv='Content-Security-Policy' "
             "content=\"default-src 'none'; img-src https://cdn.dailyvet.co.kr https://i3n.news1.kr\">"
             "<img id='photo' decoding='async' referrerpolicy='no-referrer' loading='eager' src='"+url+"'>")
        page.set_content(doc,wait_until="domcontentloaded",timeout=13000)
        issue=None
        try:page.locator("#photo").evaluate("(img)=>img.decode()",timeout=14000)
        except Exception as ex:issue=type(ex).__name__
        d=page.locator("#photo").evaluate("(i)=>({width:i.naturalWidth,height:i.naturalHeight,complete:i.complete})")
        meta=responses.get(url,{})
        ok=meta.get("http")==200 and meta.get("type","").startswith("image/") and d["width"]>0 and d["height"]>0
        records.append({"source":rec["source"],"article_no":rec["article_no"],"photo_url":url,"http":meta.get("http"),"mime":meta.get("type"),"width":d["width"],"height":d["height"],"result":"DECODE_OK" if ok else "DECODE_FAILED","error":issue})
        print("R74_ONLY_NEW_VERIFICATION",n,"/15",rec["source"],rec["article_no"],records[-1]["result"],flush=True)
        if n<len(ROWS):time.sleep(1.2)
    context.close();browser.close()
assert len(requested)==15 and len(set(requested))==15 and not unexpected,(len(requested),unexpected[:2])
report={"checked":15,"passed":sum(x["result"]=="DECODE_OK" for x in records),"failed":sum(x["result"]=="DECODE_FAILED" for x in records),"records":records,"image_only_requests":15,"unexpected_requests":unexpected,"request_failures":request_failures,"publisher_permission_confirmed":False,"public_publishing":False,"media_files_persisted":0}
Path("r74-existing15-browser-verification.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
print("R74_SUMMARY",json.dumps({"passed":report["passed"],"failed":report["failed"],"failures":request_failures},ensure_ascii=False),flush=True)
if report["failed"]==0:print("PASS R74 existing 15/15 previously untested photo URLs in Chromium; no publisher article requests",flush=True)
else:print("R74_PARTIAL",report["passed"],"/15",flush=True)
