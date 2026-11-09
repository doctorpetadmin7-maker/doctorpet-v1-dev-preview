'use strict';
// R7.6 only NEW defect delta: no unsourced category "summary"; exact 18660 title.
// No network, DB, media, Site032, login, browser or prior regression retests.
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const assert=require('node:assert/strict');
const html=fs.readFileSync(path.resolve(__dirname,'../index.html'),'utf8');
const js=html.match(/<script>([\s\S]*?)<\/script>/)?.[1];
assert(js,'Inline script missing');
new vm.Script(js,{filename:'news-main-preview-inline.js'});

const from=js.indexOf('function summaryFor(){');
const to=js.indexOf('\nfunction statusInfo(s){',from);
assert(from>=0&&to>from,'R7.6 safety functions missing or drifted');
const funcs=js.slice(from,to);
const {summaryFor,visibleTitle}=vm.runInNewContext(
 funcs+'\n({summaryFor,visibleTitle})',{}, {timeout:1000}
);
const notice=summaryFor();
assert.equal(notice,'기사 소개글은 제공되지 않았습니다. 정확한 내용은 언론사 원문에서 확인하세요.');
assert(!/관련 최신 소식입니다|관련 최신 기사/.test(notice));
assert.equal(summaryFor({sourceId:'REF_DAILYVET',title:'기사'}),notice);
assert.equal((html.match(/summaryFor\(r\)/g)||[]).length,1,'Render must show one truthful provenance notice');
assert(!html.includes('진료 현장에서 참고할 핵심 내용은 원문에서 확인하세요.'));

const broken={
  sourceId:'FEED_DAILYGAEWON',
  url:'https://www.dailygaewon.com/news/articleView.html?idxno=18660',
  title:'대수회 28대 집행부 ‘동물보��·복지위원회’ 첫 회의'
};
const repaired=visibleTitle(broken);
assert.equal(repaired,'대수회 28대 집행부 ‘동물보호·복지위원회’ 첫 회의');
assert.equal(broken.title,'대수회 28대 집행부 ‘동물보��·복지위원회’ 첫 회의');
for(const delta of [
  {sourceId:'REF_DAILYVET'}, {url:broken.url+'&other=1'},
  {title:repaired},{url:'https://www.dailygaewon.com/news/articleView.html?idxno=18661'},
  {title:'다른 인코딩 손상'},
]) {
  const item={...broken,...delta};
  assert.equal(visibleTitle(item),item.title,'Only exactly matching damaged article may be repaired');
}
assert.equal(visibleTitle({title:'정상 기사 제목'}),'정상 기사 제목');
assert.equal(visibleTitle({}),'제목 확인 중');
assert(html.includes('esc(visibleTitle(r))'),'Escaped rendering of repaired title must be preserved');
assert(html.includes('noopener noreferrer'),'No change to original article tab protection');
assert(html.includes('const size=100'),'Existing 100/page pagination preserved');
assert(html.includes("const API='https://mabvxdcpmfdzrqlgkxqn.supabase.co/functions/v1/doctorpet-vet-news-release-data'"),
       'Approved read-only API unchanged');
assert(html.includes("FEED_DAILYGAEWON")&&html.includes("REF_DAILYVET")&&html.includes("REF_HAPPYPET"));
assert(html.includes("onerror="),'Existing photo fallback must remain intact');
console.log('PASS R7.6 one-file preview delta: title exact 18660 repair 1; unsafe cases 5; metadata-only notice 1; JS syntax; links, data source, photo fallback, 100/page preserved; 0 server writes');
