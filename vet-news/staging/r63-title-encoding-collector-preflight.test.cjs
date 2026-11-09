'use strict';
// Synthetic-only tests. Never call the producer, scheduler, database or publisher.
const test=require('node:test');
const assert=require('node:assert/strict');
const {titleDefect,decodeStrictUtf8,preflight,SOURCE}=require('./r63-title-encoding-collector-preflight.cjs');
const base='https://www.dailygaewon.com/news/articleView.html?idxno=';
function fixture(){
  return Array.from({length:50},(_,i)=>({url:base+(19000+i),title:'정상 메타데이터 제목 '+String(i).padStart(2,'0')}));
}
test('known replacement character is rejected, normal Korean accepted',()=>{
  assert.equal(titleDefect('동물보\uFFFD\uFFFD·복지위원회'),'REPLACEMENT_CHARACTER');
  assert.equal(titleDefect('동물보호·복지위원회'),null);
  assert.equal(titleDefect('가\u0000나'),'CONTROL_CHARACTER');
  assert.equal(titleDefect(' '),'EMPTY_OR_NONSTRING_TITLE');
  assert.equal(titleDefect('가'.repeat(501)),'TITLE_TOO_LONG');
});
test('strict bytes decoder rejects loss-prone UTF-8 rather than silently replacing',()=>{
  assert.equal(decodeStrictUtf8(new TextEncoder().encode('동물보호')),'동물보호');
  assert.throws(()=>decodeStrictUtf8(Uint8Array.of(0xED,0xA0,0x80)),TypeError);
  assert.throws(()=>decodeStrictUtf8('not bytes'),TypeError);
});
test('304: current damaged historic cache produces one warning and zero new articles',()=>{
  const old=fixture();old[10]={...old[10],title:'기존 손상 \uFFFD 기사'};
  const r=preflight({sourceId:SOURCE,httpStatus:304,resultItems:[],normalizedItems:old});
  assert.equal(r.mode,'CACHE_MONITOR_ONLY');
  assert.equal(r.newRows,0);assert.equal(r.heldNew,0);
  assert.equal(r.cacheWarnings.length,1);
  assert.equal(r.safeNewItems.length,0);
});
test('fresh 200: hold one damaged title only, preserve clean other 49',()=>{
  const now=fixture();now[10]={...now[10],title:'새 손상 \uFFFD 기사'};
  const result=preflight({sourceId:SOURCE,httpStatus:200,resultItems:now,normalizedItems:now.map(x=>({...x}))});
  assert.equal(result.mode,'HOLD_DAMAGED_NEW_ITEMS');
  assert.equal(result.heldNew,1);
  assert.equal(result.safeNewItems.length,49);
  assert.equal(result.heldItems[0].url,now[10].url);
  assert.equal(now[10].title,'새 손상 \uFFFD 기사','must not mutate original');
});
test('fresh 200: 50 clean rows do not require media rights or publish anything',()=>{
  const fresh=fixture();
  const r=preflight({sourceId:SOURCE,httpStatus:200,resultItems:fresh,normalizedItems:fresh});
  assert.equal(r.mode,'NEW_ITEMS_READY_FOR_REVIEW');
  assert.equal(r.safeNewItems.length,50);
  assert.equal(r.heldNew,0);
});
test('cached title corruption blocks only that title even when result title looks clean',()=>{
  const result=fixture(),cache=fixture();
  cache[3].title='깨짐 \uFFFD';
  const r=preflight({sourceId:SOURCE,httpStatus:200,resultItems:result,normalizedItems:cache});
  assert.equal(r.heldNew,1);assert.equal(r.safeNewItems.length,49);
  assert.equal(r.heldItems[0].reason,'REPLACEMENT_CHARACTER');
});
test('other source, malformed URL, duplicate URL, missing cached entry fail closed',()=>{
  const feed=fixture();
  assert.throws(()=>preflight({sourceId:'REF_DAILYVET',httpStatus:200,resultItems:feed,normalizedItems:feed}),/SOURCE_NOT_APPROVED/);
  assert.throws(()=>preflight({sourceId:SOURCE,httpStatus:201,resultItems:feed,normalizedItems:feed}),/UNSUPPORTED/);
  const bad=fixture();bad[0]={...bad[0],url:'http://www.dailygaewon.com/news/articleView.html?idxno=1'};
  assert.throws(()=>preflight({sourceId:SOURCE,httpStatus:200,resultItems:bad,normalizedItems:bad}),/INVALID/);
  const dup=fixture();dup[1]={...dup[1],url:dup[0].url};
  assert.throws(()=>preflight({sourceId:SOURCE,httpStatus:200,resultItems:dup,normalizedItems:dup}),/DUPLICATE/);
  assert.throws(()=>preflight({sourceId:SOURCE,httpStatus:200,resultItems:feed,normalizedItems:feed.slice(0,-1)}),/MISSING_IN_NORMALIZED|ITEM_COUNT_MISMATCH/);
});
test('same-title distinct URL articles are not merged',()=>{
  const items=fixture();
  items[0].title='합법적으로 같은 제목';
  items[1].title='합법적으로 같은 제목';
  const result=preflight({sourceId:SOURCE,httpStatus:200,resultItems:items,normalizedItems:items});
  assert.equal(result.safeNewItems.length,50);
  assert.equal(new Set(result.safeNewItems.map(r=>r.url)).size,50);
});
