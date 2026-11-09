#!/usr/bin/env python3
"""R7.0: 61 new image-only decode checks, no duplicate 3 prior R6.9A probes.

Reads the existing R6.5 immutable 64-photo inventory artifact; does NOT
contact RSS/article pages, query Supabase, save photo bytes, or publish media.
Uses single 390x844 Chromium browser, direct requests to previously discovered
publisher thumbnail URL only, one at a time with rate limit and no retries.
Outputs *only* URL/status/natural image dimensions/error report (rights pending).
"""
from pathlib import Path
from collections import Counter
from playwright.sync_api import sync_playwright
import json, html, re, time, sys, shutil, os, urllib.parse

IN=Path(os.environ.get("PHOTO_INVENTORY_PATH","r65-metadata/r65-inventory-64.json"))
OUT=Path(os.environ.get("REPORT_PATH","r70-photo-browser-verification.json"))
KNOWN_DONE={"18675","18674","18673"}
DATA=json.loads(IN.read_text("utf-8"))["data"]
assert len(DATA)==64 and len({r["article_no"] for r in DATA})==64, "R6.5 inventory unexpectedly changed"
targets=[r for r in DATA if r["article_no"] not in KNOWN_DONE]
assert len(targets)==61, "Unexpected new target count"
urls=set()
for r in targets:
    u=urllib.parse.urlparse(r["photo_url"])
    assert r["source_id"]=="FEED_DAILYGAEWON"
    assert r["result"]=="PHOTO_URL_EXTRACTED"
    assert r["photo_file_downloaded"] is False
    assert r["rights"]=="RIGHTS_NOT_VERIFIED"
    assert u.scheme=="https" and u.hostname=="www.dailygaewon.com"
    assert re.fullmatch(r"/news/thumbnail/\d{6}/"+re.escape(r["article_no"])+r"_.*\.(jpg|jpeg|png|webp)",u.path,re.I)
    assert not u.query and not u.fragment and not u.username
    assert r["photo_url"] not in urls
    urls.add(r["photo_url"])

results=[]
unexpected=[]
actual_requests=[]
with sync_playwright() as pw:
    executable=shutil.which("google-chrome") or shutil.which("chromium") or shutil.which("chromium-browser")
    launch={"headless":True,"args":["--no-sandbox","--disable-dev-shm-usage"],"timeout":30000}
    if executable:launch["executable_path"]=executable
    browser=pw.chromium.launch(**launch)
    context=browser.new_context(viewport={"width":390,"height":844},locale="ko-KR",service_workers="block")
    page=context.new_page()
    responses={}
    def route_handler(route):
        request=route.request
        if request.url in urls and request.method=="GET" and request.resource_type=="image":
            actual_requests.append(request.url)
            return route.continue_()
        unexpected.append({"url":request.url,"method":request.method,"type":request.resource_type})
        return route.abort()
    def on_response(res):
        if res.url in urls:
            responses[res.url]={"status":res.status,"mime":res.headers.get("content-type","")}
    page.route("**/*",route_handler)
    page.on("response",on_response)
    for index,row in enumerate(targets,1):
        photo=row["photo_url"]
        article=row["article_no"]
        safe=html.escape(photo,quote=True)
        doc=(
          "<!doctype html><html><head><meta charset='utf-8'>"
          "<meta http-equiv='Content-Security-Policy' content=\"default-src 'none'; "
          "img-src https://www.dailygaewon.com; base-uri 'none'\">"
          "</head><body><img id='one' loading='eager' decoding='async' "
          "referrerpolicy='no-referrer' src='"+safe+"' width='250' height='180'></body></html>"
        )
        tic=time.monotonic()
        reason=None
        try:
            page.set_content(doc,wait_until="domcontentloaded",timeout=13000)
            try:page.locator("#one").evaluate("(img)=>img.decode()",timeout=13000)
            except Exception as error:reason=type(error).__name__
            state=page.locator("#one").evaluate("(i)=>({complete:i.complete,width:i.naturalWidth,height:i.naturalHeight})",timeout=5000)
        except Exception as error:
            reason=reason or type(error).__name__
            state={"complete":False,"width":0,"height":0}
        meta=responses.get(photo,{})
        ok=(meta.get("status")==200 and meta.get("mime","").lower().startswith("image/") and
            state["complete"] and state["width"]>0 and state["height"]>0)
        result={
          "article_no":article,"image_url":photo,
          "http":meta.get("status"),"mime":meta.get("mime"),
          "naturalWidth":state["width"],"naturalHeight":state["height"],
          "result":"DECODE_OK" if ok else "DECODE_FAILED",
          "error_type":reason,"elapsed_ms":int((time.monotonic()-tic)*1000),
          "rights":"RIGHTS_NOT_VERIFIED","image_bytes_saved":0
        }
        results.append(result)
        print("R70_NEW",index,"/",len(targets),article,result["result"],"HTTP",result["http"],"natural",result["naturalWidth"],result["naturalHeight"],flush=True)
        if index<len(targets):time.sleep(1.05)
    context.close()
    browser.close()
assert len(actual_requests)==61 and len(set(actual_requests))==61, "Image-only request count unexpected"
assert not unexpected,"Requests other than known 61 image URLs occurred: "+str(unexpected[:4])
counts=dict(Counter(x["result"] for x in results))
report={
    "report":"DOCTORPET_R70_61_NEW_IMAGE_ONLY_BROWSER_DECODE",
    "preexisting_R69A_verified":sorted(KNOWN_DONE),
    "view":"Chromium 390x844 browser viewport emulation (not physical handset)",
    "source":"FEED_DAILYGAEWON",
    "tested_new_articles":61,
    "new_unique_requests":len(actual_requests),
    "unexpected_requests":unexpected,
    "result_counts":counts,
    "no_article_request":True,
    "no_media_file_download":True,
    "photo_publisher_permission_confirmed":False,
    "records":results
}
OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
print("R70_SUMMARY",json.dumps(counts,ensure_ascii=False),flush=True)
if counts.get("DECODE_FAILED",0):
    print("R70_PARTIAL",sum(x["result"]=="DECODE_OK" for x in results),"/61",flush=True)
else:
    print("PASS R70 incremental Chromium decode 61/61, plus prior R6.9A 3/3; 64 total distinct. Image bytes saved 0; no publishing.",flush=True)
