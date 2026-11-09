#!/usr/bin/env python3
"""R6.5: DailyGaewon only, bounded rights-pending OG photo URL inventory.

EXPLICIT SAFETY BOUNDS:
- Existing 64 exact approved DEV article URLs only. No DailyVet, HappyPet or FarmInsight.
- robots.txt permission checked first, fail closed for 401/403, network errors.
- Metadata discovery ONLY. No image bytes downloaded or mirrored, no full article
  body saved, no DB, cron, permissions, storage, production or public page writes.
- Low rate, sequential GET, no publisher bypass, per-page 1.5MiB cap.
- Output CSV/JSON has public photo URLs only and RIGHTS_NOT_VERIFIED.
The artifact does not grant copyright permission to publish or hotlink photos.
"""
import argparse,csv,hashlib,html,json,pathlib,re,time,urllib.error,urllib.parse,urllib.request,urllib.robotparser
from html.parser import HTMLParser
from datetime import datetime,timezone
from collections import Counter

SOURCE="FEED_DAILYGAEWON"
HOST="www.dailygaewon.com"
BASE=f"https://{HOST}/news/articleView.html?idxno="
IDS="18675,18674,18673,18672,18671,18670,18668,18667,18664,18662,18661,18660,18659,18657,18655,18654,18653,18652,18651,18650,18649,18629,18560,18648,18647,18644,18646,18645,18643,18642,18641,18640,18637,18635,18634,18632,18630,18627,18626,18625,18623,18622,18620,18619,18618,18617,18616,18614,18612,18609,18608,18604,18603,18602,18601,18600,18582,18599,18598,18597,18596,18594,18593,18633".split(",")
assert len(IDS)==64 and len(set(IDS))==64
UA="DoctorPet-private-article-image-inventory/1.0 (+contact: publisher rights review)"
MAX_HTML=1536*1024
class NoOffsiteRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        parts=urllib.parse.urlsplit(newurl)
        if parts.scheme!="https" or parts.hostname!=HOST:
            raise ValueError("OFFSITE_OR_NONHTTPS_REDIRECT_BLOCKED")
        return super().redirect_request(req,fp,code,msg,headers,newurl)
opener=urllib.request.build_opener(NoOffsiteRedirect)
def get(url,limit=MAX_HTML):
    req=urllib.request.Request(url,headers={"User-Agent":UA,"Accept":"text/html,application/xhtml+xml;q=0.9,*/*;q=0.2","Accept-Language":"ko-KR,ko;q=0.8"},method="GET")
    with opener.open(req,timeout=18) as res:
        b=res.read(limit+1)
        if len(b)>limit:raise ValueError("RESPONSE_TOO_LARGE")
        return res.status,res.headers,b
class OgParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True);self.tags=[];self.links=[]
    def handle_starttag(self,tag,attr):
        a={str(k).lower():v for k,v in attr if k and v is not None}
        if tag=="meta":
            key=(a.get("property") or a.get("name") or "").lower()
            val=a.get("content")
            if key in ("og:image","og:image:url","twitter:image","twitter:image:src") and val:self.tags.append((key,val))
        if tag=="link" and "image_src" in (a.get("rel") or "").lower() and a.get("href"):
            self.links.append(("link:image_src",a["href"]))
def strict_utf8(body,headers):
    ct=headers.get("Content-Type","").lower()
    charset=re.search(r"charset\s*=\s*['\"]?([a-z0-9_-]+)",ct)
    encoding=charset.group(1) if charset else "utf-8"
    if encoding not in ("utf-8","utf8","euc-kr","cp949"):raise ValueError("UNSUPPORTED_DECLARED_CHARSET_"+encoding)
    try:return body.decode(encoding,errors="strict")
    except UnicodeError:raise ValueError("NONLOSSLESS_HTML_DECODING")
def image_candidate(baseurl,val):
    u=urllib.parse.urljoin(baseurl,html.unescape(str(val)).strip())
    x=urllib.parse.urlsplit(u)
    if x.scheme not in ("https","http") or not x.hostname:return None
    # No active image fetch here. Host recorded for later permission audit.
    if x.username or x.password:return None
    return u
def robots_allowed():
    try:
        status,headers,b=get(f"https://{HOST}/robots.txt",limit=262144)
        if status!=200:return False,"ROBOTS_BAD_STATUS_"+str(status)
        p=urllib.robotparser.RobotFileParser();p.parse(b.decode("utf-8","replace").splitlines())
        forbidden=[article for article in IDS if not p.can_fetch(UA,BASE+article)]
        return len(forbidden)==0,"ALLOW" if not forbidden else "DISALLOWED_ARTICLE_COUNT_"+str(len(forbidden))
    except urllib.error.HTTPError as e:
        # 404 means no robots policy is advertised; never override 401/403.
        if e.code==404:return True,"ROBOTS_404_NO_POLICY"
        return False,"ROBOTS_HTTP_"+str(e.code)
    except Exception as e:return False,"ROBOTS_CHECK_ERROR_"+type(e).__name__
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--limit",type=int,choices=(2,3,64),default=3)
    ap.add_argument("--output",default="r65-photo-inventory")
    args=ap.parse_args()
    allowed,robots_reason=robots_allowed()
    print("R65_ROBOTS",robots_reason,flush=True)
    if not allowed:raise SystemExit("Stopped: robots/access check not clear; no article page requests.")
    targets=IDS if args.limit==64 else IDS[:args.limit]
    records=[]
    for pos,idx in enumerate(targets,1):
        url=BASE+idx
        item={"source_id":SOURCE,"article_no":idx,"article_url":url,"photo_url":"","photo_origin":"","photo_method":"",
              "page_http":None,"page_sha256":"","result":"UNKNOWN",
              "rights":"RIGHTS_NOT_VERIFIED","photo_file_downloaded":False}
        try:
            status,headers,b=get(url)
            item["page_http"]=status
            item["page_sha256"]=hashlib.sha256(b).hexdigest()
            ct=headers.get("Content-Type","")
            if "html" not in ct.lower() and not b[:100].lower().startswith(b"<!doctype html"):
                item["result"]="NON_HTML"
            else:
                parser=OgParser();parser.feed(strict_utf8(b,headers))
                candidates=parser.tags+parser.links
                valid=[(kind,image_candidate(url,val)) for kind,val in candidates]
                valid=[(kind,link) for kind,link in valid if link]
                if valid:
                    # Prefer the publisher's declared OpenGraph article image.
                    method,img=valid[0]
                    item["photo_url"]=img;item["photo_origin"]=urllib.parse.urlsplit(img).hostname
                    item["photo_method"]=method
                    item["result"]="PHOTO_URL_EXTRACTED"
                else:item["result"]="NO_OG_PHOTO"
        except urllib.error.HTTPError as ex:item["page_http"]=ex.code;item["result"]="HTTP_"+str(ex.code)
        except Exception as ex:item["result"]="FETCH_OR_PARSE_"+type(ex).__name__
        records.append(item)
        print("R65_SCAN",pos,"/",len(targets),idx,item["result"],item["photo_method"],flush=True)
        if pos<len(targets):time.sleep(1.35)
    root=pathlib.Path(args.output);root.parent.mkdir(parents=True,exist_ok=True)
    with root.with_suffix(".csv").open("w",newline="",encoding="utf-8-sig") as f:
        writer=csv.DictWriter(f,fieldnames=list(records[0]));writer.writeheader();writer.writerows(records)
    with root.with_suffix(".json").open("w",encoding="utf-8") as f:
        json.dump({"created_utc":datetime.now(timezone.utc).isoformat(),"robots":robots_reason,
          "requested":len(targets),"summary":dict(Counter(r["result"] for r in records)),
          "data":records},f,ensure_ascii=False,indent=2)
    summary=dict(Counter(r["result"] for r in records))
    print("R65_SUMMARY",json.dumps({"requested":len(targets),**summary},sort_keys=True),flush=True)
if __name__=="__main__":main()
