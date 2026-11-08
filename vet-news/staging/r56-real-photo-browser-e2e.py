#!/usr/bin/env python3
"""R5.6 photo visibility regression: actual DEV metadata, one SYNTHETIC local PNG.
The R5.5 HTML is never deployed. Only a browser document and image are
intercepted as test fixtures; the browser requests the actual DEV API.
"""
import json, pathlib, struct, urllib.request, zlib
from playwright.sync_api import sync_playwright

ORIGIN="https://doctorpetadmin7-maker.github.io"
SITE=ORIGIN+"/doctorpet-v1-dev-preview/vet-news/"
API="https://mabvxdcpmfdzrqlgkxqn.supabase.co/functions/v1/doctorpet-vet-news-release-data"
PHOTO_NAME="doctorpet-synthetic-000.png"
PHOTO_URL=SITE+"licensed-media/"+PHOTO_NAME
HTML=pathlib.Path(__file__).with_name("r55-licensed-media-attributed-ui.html").read_text(encoding="utf-8")
assert "img-src 'self'" in HTML, "BLOCKER: CSP must allow same-origin approved images"
assert "img-src 'none'" not in HTML, "BLOCKER: CSP denies every licensed image"
PLACEHOLDER="const LICENSED_ARTICLE_MEDIA=Object.freeze({});"
assert HTML.count(PLACEHOLDER)==1

req=urllib.request.Request(API,headers={"Origin":ORIGIN},method="GET")
with urllib.request.urlopen(req,timeout=18) as resp:
    assert resp.status==200 and resp.headers.get("Access-Control-Allow-Origin")==ORIGIN
    data=json.loads(resp.read(1500000))
rows=data["groups"]["FEED_DAILYGAEWON"]
assert len(rows)>0 and not data["groups"]["REF_DAILYVET"] and not data["groups"]["REF_HAPPYPET"]
assert all(r["image"] is None and r["excerpt"] is None for r in rows)
row=max(rows,key=lambda r:(r["publishedAt"] or "",r["id"]))
credit="© DoctorPet original SYNTHETIC test photo"
intro="닥터펫 자체 작성 테스트 소개글입니다. 실제 원문 기사의 내용을 설명하거나 인용하지 않는 가상 데이터입니다."
manifest={row["id"]:{"sourceId":"FEED_DAILYGAEWON","articleUrl":row["url"],
 "photoRights":"OWNED_OR_LICENSED","photoFile":PHOTO_NAME,"photoAttribution":credit,
 "summaryRights":"EDITORIAL_VERIFIED","summary":intro}}
fixture=HTML.replace(PLACEHOLDER,"const LICENSED_ARTICLE_MEDIA=Object.freeze("+json.dumps(manifest,ensure_ascii=False)+");")

def photo():
    def chunk(kind,data):
        return struct.pack("!I",len(data))+kind+data+struct.pack("!I",zlib.crc32(kind+data)&0xffffffff)
    pix=b"\x00\xff\x00\x00\xff"
    return (b"\x89PNG\r\n\x1a\n"+
      chunk(b"IHDR",struct.pack("!IIBBBBB",1,1,8,6,0,0,0))+
      chunk(b"IDAT",zlib.compress(pix))+
      chunk(b"IEND",b""))

with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,args=["--no-sandbox","--disable-dev-shm-usage"],channel="chrome")
    for image_status in (200,404):
        context=browser.new_context(viewport={"width":390,"height":850},locale="ko-KR")
        page=context.new_page()
        image_requests=[]
        other_requests=[]
        def route_req(route):
            req=route.request
            if req.is_navigation_request() and req.url==SITE:
                route.fulfill(status=200,content_type="text/html",body=fixture)
            elif req.url==API:
                route.continue_() # Must use LIVE DEV response, not mock news JSON
            elif req.url==PHOTO_URL:
                image_requests.append(req.url)
                if image_status==200:
                    route.fulfill(status=200,content_type="image/png",body=photo())
                else:
                    route.fulfill(status=404,body="Not found")
            else:
                other_requests.append(req.url)
                route.abort()
        page.route("**/*",route_req)
        page.goto(SITE,wait_until="domcontentloaded",timeout=25000)
        page.locator("#apiStatus[data-kind='ready']").wait_for(timeout=25000)
        assert page.locator(".news-card").count()==len(rows)
        img=page.locator(".thumb img").first
        img.scroll_into_view_if_needed()
        expected="loaded" if image_status==200 else "error"
        page.locator(f'.thumb[data-photo="{expected}"]').first.wait_for(timeout=12000)
        assert len(image_requests)==1,(image_status,"wrong synthetic image requests",image_requests)
        assert page.locator(".thumb img").count()==1
        assert page.locator(".thumb[data-photo='loaded']").count()==(1 if image_status==200 else 0)
        attribution=page.locator(".media-attribution").first
        assert attribution.inner_text()==credit
        if image_status==200:
            assert img.evaluate("(img)=>img.naturalWidth")==1
            assert attribution.is_visible(),"photo loaded but licensed photo attribution hidden"
        else:
            assert not attribution.is_visible(),"failed image should not show a false photo credit"
            assert page.locator(".thumb[data-photo='error'] .placeholder").first.is_visible()
        assert intro in page.locator(".news-card").first.inner_text()
        assert not other_requests,other_requests
        assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")
        print("R5.6 PASS: LIVE DEV API",len(rows),"articles; SYNTHETIC same-origin image",image_status,
              "=>",expected,"credit verified, media failures fail safely")
        context.close()
    browser.close()
print("R5.6 complete: actual image decoded, credit displayed, missing-file fallback, original publisher images 0, no deployment.")
