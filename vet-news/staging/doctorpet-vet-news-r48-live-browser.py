#!/usr/bin/env python3
"""Read-only R4.8 full-browser test: live DEV news JSON replayed in staged R4.5 UI.
No requests to publisher sites, mutations, collection, claim, or production.
Browser requests are intercepted; this is NOT a direct browser CORS test.
"""
import json, pathlib, shutil, urllib.request
from playwright.sync_api import sync_playwright

API="https://mabvxdcpmfdzrqlgkxqn.supabase.co/functions/v1/doctorpet-vet-news-release-data"
ORIGIN="https://doctorpetadmin7-maker.github.io"
req=urllib.request.Request(API,headers={"Origin":ORIGIN,"Accept":"application/json"},method="GET")
with urllib.request.urlopen(req,timeout=18) as res:
    assert res.status==200
    assert res.headers.get("Access-Control-Allow-Origin")==ORIGIN
    assert "no-store" in res.headers.get("Cache-Control","")
    payload=json.loads(res.read(1500000))
assert payload["version"]==2 and payload["pageSize"]==100
groups=payload["groups"]; states=payload["states"]
assert set(groups)=={"FEED_DAILYGAEWON","REF_DAILYVET","REF_HAPPYPET"}
assert groups["REF_DAILYVET"]==[] and groups["REF_HAPPYPET"]==[]
for key in ("REF_DAILYVET","REF_HAPPYPET"):
    assert states[key]["publicationStatus"]=="WITHHELD_RIGHTS_PENDING"
    assert states[key]["actualCount"]==0
rows=groups["FEED_DAILYGAEWON"]
assert 0<len(rows)<=2000 and payload["candidates"]["visibleInRelease"] is False
for r in rows:
    assert r["sourceId"]=="FEED_DAILYGAEWON" and r["actualStored"]
    assert r["image"] is None and r["excerpt"] is None
    assert r["imageState"]=="WITHHELD_RIGHTS_PENDING" and r["excerptState"]=="WITHHELD_RIGHTS_PENDING"
    assert r["url"].startswith("https://www.dailygaewon.com/")
    assert isinstance(r["title"],str) and r["title"].strip()
html=pathlib.Path(__file__).with_name("r4_5-rights-safe-ui.html").read_text(encoding="utf-8")
assert f"const API='{API}';" in html
chrome=next((shutil.which(p) for p in ("google-chrome","chromium","chromium-browser") if shutil.which(p)),None)
errors=[]
with sync_playwright() as pw:
    args={"headless":True,"args":["--no-sandbox","--disable-dev-shm-usage"]}
    if chrome:args["executable_path"]=chrome
    browser=pw.chromium.launch(**args)
    for width in (1440,390,360,320):
        page=browser.new_page(viewport={"width":width,"height":850})
        outgoing=[]
        page.on("pageerror",lambda e: errors.append(str(e)))
        page.on("request",lambda request: outgoing.append(request.url) if request.url!=API else None)
        page.route(API,lambda route: route.fulfill(status=200,content_type="application/json",
            headers={"Access-Control-Allow-Origin":"*","Cache-Control":"no-store"},
            body=json.dumps(payload,ensure_ascii=False)))
        page.set_content(html,wait_until="load")
        page.locator(".news-card").first.wait_for(timeout=15000)
        expected=min(100,len(rows))
        assert page.locator(".news-card").count()==expected,(width,"card count")
        assert "DEV 저장 RSS 메타데이터" in page.locator("#apiStatus").inner_text()
        assert page.locator(".thumb[data-photo='withheld']").count()==expected
        assert page.locator(".news-card img").count()==0
        assert page.locator("a.card-link").count()==expected
        assert page.locator("#pagePrev").is_disabled()
        assert page.evaluate("document.documentElement.scrollWidth<=window.innerWidth"),(width,"overflow")
        title=page.locator(".news-card .headline").first.inner_text()
        assert title in [r["title"] for r in rows]
        for restricted in ("REF_DAILYVET","REF_HAPPYPET"):
            page.locator(f'[data-source="{restricted}"]').click()
            assert page.locator(".news-card").count()==0
            assert "보관 중" in page.locator("#newsResult").inner_text()
        page.locator('[data-source="FEED_DAILYGAEWON"]').click()
        assert page.locator(".news-card").count()==expected
        term=title[:2]
        page.locator("#searchInput").fill(term)
        matches=[r for r in rows if term.casefold() in r["title"].casefold()]
        assert page.locator(".news-card").count()==len(matches),(width,"search")
        page.locator("#clearButton").click()
        assert page.locator(".news-card").count()==expected
        assert page.locator("#searchInput").input_value()==""
        for link in page.locator("a.card-link").all():
            assert link.get_attribute("href").startswith("https://www.dailygaewon.com/")
            assert link.get_attribute("target")=="_blank"
        assert not outgoing,(width,"external requests",outgoing[:2])
        print(f"R4.8 PASS browser {width}px: {expected} REAL DEV metadata rows, source selector, search, clear, links, photo hold, no overflow/outgoing network")
        page.close()
    browser.close()
assert not errors,errors
print(f"R4.8 LIVE DEV RESPONSE + FULL BROWSER PASS: {len(rows)} metadata rows, 4 viewports, restricted 0, photos 0")
