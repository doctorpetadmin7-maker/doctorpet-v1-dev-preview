#!/usr/bin/env python3
"""R7.2 -- one-off, bounded DailyVet OG-photo metadata research.

Only 10 EXACT previously stored private article URLs lacking image metadata.
Checks publisher robots policy before requests. One sequential GET/article, no
retry, never claims/resumes existing collector, downloads any photo bytes,
copies article content, edits DB/Storage, or publishes cards. HTTP 403/429 and
robots denial are STOP conditions. This is a rights-pending PRIVATE review.
"""
import csv, hashlib, html, json, pathlib, re, time, urllib.error
import urllib.parse, urllib.request, urllib.robotparser
from collections import Counter
from datetime import datetime, timezone
from html.parser import HTMLParser

HOST="www.dailyvet.co.kr"
ARTICLES=[
 ("303106","https://www.dailyvet.co.kr/news/academy/303106"),
 ("303119","https://www.dailyvet.co.kr/news/college/303119"),
 ("303130","https://www.dailyvet.co.kr/news/academy/303130"),
 ("303159","https://www.dailyvet.co.kr/news/academy/303159"),
 ("303163","https://www.dailyvet.co.kr/news/college/303163"),
 ("303174","https://www.dailyvet.co.kr/news/academy/303174"),
 ("303175","https://www.dailyvet.co.kr/news/policy/303175"),
 ("303197","https://www.dailyvet.co.kr/news/association/303197"),
 ("303224","https://www.dailyvet.co.kr/news/industry/303224"),
 ("303257","https://www.dailyvet.co.kr/news/industry/303257"),
]
assert len(ARTICLES)==10 and len({i for i,_ in ARTICLES})==10
UA="DoctorPet-Private-Metadata-Review/1.0"
MAX_HTML=2_000_000
class SameHostRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,req,fp,code,msg,headers,url):
  p=urllib.parse.urlsplit(url)
  if p.scheme!="https" or p.hostname!=HOST:
   raise RuntimeError("OFFSITE_REDIRECT_BLOCKED")
  return super().redirect_request(req,fp,code,msg,headers,url)
opener=urllib.request.build_opener(SameHostRedirect)
def get(url,max_size):
 req=urllib.request.Request(url,headers={"User-Agent":UA,"Accept":"text/html,application/xhtml+xml;q=0.9,*/*;q=0.1"},method="GET")
 with opener.open(req,timeout=18) as r:
  b=r.read(max_size+1)
  if len(b)>max_size:raise ValueError("HTML_EXCEEDS_2MB")
  return r.status,r.headers,b
def robots_gate():
 try:
  status,headers,b=get("https://www.dailyvet.co.kr/robots.txt",200_000)
  if status!=200:return "STOP_ROBOTS_UNAVAILABLE"
  rp=urllib.robotparser.RobotFileParser();rp.parse(b.decode("utf-8","replace").splitlines())
  if not all(rp.can_fetch(UA,url) for _,url in ARTICLES):return "STOP_ROBOTS_DISALLOW"
  return "ALLOW"
 except urllib.error.HTTPError as e:
  return "ALLOW_ROBOTS_404" if e.code==404 else "STOP_ROBOTS_HTTP_"+str(e.code)
 except Exception as e:return "STOP_ROBOTS_"+type(e).__name__
class Meta(HTMLParser):
 def __init__(self):super().__init__(convert_charrefs=True);self.candidates=[]
 def handle_starttag(self,tag,attrs):
  if tag!="meta":return
  a={k.lower():v for k,v in attrs if k and v}
  k=(a.get("property") or a.get("name") or "").lower()
  if k in {"og:image","og:image:url","og:image:secure_url","twitter:image","twitter:image:src"}:
   self.candidates.append((k,a["content"]))
def safe_img(article_url,val):
 if not val:return None
 try:
  url=urllib.parse.urljoin(article_url,html.unescape(val).strip())
  p=urllib.parse.urlsplit(url)
  if p.scheme!="https" or p.hostname not in ("cdn.dailyvet.co.kr","www.dailyvet.co.kr"):
   return None
  if p.username or p.password or p.port not in (None,443):return None
  if not re.search(r"\.(jpg|jpeg|png|webp)(?:$|\?)",p.path,re.I):return None
  return url
 except (ValueError,TypeError):return None
def main():
 gate=robots_gate()
 print("R72_ROBOTS",gate,flush=True)
 if not gate.startswith("ALLOW"):
  print("R72_ABORT no article requests",flush=True);return 2
 items=[];stopped=False
 for index,(no,url) in enumerate(ARTICLES,1):
  row={"article_no":no,"article_url":url,"image_url":"","meta_method":"","result":"UNKNOWN","http_status":None,
       "article_html_sha256":"","rights":"PUBLISHER_PERMISSION_UNCONFIRMED","photo_bytes_downloaded":0}
  try:
   status,headers,b=get(url,MAX_HTML)
   row["http_status"]=status
   row["article_html_sha256"]=hashlib.sha256(b).hexdigest()
   content_type=headers.get("Content-Type","").lower()
   if not ("text/html" in content_type or "application/xhtml+xml" in content_type):
    row["result"]="NOT_HTML"
   else:
    enc=re.search(r"charset\s*=\s*([a-z0-9_-]+)",content_type)
    charset=enc.group(1) if enc else "utf-8"
    if charset not in ("utf-8","utf8","euc-kr","cp949"):raise ValueError("UNSUPPORTED_DECLARED_CHARSET")
    parser=Meta();parser.feed(b.decode(charset,"strict"))
    for method,candidate in parser.candidates:
     img=safe_img(url,candidate)
     if img:
      row["image_url"]=img;row["meta_method"]=method;break
    row["result"]="PHOTO_URL_FOUND" if row["image_url"] else "NO_SAFE_OG_IMAGE"
  except urllib.error.HTTPError as e:
   row["http_status"]=e.code;row["result"]="HTTP_"+str(e.code)
   if e.code in (401,403,429):
    print("R72_STOP_ACCESS_RESTRICTION",no,e.code,flush=True);stopped=True
  except Exception as e:row["result"]="FETCH_OR_PARSE_"+type(e).__name__
  items.append(row)
  print("R72_SCAN",index,"/",len(ARTICLES),no,row["result"],flush=True)
  if stopped:break
  if index<len(ARTICLES):time.sleep(1.6)
 path=pathlib.Path("r72-dailyvet-10-metadata.json")
 result={"as_of":datetime.now(timezone.utc).isoformat(),"robots_gate":gate,"expected":10,
         "checked":len(items),"result_counts":dict(Counter(r["result"] for r in items)),
         "data":items,"article_text_saved":False,"image_bytes_saved":0,
         "publisher_permission_confirmed":False,"active_collector_modified":False}
 path.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
 with pathlib.Path("r72-dailyvet-10-metadata.csv").open("w",encoding="utf-8-sig",newline="") as f:
  writer=csv.DictWriter(f,fieldnames=list(items[0].keys()));writer.writeheader();writer.writerows(items)
 print("R72_SUMMARY",json.dumps(result["result_counts"],ensure_ascii=False),flush=True)
 return 0
if __name__=="__main__":raise SystemExit(main())
