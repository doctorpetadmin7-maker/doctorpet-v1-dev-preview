'use strict';
const assert=require('node:assert/strict');
const {create}=require('../shared/speech-controller.js');

function fixture(availability) {
  let time=1700000000000, token=0;
  const timers=new Map(), instances=[], final=[], drafts=[], states=[], errors=[], capabilities=[];
  const listeners={};
  const document={hidden:false,addEventListener(k,fn){listeners[k]=fn;},removeEventListener(k){delete listeners[k];}};
  class Recognition {
    constructor(){this.processLocally=false;this.running=false;this.stops=0;this.aborts=0;instances.push(this);}
    start(){assert.equal(instances.filter(r=>r.running).length,0,'Only one engine may run');this.running=true;this.onstart?.();}
    stop(){this.stops++;}
    abort(){this.aborts++;this.running=false;this.onend?.();}
    end(){this.running=false;this.onend?.();}
    error(code){this.onerror?.({error:code});}
    speech(){this.onspeechstart?.();}
    result(values,resultIndex=0){this.onresult?.({resultIndex,results:values.map(([text,done])=>Object.assign([{transcript:text}],{isFinal:done}))});}
  }
  if(availability!==undefined) Recognition.available=()=>typeof availability==='function'?availability():Promise.resolve(availability);
  Recognition.install=()=>{throw new Error('Must not download a model');};
  const environment={SpeechRecognition:Recognition,isSecureContext:true,document,Date:{now:()=>time},
    setTimeout(fn,delay){const id=++token;timers.set(id,{at:time+delay,fn});return id;},clearTimeout(id){timers.delete(id);},
    addEventListener(k,fn){listeners[k]=fn;},removeEventListener(k){delete listeners[k];}};
  const c=create({environment,onFinal:v=>final.push(v),onDraft:v=>drafts.push(v),onState:v=>states.push(v),onError:v=>errors.push(v),onCapability:v=>capabilities.push(v)});
  function tick(ms){const until=time+ms;let loops=0;for(;;){const next=[...timers].filter(([,t])=>t.at<=until).sort((a,b)=>a[1].at-b[1].at)[0];if(!next)break;assert.ok(++loops<100,'No timer loop');time=next[1].at;timers.delete(next[0]);next[1].fn();}time=until;}
  return {c,instances,final,drafts,states,errors,capabilities,environment,listeners,tick,latest:()=>instances.at(-1)};
}

(async()=>{
  let checks=0;
  async function test(name,fn){await fn();checks++;console.log('PASS',name);}

  await test('No mic before click; 15 seconds of silence never invokes stop',()=>{
    const f=fixture();f.tick(15000);assert.equal(f.instances.length,0);
    assert.equal(f.c.start(),true);assert.equal(f.c.start(),false);
    f.tick(15000);assert.equal(f.instances.length,1);assert.equal(f.latest().stops,0);assert.equal(f.c.getState().phase,'listening');f.c.destroy();
  });
  await test('Interim text replaces; same final slot replay commits once',()=>{
    const f=fixture();f.c.start();const r=f.latest();r.speech();
    r.result([['이틀',false]]);r.result([['이틀 뒤 병원',false]]);
    assert.equal(f.c.getSnapshot().text,'이틀 뒤 병원');assert.equal(f.final.length,0);
    r.result([['이틀 뒤 병원',true]]);for(let n=0;n<10;n++)r.result([['이틀 뒤 병원',true]]);
    assert.equal(f.final.length,1);assert.equal(f.c.getSnapshot().text,'이틀 뒤 병원');f.c.destroy();
  });
  await test('Ten duplicated result slots do not duplicate one phrase',()=>{
    const f=fixture();f.c.start();f.latest().speech();
    f.latest().result(Array.from({length:10},()=>['내일 병원',true]));
    assert.equal(f.final.length,1);assert.equal(f.c.getSnapshot().text,'내일 병원');f.c.destroy();
  });
  await test('Cumulative engine result plus interim/final becomes only the new suffix',()=>{
    const f=fixture();f.c.start();const r=f.latest();r.speech();r.result([['내일 병원',true]]);
    r.result([['내일 병원',true],['내일 병원 모레 회의',false]],1);
    assert.equal(f.c.getSnapshot().text,'내일 병원 모레 회의');
    r.result([['내일 병원',true],['내일 병원 모레 회의',true]],1);
    assert.deepEqual(f.final.map(x=>x.text),['내일 병원','모레 회의']);assert.equal(f.c.getSnapshot().text,'내일 병원 모레 회의');f.c.destroy();
  });
  await test('Same date with a different event and an intentional repeated utterance survive',()=>{
    const f=fixture();f.c.start();const r=f.latest();r.speech();r.result([['내일 병원',true]]);
    r.result([['내일 병원',true],['내일 회의',true]],1);
    r.speech();r.result([['내일 병원',true],['내일 회의',true],['내일 회의',true]],2);
    assert.deepEqual(f.final.map(x=>x.text),['내일 병원','내일 회의','내일 회의']);f.c.destroy();
  });
  await test('Engine end reconnects exactly once; boundary replay suppressed, new speech accepted',()=>{
    const f=fixture();f.c.start();const first=f.latest();first.speech();first.result([['모레 검진',true]]);first.end();
    assert.equal(f.c.getState().phase,'reconnecting');f.tick(219);assert.equal(f.instances.length,1);f.tick(1);assert.equal(f.instances.length,2);
    const second=f.latest();second.result([['모레 검진',true]]);assert.equal(f.final.length,1);
    second.speech();second.result([['모레 검진',true],['모레 검진',true]],1);assert.equal(f.final.length,2);f.c.destroy();
  });
  await test('Finalizing a reconnect replaces its unconfirmed interim tail',()=>{
    const f=fixture();f.c.start();f.latest().result([['이틀 뒤 병원',false]]);f.latest().end();
    assert.equal(f.c.getSnapshot().segments[0].unconfirmed,true);f.tick(650);
    f.latest().speech();f.latest().result([['이틀 뒤 병원에 가기',true]]);
    assert.equal(f.c.getSnapshot().text,'이틀 뒤 병원에 가기');assert.equal(f.final.length,1);f.c.destroy();
  });
  await test('Normal stop flushes final and settles once; no restart',async()=>{
    const f=fixture();f.c.start();const r=f.latest();r.result([['내일 검진',false]]);
    const p=f.c.stop(),p2=f.c.stop();assert.equal(r.stops,1);
    r.result([['내일 검진',true]]);r.end();await p;await p2;f.tick(20000);
    assert.equal(f.final.length,1);assert.equal(f.instances.length,1);assert.equal(f.c.getState().phase,'idle');f.c.destroy();
  });
  await test('Idle stop never replays an empty or stale draft over manual edits',async()=>{
    const f=fixture();let count=f.drafts.length;await f.c.stop();assert.equal(f.drafts.length,count);
    f.c.start();f.latest().result([['이전 음성 내용',true]]);const p=f.c.stop();f.latest().end();await p;
    // The consumer can now freely edit its own text; another idle stop is silent.
    count=f.drafts.length;await f.c.stop();await f.c.stop();assert.equal(f.drafts.length,count);f.c.destroy();
  });
  await test('Stop timeout retains unfinished text without confirming it',async()=>{
    const f=fixture();f.c.start();f.latest().result([['다음 주 화요일',false]]);const p=f.c.stop();
    f.tick(1800);await p;assert.equal(f.final.length,0);assert.equal(f.c.getSnapshot().text,'다음 주 화요일');
    assert.equal(f.c.getSnapshot().segments[0].unconfirmed,true);assert.equal(f.latest().aborts,1);f.c.destroy();
  });
  await test('Discard invalidates late result/end callbacks before UI is cleared',async()=>{
    const f=fixture();f.c.start();const r=f.latest(),lateResult=r.onresult,lateEnd=r.onend;
    r.result([['남길 필요 없는 문장',false]]);await f.c.stop({discard:true});
    const callbackCount=f.drafts.length;lateResult({resultIndex:0,results:[Object.assign([{transcript:'늦은 문장'}],{isFinal:true})]});lateEnd();f.tick(10000);
    assert.equal(f.c.getSnapshot().text,'');assert.equal(f.final.length,0);assert.equal(f.drafts.length,callbackCount);assert.equal(f.instances.length,1);f.c.destroy();
  });
  await test('Permission rejection never retries',()=>{
    const f=fixture();f.c.start();f.latest().error('not-allowed');f.tick(30000);
    assert.equal(f.instances.length,1);assert.equal(f.c.getState().phase,'error');assert.equal(f.c.getState().desired,false);f.c.destroy();
  });
  await test('Repeated no-speech ends use bounded backoff, then pause',()=>{
    const f=fixture();f.c.start();
    for(const delay of [650,1600,3600]){const r=f.latest();r.error('no-speech');r.end();assert.equal(f.c.getState().retryInMs,delay);f.tick(delay);}
    f.latest().error('no-speech');f.latest().end();f.tick(100000);
    assert.equal(f.instances.length,4);assert.equal(f.c.getState().phase,'paused');assert.equal(f.c.getState().reason,'recognizer-keeps-ending');f.c.destroy();
  });
  await test('Four ordinary long silence endings keep continue-listening enabled',()=>{
    const f=fixture();f.c.start();
    for(let n=0;n<4;n++){
      f.tick(5100);const r=f.latest();r.error('no-speech');r.end();
      assert.equal(f.c.getState().desired,true);assert.equal(f.c.getState().phase,'reconnecting');
      assert.equal(f.c.getState().retryInMs,650);f.tick(650);
    }
    assert.equal(f.instances.length,5);assert.equal(f.c.getState().desired,true);assert.equal(f.c.getState().phase,'listening');f.c.destroy();
  });
  await test('An error without end cannot spawn a parallel recognizer',()=>{
    const f=fixture();f.c.start();f.latest().error('network');f.tick(1800);
    assert.equal(f.instances.length,1);assert.equal(f.c.getState().phase,'paused');assert.equal(f.latest().aborts,1);f.c.destroy();
  });
  await test('Page hiding aborts once and does not auto-start in background',()=>{
    const f=fixture();f.c.start();f.environment.document.hidden=true;f.listeners.visibilitychange();f.tick(30000);
    assert.equal(f.latest().aborts,1);assert.equal(f.c.getState().phase,'paused');assert.equal(f.instances.length,1);
    f.environment.document.hidden=false;f.listeners.visibilitychange();assert.equal(f.instances.length,1);f.c.destroy();
  });
  await test('Available ko-KR local mode sets processLocally; downloadable does not install',async()=>{
    const f=fixture('available');await f.c.checkCapability();f.c.start();assert.equal(f.latest().processLocally,true);assert.equal(f.c.getState().local,true);f.c.destroy();
    const g=fixture('downloadable');await g.c.checkCapability();g.c.start();assert.equal(g.latest().processLocally,false);assert.equal(g.c.getState().local,false);g.c.destroy();
  });
  await test('An unfinished capability check never delays start or changes an active run mode',async()=>{
    let release;const f=fixture(()=>new Promise(resolve=>{release=resolve;}));
    f.c.start();assert.equal(f.instances.length,1);assert.equal(f.latest().processLocally,false);
    release('available');await f.c.checkCapability();f.latest().speech();f.latest().result([['내일 회의',true]]);f.latest().end();f.tick(220);
    assert.equal(f.latest().processLocally,false);await f.c.stop({discard:true});f.c.start();assert.equal(f.latest().processLocally,true);f.c.destroy();
  });
  console.log('\n'+checks+' behavioral checks passed. Fake engine and virtual clock only; no physical microphone test.');
})().catch(error=>{console.error(error);process.exitCode=1;});
