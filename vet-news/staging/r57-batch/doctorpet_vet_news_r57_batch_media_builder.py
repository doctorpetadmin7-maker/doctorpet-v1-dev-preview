#!/usr/bin/env python3
"""Build a *review-only* news-card HTML from documented, locally available assets.

No network calls, collection, external sends, GitHub writes, or deployment. A record
of permission is required but does NOT itself prove that permission is genuine.
The review owner must independently verify every right before using the output.
"""
from __future__ import annotations
import argparse
import csv
from datetime import date
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import struct
import zlib
from urllib.parse import urlsplit

COLS = (
    'article_id', 'source_id', 'article_url',
    'photo_file', 'photo_sha256', 'photo_rights_basis',
    'photo_approval_ref', 'photo_credit', 'photo_rights_until',
    'summary_ko', 'summary_rights_basis', 'summary_review_ref',
)
MAX_ROWS = 2000
MAX_FILE_BYTES = 5 * 1024 * 1024
PHOTO_NAME = re.compile(r'[a-zA-Z0-9_-]{8,100}\.(?:webp|png|jpe?g)\Z', re.IGNORECASE)
EVIDENCE = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.:/-]{5,128}\Z')
SUPPORTED_PHOTO = {'ORIGINAL_OWNED', 'LICENSED'}
SUPPORTED_SUMMARY = {'ORIGINAL_EDITORIAL', 'LICENSED_TEXT'}
PLACEHOLDER = 'const LICENSED_ARTICLE_MEDIA=Object.freeze({});'


def abort(msg: str) -> None:
    raise ValueError(msg)


def safe_text(value: str, *, field: str, max_len: int) -> str:
    if len(value) > max_len or any(x in value for x in '<>\x00\r\n'):
        abort(f'{field}: invalid text or length')
    return value


def parse_articles(source: Path) -> dict[str, dict]:
    obj = json.loads(source.read_text(encoding='utf-8'))
    if not isinstance(obj, dict) or obj.get('version') != 2 or obj.get('pageSize') != 100:
        abort('snapshot must be the v2 sanitised DEV release-data contract')
    groups = obj.get('groups')
    if not isinstance(groups, dict) or set(groups) != {'FEED_DAILYGAEWON', 'REF_DAILYVET', 'REF_HAPPYPET'}:
        abort('snapshot group contract mismatch')
    if groups['REF_DAILYVET'] != [] or groups['REF_HAPPYPET'] != []:
        abort('snapshot contains private trial rows')
    states = obj.get('states')
    if not isinstance(states, dict):
        abort('snapshot rights states absent')
    for restricted in ('REF_DAILYVET', 'REF_HAPPYPET'):
        state = states.get(restricted)
        if (not isinstance(state, dict) or state.get('publicationStatus') != 'WITHHELD_RIGHTS_PENDING'
                or state.get('actualCount') != 0):
            abort('snapshot private source disclosure gate changed')
    if obj.get('candidates', {}).get('visibleInRelease') is not False:
        abort('snapshot unpublished candidate gate changed')
    rows = groups['FEED_DAILYGAEWON']
    if not isinstance(rows, list) or len(rows) > MAX_ROWS:
        abort('invalid snapshot articles')
    answer, seen_urls = {}, set()
    for item in rows:
        if not isinstance(item, dict) or item.get('sourceId') != 'FEED_DAILYGAEWON' or item.get('actualStored') is not True:
            abort('unapproved source in snapshot')
        if (item.get('image') is not None or item.get('excerpt') is not None
                or item.get('imageState') != 'WITHHELD_RIGHTS_PENDING'
                or item.get('excerptState') != 'WITHHELD_RIGHTS_PENDING'):
            abort('snapshot media rights gate changed')
        forbidden = {'body', 'content', 'articleHtml', 'previewImage', 'imageUrl', 'summary', 'listExcerpt'}
        if any(key in item for key in forbidden):
            abort('snapshot contains private publication fields')
        article_id, url = item.get('id'), item.get('url')
        if (not isinstance(article_id, str) or not isinstance(url, str)
                or not article_id or article_id in answer or url in seen_urls):
            abort('invalid or duplicate article ID or URL')
        validate_source_url(url)
        seen_urls.add(url)
        answer[article_id] = item
    return answer


def validate_source_url(url: str) -> None:
    try:
        parsed = urlsplit(url)
        if (parsed.scheme != 'https' or parsed.hostname not in ('www.dailygaewon.com','dailygaewon.com')
            or parsed.username or parsed.password or parsed.port or parsed.fragment
            or not parsed.path.startswith('/news/')):
            abort('article URL outside approved metadata host/path')
    except ValueError:
        abort('malformed article URL')


def verify_image(contents: bytes, ext: str) -> bool:
    """Check container structure, not just magic bytes; browser decode is still required."""
    ext = ext.lower()
    if ext in ('.jpg', '.jpeg'):
        # A JPEG SOI without its EOI is never a usable browser thumbnail.
        return contents.startswith(b'\xff\xd8\xff') and contents.endswith(b'\xff\xd9')
    if ext == '.png':
        if not contents.startswith(b'\x89PNG\r\n\x1a\n'):
            return False
        pos, found_ihdr, found_idat = 8, False, False
        while pos + 12 <= len(contents):
            n = int.from_bytes(contents[pos:pos+4], 'big')
            if n > MAX_FILE_BYTES or pos + 12 + n > len(contents):
                return False
            kind = contents[pos+4:pos+8]
            body = contents[pos+8:pos+8+n]
            crc = int.from_bytes(contents[pos+8+n:pos+12+n], 'big')
            if zlib.crc32(kind + body) & 0xffffffff != crc:
                return False
            pos += 12 + n
            if not found_ihdr:
                if kind != b'IHDR' or n != 13:
                    return False
                width, height = struct.unpack('>II', body[:8])
                if not 1 <= width <= 20000 or not 1 <= height <= 20000:
                    return False
                found_ihdr = True
            if kind == b'IDAT':
                found_idat = True
            if kind == b'IEND':
                return found_ihdr and found_idat and n == 0 and pos == len(contents)
        return False
    if ext == '.webp':
        if contents[:4] != b'RIFF' or contents[8:12] != b'WEBP':
            return False
        riff_length = int.from_bytes(contents[4:8], 'little')
        return riff_length + 8 == len(contents) and contents[12:16] in (b'VP8 ', b'VP8L', b'VP8X')
    return False


def validate_photo(row: dict[str,str], asset_dir: Path, seen: set[str]) -> dict:
    keys = ('photo_file','photo_sha256','photo_rights_basis','photo_approval_ref','photo_credit','photo_rights_until')
    if not any(row[k] for k in keys):
        return {}
    base, given_hash, rights, evidence, credit, end_date = (row[k] for k in keys)
    if not PHOTO_NAME.fullmatch(base) or base in seen:
        abort('photo file name invalid or duplicate')
    if rights not in SUPPORTED_PHOTO or not EVIDENCE.fullmatch(evidence) or not safe_text(credit, field='photo credit', max_len=200).strip():
        abort('photo rights, record reference or attribution incomplete')
    if not re.fullmatch(r'[0-9a-fA-F]{64}', given_hash):
        abort('photo SHA-256 missing or invalid')
    if rights == 'LICENSED' and not end_date:
        abort('licensed photos require an expiry date; use a reviewed date for indefinite rights')
    if end_date:
        try:
            end = date.fromisoformat(end_date)
        except ValueError:
            abort('invalid photo rights expiry')
        if end < date.today():
            abort('expired photo rights')
    path = (asset_dir / base).resolve()
    if path.parent != asset_dir.resolve() or not path.is_file():
        abort('photo not found inside approved local licensed-media directory')
    if not (64 <= path.stat().st_size <= MAX_FILE_BYTES):
        abort('photo file size outside allowed range')
    contents = path.read_bytes()
    if not verify_image(contents, path.suffix):
        abort('file extension does not match a permitted image signature')
    if hashlib.sha256(contents).hexdigest().lower() != given_hash.lower():
        abort('photo SHA256 does not match supplied local file')
    seen.add(base)
    return {'photoRights':'OWNED_OR_LICENSED','photoFile':base,'photoAttribution':credit}


def validate_summary(row: dict[str,str]) -> dict:
    fields = ('summary_ko','summary_rights_basis','summary_review_ref')
    if not any(row[k] for k in fields):
        return {}
    summary, rights, evidence = (row[k] for k in fields)
    summary = summary.strip()
    if rights not in SUPPORTED_SUMMARY or not EVIDENCE.fullmatch(evidence):
        abort('summary review rights or evidence missing')
    if not 12 <= len(summary) <= 280:
        abort('summary length must be 12..280 characters')
    safe_text(summary, field='summary',max_len=280)
    return {'summaryRights':'EDITORIAL_VERIFIED','summary':summary}


def build(rows: list[dict[str,str]], article_map:dict, photo_dir:Path) -> tuple[dict,int,int]:
    seen_articles, seen_files = set(), set()
    manifest={}
    n_img=n_summary=0
    if len(rows)>MAX_ROWS:
        abort('too many media approval records')
    for index,row in enumerate(rows,2):
        article_id=row['article_id']
        if not article_id or article_id in seen_articles:
            abort(f'row {index}: missing/duplicate article ID')
        seen_articles.add(article_id)
        article=article_map.get(article_id)
        if article is None or row['source_id']!='FEED_DAILYGAEWON' or article['url'] != row['article_url']:
            abort(f'row {index}: article not present or mismatched in the DEV sanitised snapshot')
        photo = validate_photo(row,photo_dir,seen_files)
        summary = validate_summary(row)
        if not photo and not summary:
            continue  # Pending: not a permitted publication asset.
        manifest[article_id]={'articleUrl':row['article_url'],'sourceId':row['source_id'],**photo,**summary}
        n_img+=bool(photo)
        n_summary+=bool(summary)
    return manifest,n_img,n_summary


def run(args) -> tuple[int,int,int]:
    source_csv=Path(args.csv)
    media_dir=Path(args.media_dir).resolve()
    template=Path(args.template)
    output=Path(args.output)
    # The HTML resolves the exact same-origin ./licensed-media/ folder at runtime.
    if media_dir != (output.parent/'licensed-media').resolve():
        abort('media_dir must be the licensed-media subdirectory alongside output HTML')
    if output.exists():
        abort('output already exists; never overwrite review or public site files')
    with source_csv.open(encoding='utf-8-sig',newline='') as fp:
        reader=csv.DictReader(fp)
        if tuple(reader.fieldnames or ()) != COLS:
            abort('CSV columns must match approved intake template exactly')
        rows=[]
        for row in reader:
            if None in row or any(v is None for v in row.values()):
                abort('malformed CSV row')
            rows.append({k:v.strip() for k,v in row.items()})
    snapshot=parse_articles(Path(args.snapshot))
    manifest, n_img, n_summary=build(rows,snapshot,media_dir)
    html=template.read_text(encoding='utf-8')
    if (html.count(PLACEHOLDER)!=1 or not html.startswith('<!doctype html>')
            or 'class=\"media-attribution\"' not in html):
        abort('R5.7/R5.6 attribution-ready template is required')
    raw=json.dumps(manifest,ensure_ascii=False,sort_keys=True,separators=(',',':'))
    raw=raw.replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026').replace('\u2028','\\u2028').replace('\u2029','\\u2029')
    built=html.replace(PLACEHOLDER, 'const LICENSED_ARTICLE_MEDIA=Object.freeze('+raw+');')
    output.parent.mkdir(parents=True,exist_ok=True)
    # Never publish. Link is atomic and FAILS if another process created the output
    # after the preflight check (os.replace would silently overwrite in that race).
    fd, tmp=tempfile.mkstemp(prefix='vet-news-r57-',suffix='.tmp',dir=output.parent)
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as fo:
            fo.write(built)
            fo.flush()
            os.fsync(fo.fileno())
        os.link(tmp,output)  # atomic no-overwrite: FileExistsError -> HOLD
    finally:
        if os.path.exists(tmp):os.unlink(tmp)
    return len(manifest),n_img,n_summary


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for field in ('csv','snapshot','media-dir','template','output'):
        parser.add_argument('--'+field,required=True)
    args=parser.parse_args()
    try:
        n,images,summaries=run(args)
    except (ValueError,OSError,KeyError,TypeError,json.JSONDecodeError) as exc:
        print('HOLD — review bundle not generated: '+str(exc),file=sys.stderr)
        return 2
    print(f'PASS — REVIEW ONLY: {n} article mappings, {images} local verified-image files, {summaries} reviewed two-line texts. NO publishing, NO rights independently confirmed.')
    return 0

if __name__=='__main__':raise SystemExit(main())