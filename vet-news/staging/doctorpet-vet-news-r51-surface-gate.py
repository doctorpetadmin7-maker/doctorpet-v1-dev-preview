#!/usr/bin/env python3
"""R5.1: DEV-only read-only guard for explicitly disabled legacy news endpoints.
Run without credentials or API keys. No publisher fetch, claim, DB writes or deploy.
"""
import urllib.request
import urllib.error

ROOT="https://mabvxdcpmfdzrqlgkxqn.supabase.co/functions/v1/"
STALE=(
 "doctorpet-news-public-preview",
 "doctorpet-news-static-publisher",
 "doctorpet-news-public-data",
 "doctorpet-vet-news-dev-data",
 "doctorpet-vet-news-member",
)
GITHUB_ORIGIN="https://doctorpetadmin7-maker.github.io"
for slug in STALE:
    for origin in (None,GITHUB_ORIGIN):
        headers={"Accept":"application/json"}
        if origin:headers["Origin"]=origin
        request=urllib.request.Request(ROOT+slug,method="GET",headers=headers)
        try:
            with urllib.request.urlopen(request,timeout=15) as response:
                status=response.status
                body=response.read(20000)
                headers=dict(response.headers)
        except urllib.error.HTTPError as err:
            status=err.code
            body=err.read(20000)
            headers=dict(err.headers)
        assert status==410, (slug,origin,status,body[:200])
        lower=body.lower()
        for forbidden in (b"private_reference_trials",b"source_url",b"imageurl",b"preview_image_metadata",b"publishedat",b"access_token"):
            assert forbidden not in lower,(slug,"Sensitive field in 410 response",forbidden)
        assert b"disabled" in lower or b"feature_deferred" in lower,(slug,"unexpected response")
        assert "no-store" in headers.get("Cache-Control",""),(slug,"no-cache missing")
        print("PASS R5.1 disabled HTTP 410",slug,"browser-origin" if origin else "no-origin")

# The nonpublic news-authority endpoint must not permit unauthenticated requests.
for suffix in ("doctorpet-news-authority/verify","doctorpet-news-authority/domestic-news"):
    req=urllib.request.Request(ROOT+suffix,method="GET",
        headers={"Origin":"https://doctorpet-032-review.suppoess77.chatgpt.site"})
    try:
        with urllib.request.urlopen(req,timeout=15) as response:
            status=response.status
    except urllib.error.HTTPError as err:
        status=err.code
        err.read(1000)
    assert status in (401,403), ("unauthenticated news authority unexpectedly responded",suffix,status)
    print("PASS R5.1 anonymous authority blocked",suffix,status)

print("R5.1 PASS: five disabled DEV news functions, two authenticated authority paths, no rights-sensitive response.")
