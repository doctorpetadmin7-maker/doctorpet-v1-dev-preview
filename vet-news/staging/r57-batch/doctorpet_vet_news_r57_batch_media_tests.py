#!/usr/bin/env python3
"""Isolated synthetic test cases; no real third-party photos/rights or external network."""
from __future__ import annotations
import contextlib
import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import zlib
import struct

SCRIPT = Path(__file__).with_name('doctorpet_vet_news_r57_batch_media_builder.py')
COLS=('article_id','source_id','article_url','photo_file','photo_sha256','photo_rights_basis','photo_approval_ref','photo_credit','photo_rights_until','summary_ko','summary_rights_basis','summary_review_ref')


def png_pixel(red:int,green:int,blue:int) -> bytes:
    def chunk(k:bytes,body:bytes) -> bytes:
        return struct.pack('!I',len(body))+k+body+struct.pack('!I',zlib.crc32(k+body)&0xffffffff)
    pixel=bytes((0,red%256,green%256,blue%256,255))
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('!IIBBBBB',1,1,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(pixel))+chunk(b'IEND',b'')


def run_case(rows, articles, root:Path,expect_ok=True,tag='case', snapshot_override=None,allow_existing_output=False):
    report=root/f'{tag}.csv'
    with report.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=COLS)
        w.writeheader();w.writerows(rows)
    snapshot=root/'snapshot.json'
    payload={'version':2,'pageSize':100,'groups':{'FEED_DAILYGAEWON':[dict(x) for x in articles],'REF_DAILYVET':[],'REF_HAPPYPET':[]},
        'states':{'REF_DAILYVET':{'publicationStatus':'WITHHELD_RIGHTS_PENDING','actualCount':0},
                  'REF_HAPPYPET':{'publicationStatus':'WITHHELD_RIGHTS_PENDING','actualCount':0}},
        'candidates':{'visibleInRelease':False}}
    if snapshot_override:
        snapshot_override(payload)
    snapshot.write_text(json.dumps(payload),encoding='utf-8')
    template=root/'template.html'
    template.write_text('<!doctype html>\n<html><script>const LICENSED_ARTICLE_MEDIA=Object.freeze({});</script><small class=\"media-attribution\"></small></html>',encoding='utf-8')
    out=root/f'{tag}.html'
    proc=subprocess.run([sys.executable,str(SCRIPT),'--csv',str(report),'--snapshot',str(snapshot),'--media-dir',str(root/'licensed-media'),'--template',str(template),'--output',str(out)],capture_output=True,text=True)
    if expect_ok:
        assert proc.returncode==0,(tag,proc.stderr)
        assert out.exists(),tag
        return out.read_text(encoding='utf-8')
    assert proc.returncode!=0,(tag,proc.stdout)
    if not allow_existing_output:
        assert not out.exists(),(tag,'unsafe partial output')
    return proc.stderr


def main():
    with tempfile.TemporaryDirectory() as d:
        root=Path(d); photos=root/'licensed-media';photos.mkdir()
        data=[];articles=[]
        for i in range(100):
            url=f'https://www.dailygaewon.com/news/articleView.html?idxno={1000+i}'
            id=f'veterinary-synthetic-{i:03d}'
            name=f'licensed_picture_{i:03d}.png'
            content=png_pixel(i,i*2,i*3)
            (photos/name).write_bytes(content)
            record=dict(article_id=id,source_id='FEED_DAILYGAEWON',article_url=url,
                photo_file=name,photo_sha256=hashlib.sha256(content).hexdigest(),
                photo_rights_basis='ORIGINAL_OWNED',photo_approval_ref='PERMIT-DRPET-100001',
                photo_credit='© Dr.Pet original synthetic test',photo_rights_until='',
                summary_ko='수의계 뉴스를 소개하는 닥터펫 자체 편집 검수용 테스트 문구입니다. 실제 기사 내용과 무관합니다.',
                summary_rights_basis='ORIGINAL_EDITORIAL',summary_review_ref='REVIEW-DRPET-900001')
            data.append(record)
            articles.append({'id':id,'sourceId':'FEED_DAILYGAEWON','url':url,'title':f'가상 테스트 기사 {i}', 'image':None,'excerpt':None,'actualStored':True,'imageState':'WITHHELD_RIGHTS_PENDING','excerptState':'WITHHELD_RIGHTS_PENDING'})
        output=run_case(data,articles,root,True,'all-100')
        assert output.count('licensed_picture_')==100
        assert output.count('ORIGINAL_EDITORIAL')==0, 'private approval basis should not be emitted'
        assert output.count('PERMIT-DRPET-100001')==0, 'private evidence refs must not appear in public HTML'
        print('PASS: 100/100 original synthetic media links + separately reviewed summaries, no evidence IDs embedded')
        failures=[
            ('foreign_source', {'source_id':'REF_DAILYVET'}),
            ('cross_article', {'article_url':'https://www.dailygaewon.com/news/articleView.html?idxno=1003'}),
            ('missing_approval', {'photo_approval_ref':''}),
            ('bad_hash', {'photo_sha256':'0'*64}),
            ('past_license', {'photo_rights_basis':'LICENSED','photo_rights_until':'2020-01-01'}),
            ('missing_license_end', {'photo_rights_basis':'LICENSED','photo_rights_until':''}),
            ('remote_file', {'photo_file':'https://example.com/image.png'}),
            ('traversal', {'photo_file':'../photos/photo.png'}),
            ('wrong_summary', {'summary_rights_basis':'UNREVIEWED'}),
            ('summary_xss', {'summary_ko':'<img onerror=alert(1)> 없는 기사 소개글입니다.'}),
            ('summary_too_short', {'summary_ko':'짧음'}),
            ('missing_summary_review', {'summary_review_ref':''}),
            ('bad_image_content', {'photo_file':'fake_image_000.png','photo_sha256':hashlib.sha256(b'Z'*100).hexdigest()}),
        ]
        (photos/'fake_image_000.png').write_bytes(b'Z'*100)
        fake_png = b'\x89PNG\r\n\x1a\n' + b'\x00'*90
        (photos/'signature_only_000.png').write_bytes(fake_png)
        failures.append(('signature_only_png',{'photo_file':'signature_only_000.png','photo_sha256':hashlib.sha256(fake_png).hexdigest()}))
        bogus_webp = b'RIFF' + (99).to_bytes(4,'little') + b'WEBP' + b'VP8 ' + b'\x00'*100
        (photos/'invalid_riff_000.webp').write_bytes(bogus_webp)
        failures.append(('bogus_webp_length',{'photo_file':'invalid_riff_000.webp','photo_sha256':hashlib.sha256(bogus_webp).hexdigest()}))
        broken_jpg = b'\xff\xd8\xff' + b'\x00'*100
        (photos/'truncated_jpeg_000.jpg').write_bytes(broken_jpg)
        failures.append(('truncated_jpeg',{'photo_file':'truncated_jpeg_000.jpg','photo_sha256':hashlib.sha256(broken_jpg).hexdigest()}))
        for label,override in failures:
            modified=[dict(x) for x in data]
            modified[0].update(override)
            msg=run_case(modified,articles,root,False,label)
            assert 'HOLD' in msg,label
        print(f'PASS: {len(failures)}/{len(failures)} malformed/unauthorized/corrupt image input cases rejected without output')
        # The builder must apply the *same rights gate* as the actual published API,
        # not merely trust version:2 and empty private row arrays.
        snapshot_failures=[
            ('private_source_open', lambda d: d['states']['REF_DAILYVET'].update(publicationStatus='APPROVED')),
            ('private_count_leak', lambda d: d['states']['REF_HAPPYPET'].update(actualCount=1)),
            ('candidate_exposed', lambda d: d['candidates'].update(visibleInRelease=True)),
            ('media_image_leak', lambda d: d['groups']['FEED_DAILYGAEWON'][0].update(image={'url':'https://example.test'})),
            ('media_excerpt_leak', lambda d: d['groups']['FEED_DAILYGAEWON'][0].update(excerpt='article body text')),
            ('media_state_approved', lambda d: d['groups']['FEED_DAILYGAEWON'][0].update(imageState='APPROVED')),
            ('unsafe_summary_field', lambda d: d['groups']['FEED_DAILYGAEWON'][0].update(summary='private content')),
            ('duplicate_article_url', lambda d: d['groups']['FEED_DAILYGAEWON'][1].update(url=d['groups']['FEED_DAILYGAEWON'][0]['url'])),
            ('missing_rights_states', lambda d: d.pop('states')),
        ]
        for label,mutation in snapshot_failures:
            msg=run_case([dict(data[0])],articles,root,False,label,snapshot_override=mutation)
            assert 'HOLD' in msg,label
        print('PASS: 9/9 altered DEV snapshot rights/privacy gates rejected')
        # A second run to the same path must not rewrite or damage the first output.
        repeat=run_case([dict(data[0])],articles,root,True,'repeat-output')
        after=run_case([dict(data[0])],articles,root,False,'repeat-output',allow_existing_output=True)
        assert (root/'repeat-output.html').read_text(encoding='utf-8')==repeat
        print('PASS: output file immutable on repeat attempt')
        # Two concurrent writers must never both succeed or replace one another.
        concurrent=root/'parallel-output.html'
        params=[sys.executable,str(SCRIPT),'--csv',str(root/'repeat-output.csv'),
                '--snapshot',str(root/'snapshot.json'),'--media-dir',str(photos),
                '--template',str(root/'template.html'),'--output',str(concurrent)]
        one=subprocess.Popen(params,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        two=subprocess.Popen(params,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        o1,e1=one.communicate(timeout=25);o2,e2=two.communicate(timeout=25)
        assert sorted([one.returncode,two.returncode])==[0,2],(o1,e1,o2,e2)
        assert concurrent.exists() and concurrent.stat().st_size>100
        assert 'output already exists' in e1+e2 or 'File exists' in e1+e2
        print('PASS: concurrent save, exactly one writer succeeds and one safely fails')
        empty=run_case([],articles,root,True,'empty')
        assert 'Object.freeze({})' in empty
        print('PASS: no approved assets -> empty manifest, no article photo presented')
        own=run_case([dict(data[0],summary_ko='',summary_rights_basis='',summary_review_ref='')],articles,root,True,'photo-only')
        assert 'photoFile' in own and 'summaryRights' not in own
        summary_only=run_case([dict(data[0],photo_file='',photo_sha256='',photo_rights_basis='',photo_approval_ref='',photo_credit='',photo_rights_until='')],articles,root,True,'summary-only')
        assert 'summaryRights' in summary_only and 'photoFile' not in summary_only
        print('PASS: standalone approved photos and summaries can be registered independently')
    print('R5.7 batch build contract: PASS; output review-only; no real photos or legal clearance asserted')

if __name__=='__main__':main()
