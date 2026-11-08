'use strict';
// Read-only contract test: the exact R4.5 HTML parser consumes live DEV JSON.
// No article collection, claim, credentials, DB writes, or publisher requests.
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const htmlPath=process.argv.find(x=>x.endsWith('.html'))||path.join(__dirname,'r4_5-rights-safe-ui.html');
const source=fs.readFileSync(htmlPath,'utf8');
const start=source.indexOf("const API='https://mabvxdcpmfdzrqlgkxqn.supabase.co/functions/v1/doctorpet-vet-news-release-data';");
const end=source.indexOf('function visibleRows(){',start);
assert(start>=0&&end>start,'The R4.5 parser or DEV API reference changed');
const parse=vm.runInNewContext(source.slice(start,end)+'\nparseLegacyPayload',{URL,Date,Intl},{timeout:2000});
const API='https://mabvxdcpmfdzrqlgkxqn.supabase.co/functions/v1/doctorpet-vet-news-release-data';
const ORIGIN='https://doctorpetadmin7-maker.github.io';
function fakePayload(){return {version:2,pageSize:100,states:{FEED_DAILYGAEWON:{actualCount:1},REF_DAILYVET:{actualCount:0,publicationStatus:'WITHHELD_RIGHTS_PENDING'},REF_HAPPYPET:{actualCount:0,publicationStatus:'WITHHELD_RIGHTS_PENDING'}},groups:{FEED_DAILYGAEWON:[{id:'safe-1',title:'수의학 교육',url:'https://www.dailygaewon.com/news/articleView.html?idxno=1',publishedAt:'2026-11-06T00:00:00Z',sourceId:'FEED_DAILYGAEWON',actualStored:true,image:null,excerpt:null,imageState:'WITHHELD_RIGHTS_PENDING',excerptState:'WITHHELD_RIGHTS_PENDING'}],REF_DAILYVET:[],REF_HAPPYPET:[]},candidates:{visibleInRelease:false}}}
function reject(obj,label){assert.throws(()=>parse(obj),undefined,label);}
function negativeTests(p){
 const a=structuredClone(p);a.groups.REF_DAILYVET.push({title:'PRIVATE'});reject(a,'private trial leaked');
 const b=structuredClone(p);b.groups.REF_HAPPYPET.push({title:'PRIVATE'});reject(b,'happypet leaked');
 const c=structuredClone(p);c.groups.FEED_DAILYGAEWON[0].image={url:'https://example.com/p.jpg'};reject(c,'photo leaked');
 const d=structuredClone(p);d.groups.FEED_DAILYGAEWON[0].excerpt='unapproved text';reject(d,'excerpt leaked');
 const e=structuredClone(p);e.groups.FEED_DAILYGAEWON[0].url='https://other.example/news/1';reject(e,'external link');
 const f=structuredClone(p);f.states.REF_DAILYVET.publicationStatus='APPROVED';reject(f,'rights gate bypass');
 const g=structuredClone(p);g.groups.FEED_DAILYGAEWON[0].publishedAt=42;reject(g,'invalid date type');
 const h=structuredClone(p);h.groups.FEED_DAILYGAEWON[0].summary='made-up summary';reject(h,'unapproved summary');
}
(async()=>{
 const fixture=process.argv.includes('--fixture');let response;
 if(fixture){response=fakePayload();}
 else{
  const res=await fetch(API,{headers:{Origin:ORIGIN},signal:AbortSignal.timeout(15000),cache:'no-store'});
  assert.equal(res.status,200,'live DEV HTTP status');
  assert.equal(res.headers.get('access-control-allow-origin'),ORIGIN,'allowed CORS');
  response=await res.json();
 }
 const out=parse(response);assert(out.rows.length>0,'no approved-metadata rows');
 assert.equal(out.rows.length,response.groups.FEED_DAILYGAEWON.length,'client/server row count mismatch');
 assert.equal(out.rightsGate,'APPROVED_METADATA_ONLY');
 negativeTests(response);
 console.log('PASS R4.7 UI parser with '+(fixture?'synthetic fixture':'LIVE DEV HTTP')+': rows='+out.rows.length+', denied private/photos/excerpts, negative cases=8');
})().catch(e=>{console.error(e.stack||e);process.exitCode=1});
