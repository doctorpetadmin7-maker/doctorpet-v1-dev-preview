'use strict';
// R6.2 release-candidate only. LIVE DEV HTTP read-only; no publisher requests or writes.
// Validates a single exact article display correction and keeps distinct same-title URLs.
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const html=fs.readFileSync(path.join(__dirname,'r62-title-encoding-review-only.html'),'utf8');
const script=html.match(/<script>([\s\S]*?)<\/script>/)?.[1];
assert(script,'missing R6.2 inline script');
new vm.Script(script,{filename:'r62-review-only.js'});
const start=script.indexOf("const API='https://mabvxdcpmfdzrqlgkxqn.supabase.co/functions/v1/doctorpet-vet-news-release-data';");
const end=script.indexOf('function visibleRows(){',start);
assert(start>=0 && end>start && script.slice(start,end).includes('function correctVerifiedTitle18660'),'source drift');
const {parseLegacyPayload,correctVerifiedTitle18660}=vm.runInNewContext(script.slice(start,end)+'\n({parseLegacyPayload,correctVerifiedTitle18660})',{URL,Date,Intl},{timeout:2500});
const affected='https://www.dailygaewon.com/news/articleView.html?idxno=18660';
const id='collect:0ac6a8c5c0c2743e87cf3f471a74a1d3474d2de4';
const oldTitle='대수회 28대 집행부 ‘동물보��·복지위원회’ 첫 회의';
const newTitle='대수회 28대 집행부 ‘동물보호·복지위원회’ 첫 회의';
const row={id,sourceId:'FEED_DAILYGAEWON',url:affected,title:oldTitle,publishedAt:'2026-11-06T02:44:48Z'};
const fixed=correctVerifiedTitle18660(row);
assert.equal(fixed.title,newTitle);
assert.equal(row.title,oldTitle,'source record mutated');
assert.equal(fixed.url,row.url);
const deny=[
 {...row,id:'other'},
 {...row,url:affected+'&copy=1'},
 {...row,sourceId:'REF_DAILYVET'},
 {...row,title:'not the exact damaged title'},
 {...row,title:newTitle}
];
for(const test of deny)assert.equal(correctVerifiedTitle18660(test),test,'Unexpected correction outside exact match');
const other={...row,id:'another-article',url:'https://www.dailygaewon.com/news/articleView.html?idxno=18617'};
assert.equal(correctVerifiedTitle18660(other),other);
(async()=>{
 const API='https://mabvxdcpmfdzrqlgkxqn.supabase.co/functions/v1/doctorpet-vet-news-release-data';
 const allowed='https://doctorpetadmin7-maker.github.io';
 const res=await fetch(API,{method:'GET',headers:{Origin:allowed},signal:AbortSignal.timeout(18000)});
 assert.equal(res.status,200,'DEV API GET not 200');
 assert.equal(res.headers.get('access-control-allow-origin'),allowed,'CORS contract drift');
 const p=await res.json();
 const parsed=parseLegacyPayload(p);
 assert.equal(parsed.rightsGate,'APPROVED_METADATA_ONLY');
 const rows=parsed.rows;
 assert.equal(rows.length,64,'DEV approved article count drift; investigate before release');
 const repaired=rows.map(correctVerifiedTitle18660);
 const exact=rows.find(r=>r.url===affected);
 assert(exact,'known source article 18660 not found');
 assert(exact.title===oldTitle || exact.title===newTitle,'unexpected source title; no blanket replacement');
 assert.equal(repaired.find(r=>r.url===affected).title,newTitle);
 const changed=rows.filter((r,i)=>r.title!==repaired[i].title);
 assert.equal(changed.length,exact.title===oldTitle?1:0);
 const unchanged=rows.filter((r,i)=>r.title===repaired[i].title);
 assert.equal(unchanged.length,64-changed.length);
 assert.deepEqual(repaired.map(r=>r.url),rows.map(r=>r.url),'URLs changed');
 assert.deepEqual(repaired.map(r=>r.id),rows.map(r=>r.id),'IDs changed');
 const duplicateRows=repaired.filter(r=>r.title==='힐스코리아, Jody Lulich 교수 초청 ‘요로 심포지엄’ 성공적으로 마쳐');
 assert.equal(duplicateRows.length,2,'Two distinct source articles were incorrectly deduplicated');
 assert.equal(new Set(duplicateRows.map(r=>r.url)).size,2,'Source URLs are not distinct');
 assert(repaired.every(r=>r.sourceId==='FEED_DAILYGAEWON'),'restricted source visible');
 console.log('PASS R6.2 LIVE DEV 64 rows, exact 18660 display title corrected='+changed.length+
   ', 63 other titles preserved, 2 separate same-title articles retained, negative guard 6/6, DB unchanged');
})().catch(err=>{console.error(err.stack||err);process.exitCode=1;});
