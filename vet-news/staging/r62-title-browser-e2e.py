#!/usr/bin/env python3
"""R6.2: LIVE DEV API -> actual browser -> one corrected article title.
The candidate HTML is injected only into a temporary browser document at
an approved Origin. No site/public deployment, DB write, publisher requests.
"""
import pathlib, shutil
from playwright.sync_api import sync_playwright
SITE="https://doctorpetadmin7-maker.github.io/doctorpet-v1-dev-preview/vet-news/"
API="https://mabvxdcpmfdzrqlgkxqn.supabase.co/functions/v1/doctorpet-vet-news-release-data"
HTML=pathlib.Path(__file__).with_name("r62-title-encoding-review-only.html").read_text("utf-8")
CORRECT="대수회 28대 집행부 ‘동물보호·복지위원회’ 첫 회의"
BROKEN="대수회 28대 집행부 ‘동물보��·복지위원회’ 첫 회의"
DUP="힐스코리아, Jody Lulich 교수 초청 ‘요로 심포지엄’ 성공적으로 마쳐"
with sync_playwright() as pw:
    executable=next((shutil.which(x) for x in ("google-chrome","chromium","chromium-browser") if shutil.which(x)),None)
    opts={"headless":True,"args":["--no-sandbox","--disable-dev-shm-usage"]}
    if executable:opts["executable_path"]=executable
    browser=pw.chromium.launch(**opts)
    ctx=browser.new_context(viewport={"width":390,"height":844},locale="ko-KR",timezone_id="Asia/Seoul")
    page=ctx.new_page()
    bad=[]
    api=[]
    page.on("pageerror",lambda error:bad.append(str(error)))
    page.on("response",lambda res:api.append(res.status) if res.url==API else None)
    def route(route):
        request=route.request
        if request.is_navigation_request() and request.url==SITE:
            route.fulfill(status=200,content_type="text/html; charset=utf-8",body=HTML)
        elif request.url==API and request.method=="GET":
            route.continue_()  # LIVE API, not a fixture!
        else:
            bad.append("Unplanned request: "+request.url)
            route.abort()
    page.route("**/*",route)
    page.goto(SITE,wait_until="domcontentloaded",timeout=30000)
    page.locator("#apiStatus[data-kind='ready']").wait_for(timeout=30000)
    assert api==[200],("Actual API/CORS mismatch",api)
    assert page.locator(".news-card").count()==64
    headlines=page.locator("h3.headline").all_inner_texts()
    assert CORRECT in headlines, "18660 official title not displayed"
    assert BROKEN not in headlines, "Stored damaged title leaked into rendering"
    page.locator("#searchInput").fill("동물보호·복지위원회")
    assert page.locator(".news-card").count()==1
    assert page.locator(".headline").first.inner_text()==CORRECT
    assert page.locator(".card-link").first.get_attribute("href")=="https://www.dailygaewon.com/news/articleView.html?idxno=18660"
    page.locator("#clearButton").click()
    page.locator("#searchInput").fill(DUP)
    assert page.locator(".news-card").count()==2, "Distinct original articles were accidentally merged"
    links=set(page.locator(".card-link").evaluate_all("(els)=>els.map(el=>el.href)"))
    assert links=={
        "https://www.dailygaewon.com/news/articleView.html?idxno=18594",
        "https://www.dailygaewon.com/news/articleView.html?idxno=18617"
    },links
    page.locator("#clearButton").click()
    page.locator('[data-source="REF_DAILYVET"]').click()
    assert page.locator(".news-card").count()==0, "Private source unexpectedly visible"
    assert not bad,bad
    print("PASS R6.2 browser 390px: LIVE DEV API 64, official 18660 visible, broken text hidden, 2 distinct duplicate-title URLs preserved; blocked source 0, writes 0")
    ctx.close()
    browser.close()
