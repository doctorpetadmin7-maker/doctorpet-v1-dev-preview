'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const html=fs.readFileSync(path.join(__dirname,'r54-licensed-media-ready-ui.html'),'utf8');
const m=html.match(/<script>([\s\S]*?)<\/script>/);
assert(m,'inline script missing');
new vm.Script(m[1],{filename:'r54-page.js'});
const j=m[1];
const from=j.indexOf('const LICENSED_ARTICLE_MEDIA=');
const to=j.indexOf('function card(r,i)',from);
const cardEnd=j.indexOf('function renderList()',to);
assert(from>=0&&to>from&&cardEnd>to,'no media helper/card boundaries');
const helper=j.slice(from,to), card=j.slice(to,cardEnd);
assert(helper.includes('Object.freeze({})'),'Live media manifest must be empty by default');
const root='https://doctorpetadmin7-maker.github.io/doctorpet-v1-dev-preview/vet-news/';
const row=i=>({id:'story-'+i,sourceId:'FEED_DAILYGAEWON',url:'https://www.dailygaewon.com/news/articleView.html?idxno='+i,title:'검수 기사 '+i,publishedAt:'2026-11-06T00:00:00Z'});
const manifest=Object.fromEntries(Array.from({length:100},(_,i)=>{
 const a=row(i);
 return [a.id,{sourceId:a.sourceId,articleUrl:a.url,photoRights:'OWNED_OR_LICENSED',
   photoFile:'doctorpet-test-media-'+String(i).padStart(3,'0')+'.webp',
   photoAttribution:'© DoctorPet original test asset',
   summaryRights:'EDITORIAL_VERIFIED',
   summary:'닥터펫 자체 작성·검증 소개글입니다. 이 텍스트는 실제 기사 내용 요약이 아닌 기능 시험용 문구입니다.'}];
}));
const sandbox={
 URL,location:{href:root},state:{testFixture:true},
 classify:()=> '수의계소식',
 esc:v=>String(v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])),
 srcName:()=> '데일리개원',
 dateFmt:()=> '2026. 11. 06.'
};
function adapter(map){
 const source=helper.replace('Object.freeze({})','Object.freeze('+JSON.stringify(map)+')');
 assert.notEqual(source,helper,'test manifest injection failed');
 return vm.runInNewContext(source+'\n'+card+'\n({mediaFor,card})',sandbox,{timeout:2500});
}
const full=adapter(manifest);
let photos=0,summaries=0;
for(let i=0;i<100;i++){
 const a=row(i),m=full.mediaFor(a),markup=full.card(a,i);
 assert(m.imageUrl?.startsWith(root+'licensed-media/'),i);
 assert(m.summary?.includes('검증 소개글'),i);
 assert(markup.includes('<img '),i);
 assert(markup.includes('class="excerpt "'),i);
 assert(markup.includes('data-photo="pending"'),i);
 assert(markup.includes('referrerpolicy="no-referrer"'),i);
 photos++;summaries++;
}
assert.equal(photos,100);assert.equal(summaries,100);
const absent=vm.runInNewContext(helper+'\n'+card+'\n({mediaFor,card})',sandbox,{timeout:2500});
assert.equal(absent.mediaFor(row(1)).imageUrl,null);
assert.equal(absent.mediaFor(row(1)).summary,null);
assert(!absent.card(row(1),0).includes('<img '));
assert(absent.card(row(1),0).includes('사진 준비 중'));
const base=row(1);
const good=manifest[base.id];
const rejectImage=[
 {...good,photoRights:'UNCONFIRMED'},
 {...good,photoFile:'https://example.com/picture.jpg'},
 {...good,photoFile:'../../media/photo.jpg'},
 {...good,photoFile:'x.svg'},
 {...good,photoAttribution:''},
 {...good,articleUrl:'https://www.dailygaewon.com/news/articleView.html?idxno=999'},
 {...good,sourceId:'REF_DAILYVET'}
];
for(const item of rejectImage){
 const target=adapter({[base.id]:item}).mediaFor(base);
 assert.equal(target.imageUrl,null,JSON.stringify(item));
}
const rejectSummary=[
 {...good,summaryRights:'UNREVIEWED'},
 {...good,summary:'<img onerror=alert(1)> article fake summary'},
 {...good,summary:'x'},
 {...good,summary:'x'.repeat(281)},
 {...good,articleUrl:'https://www.dailygaewon.com/news/articleView.html?idxno=999'}
];
for(const item of rejectSummary)assert.equal(adapter({[base.id]:item}).mediaFor(base).summary,null);
const cross=adapter({'story-1':manifest['story-2']}).mediaFor(base);
assert.equal(cross.imageUrl,null);assert.equal(cross.summary,null);
assert(html.includes('const API='),'DEV read-only API unchanged');
console.log('PASS R5.4 HTML syntax, 100/100 licensed media & two-line summaries in SIMULATION; 13 rejection cases; live licensed assets 0');
