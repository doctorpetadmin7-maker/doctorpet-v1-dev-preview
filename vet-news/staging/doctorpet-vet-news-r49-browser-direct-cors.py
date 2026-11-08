#!/usr/bin/env python3
"""R4.9 - actual cross-origin browser GET to existing DEV API under GitHub Pages origin.

The staging HTML is supplied via Playwright route.fulfill at the GitHub Pages URL.
This does NOT publish/replace the public web site. The browser itself sends
the real request to Supabase: NO interception/mocking of the API response.
Read-only: no collection, claims, DB writes, or publisher requests.
"""
from pathlib import Path
from urllib.parse import urlsplit
import shutil
from playwright.sync_api import sync_playwright

DEV_API="https://mabvxdcpmfdzrqlgkxqn.supabase.co/functions/v1/doctorpet-vet-news-release-data"
SITE_URL="https://doctorpetadmin7-maker.github.io/doctorpet-v1-dev-preview/vet-news/"
DENIED_URL="https://unapproved.invalid/vet-news/"
R4_HTML=Path(__file__).with_name("r4_5-rights-safe-ui.html").read_text(encoding="utf-8")
assert f"const API='{DEV_API}';" in R4_HTML
browser_errors=[]
def test_view(browser, width, url, expect_allowed):
    ctx=browser.new_context(viewport={"width":width,"height":850},locale="ko-KR",timezone_id="Asia/Seoul")
    page=ctx.new_page()
    api_req=[]
    api_res=[]
    unexpected=[]
    console_errors=[]
    page.on("pageerror",lambda exc:browser_errors.append(str(exc)))
    page.on("console",lambda msg:console_errors.append(msg.text) if msg.type=="error" else None)
    page.on("request",lambda req:api_req.append(req) if req.url.split("?")[0]==DEV_API else None)
    page.on("response",lambda res:api_res.append(res) if res.url.split("?")[0]==DEV_API else None)
    def route_cb(route):
        rq=route.request
        if rq.is_navigation_request() and rq.url==url:
            route.fulfill(status=200,content_type="text/html; charset=utf-8",body=R4_HTML,
                headers={"Cache-Control":"no-store","X-Robots-Tag":"noindex, nofollow"})
        elif rq.url.split("?")[0]==DEV_API and rq.method=="GET":
            route.continue_() # IMPORTANT: real Chromium HTTP fetch and browser CORS checks
        else:
            unexpected.append(rq.url)
            route.abort()
    page.route("**/*",route_cb)
    page.goto(url,wait_until="domcontentloaded",timeout=25000)
    assert page.evaluate("location.origin")==urlsplit(url).scheme+"://"+urlsplit(url).hostname, "wrong browser origin"
    if expect_allowed:
        page.locator("#apiStatus[data-kind='ready']").wait_for(state="visible",timeout=25000)
        assert len(api_req)==1,("API request count",width,len(api_req))
        assert len(api_res)==1 and api_res[0].status==200,("API status",width,[r.status for r in api_res])
        assert api_req[0].headers.get("origin")=="https://doctorpetadmin7-maker.github.io", "Unexpected origin request header"
        assert api_res[0].headers.get("access-control-allow-origin")=="https://doctorpetadmin7-maker.github.io", "CORS denied"
        assert "no-store" in api_res[0].headers.get("cache-control",""),"Cache policy"
        assert page.locator(".news-card").count()==64,(width,"rows",page.locator(".news-card").count())
        assert page.locator(".thumb[data-photo='withheld']").count()==64, "Photos were not withheld"
        assert page.locator("img").count()==0, "External images should never render"
        assert page.locator("#pageNext").is_disabled() and page.locator("#pagePrev").is_disabled()
        assert page.evaluate("document.documentElement.scrollWidth<=innerWidth"),(width,"page overflow")
        header=page.locator(".news-card h3.headline").first.inner_text()
        first_link=page.locator("a.card-link").first
        assert first_link.get_attribute("href").startswith("https://www.dailygaewon.com/")
        assert first_link.get_attribute("target")=="_blank"
        for src in ("REF_DAILYVET","REF_HAPPYPET"):
            page.locator(f"[data-source='{src}']").click()
            assert page.locator(".news-card").count()==0, "Private publisher visible"
            assert "보관 중" in page.locator("#newsResult").inner_text(), "Missing hold message"
        page.locator("[data-source='all']").click()
        term=header[:2]
        page.locator("#searchInput").fill(term)
        matches=page.locator(".news-card").count()
        assert 0 < matches <= 64, "Search returned empty or invalid"
        for title in page.locator("h3.headline").all_inner_texts():
            assert term.lower() in title.lower(), "Wrong search result"
        page.locator("#clearButton").click()
        assert page.locator(".news-card").count()==64, "Clear search failed"
        assert page.locator("#searchInput").input_value()==""
        assert page.locator("#apiStatus").get_attribute("data-kind")=="ready"
        print(f"R4.9 PASS {width}px REAL-BROWSER CORS: origin=GitHub Pages, API HTTP 200, metadata=64, search, sources, links, photos=0, no overflow")
    else:
        page.locator("#apiStatus[data-kind='error']").wait_for(state="visible",timeout=25000)
        assert len(api_req)==1 and len(api_res)==1, "Denied-origin request missing"
        assert api_res[0].status==403,("Expected real HTTP 403",api_res[0].status)
        assert page.locator(".news-card").count()==0, "Fail-closed browser leaked rows"
        print("R4.9 PASS denied browser origin: real API HTTP 403, UI fail-closed, rows=0")
    assert not unexpected,(width,"Unexpected outbound requests",unexpected)
    assert not browser_errors,(width,"JavaScript errors",browser_errors)
    if expect_allowed:
        assert not console_errors,(width,"Browser console error",console_errors)
    ctx.close()
with sync_playwright() as pw:
    browser_args={"headless":True,"args":["--no-sandbox","--disable-dev-shm-usage"]}
    system_chrome=next((shutil.which(name) for name in ("google-chrome","chromium","chromium-browser") if shutil.which(name)),None)
    if system_chrome:
        browser_args["executable_path"]=system_chrome
    browser=pw.chromium.launch(**browser_args)
    for w in (1440,390,360,320):
        test_view(browser,w,SITE_URL,True)
    test_view(browser,390,DENIED_URL,False)
    browser.close()
print("R4.9 FINAL PASS: REAL Chromium browser requests to DEV API under simulated GitHub Pages document origin; 4 approved viewports + denied origin, NO public deployment.")
