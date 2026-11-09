'use strict';
/**
 * R6.3 - OFFLINE CANDIDATE ONLY: title quality preflight for one approved feed.
 * Integration point is BEFORE doctorpet_domestic_news.apply_run. This file
 * does not fetch websites, call DB, claim work, write feeds, or deploy.
 *
 * The stored 2026-11-06 normalized feed contains one U+FFFD title.
 * Treat a current HTTP 304 as CACHE_MONITOR_ONLY, never as 50 new articles;
 * for a future HTTP 200 hold affected NEW rows for review, preserving others.
 * Actual integration must maintain apply_run accepted/count/cache contracts.
 */
const SOURCE='FEED_DAILYGAEWON';
function titleDefect(title){
  if(typeof title!=='string'||!title.trim())return 'EMPTY_OR_NONSTRING_TITLE';
  if(title.includes('\uFFFD'))return 'REPLACEMENT_CHARACTER';
  if(/[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F]/u.test(title))return 'CONTROL_CHARACTER';
  if(title.length>500)return 'TITLE_TOO_LONG';
  return null;
}
function decodeStrictUtf8(raw){
  if(!(raw instanceof Uint8Array))throw new TypeError('UTF8_BYTES_REQUIRED');
  // If the publisher explicitly declares another encoding, decode by that
  // verified charset before running titleDefect; never guess silently.
  return new TextDecoder('utf-8',{fatal:true}).decode(raw);
}
function validURL(raw){
  try{
    const u=new URL(raw);
    return u.protocol==='https:'&&u.hostname==='www.dailygaewon.com'&&
       u.pathname==='/news/articleView.html'&&/^\d+$/.test(u.searchParams.get('idxno')||'')&&
       [...u.searchParams.keys()].length===1;
  }catch{return false}
}
function preflight({sourceId,httpStatus,resultItems,normalizedItems}){
  if(sourceId!==SOURCE)throw Error('SOURCE_NOT_APPROVED_FOR_THIS_PREFLIGHT');
  if(![200,304].includes(httpStatus))throw Error('UNSUPPORTED_HTTP_STATUS');
  if(!Array.isArray(resultItems)||!Array.isArray(normalizedItems))throw Error('FEED_SCHEMA_INVALID');
  const originalCache=new Map();
  const badCache=[];
  for(const item of normalizedItems){
    const id=String(item?.url||'');
    if(!validURL(id)||originalCache.has(id))throw Error('NORMALIZED_CACHE_LINK_INVALID_OR_DUPLICATE');
    originalCache.set(id,item);
    const defect=titleDefect(item?.title);
    if(defect)badCache.push({url:id,reason:defect});
  }
  if(httpStatus===304){
    // A 304 proves no new bytes were fetched. Existing cache may already
    // contain a historic damaged title: monitor and repair separately.
    return {mode:'CACHE_MONITOR_ONLY',newRows:0,heldNew:0,cacheWarnings:badCache,
      safeNewItems:[],heldItems:[]};
  }
  const kept=[],held=[];
  const seen=new Set();
  for(const item of resultItems){
    const url=String(item?.url||'');
    const cache=originalCache.get(url);
    if(!validURL(url)||seen.has(url))throw Error('RESULT_URL_INVALID_OR_DUPLICATE');
    seen.add(url);
    const defect=titleDefect(item?.title)||titleDefect(cache?.title)||
       (cache&&cache.title!==item.title?'TITLE_CACHE_DISAGREES':null)||
       (!cache?'MISSING_IN_NORMALIZED_CACHE':null);
    if(defect)held.push({url,reason:defect});
    else kept.push(item);
  }
  if(seen.size!==originalCache.size)throw Error('FEED_CACHE_ITEM_COUNT_MISMATCH');
  return {mode:held.length?'HOLD_DAMAGED_NEW_ITEMS':'NEW_ITEMS_READY_FOR_REVIEW',
    newRows:resultItems.length,heldNew:held.length,cacheWarnings:badCache,
    safeNewItems:kept,heldItems:held};
}
module.exports={SOURCE,titleDefect,decodeStrictUtf8,preflight};
