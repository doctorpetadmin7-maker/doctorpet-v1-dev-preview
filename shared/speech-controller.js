/* DoctorPet speech controller v4 — no recording or application sound playback.
 *
 * create({onState, onDraft, onFinal, onError, onCapability}) does NOT start a mic.
 * start() MUST be called by the UI's explicit click. It starts synchronously using
 * the capability known at that instant; an unfinished capability query never
 * delays/replays the click. Call checkCapability() at UI initialization.
 *
 * onState: {phase, desired, active, local, reason, retryInMs, canStart}.
 * phases: idle|starting|listening|reconnecting|stopping|paused|error|unsupported.
 * onDraft: {text, finalText, interimText, segments, local}. This is a REPLACEMENT
 * snapshot of this logical listening run, including reconnects. Each segment is
 * {id,text,isFinal,unconfirmed,sessionId,index}. Never append onDraft.text.
 * onFinal: {id,text,sessionId,index,local}, once per accepted result slot. An app
 * must also use id as its upsert key. Unfinished interim text is never finalized.
 * start() begins a new run; the caller owns any previous run's saved text.
 * stop() returns a Promise, flushes final results, then resolves in idle state.
 * stop({discard:true}) invalidates callbacks BEFORE abort, clears the run without
 * emitting text, and resolves immediately. Use this before clearing/replacing UI.
 * Page hiding aborts the microphone and leaves unconfirmed text for review.
 *
 * Recognition results are indexed snapshots, per the Web Speech API specification:
 * https://webaudio.github.io/web-speech-api/#speechreco-event
 * Limited replay guards only suppress immediate duplicates without new-utterance
 * evidence; identical text spoken in a new speech turn is intentionally retained.
 * Runtime local availability is checked without downloading a model. Browser
 * mode can use the browser provider's service; it is NOT labeled on-device.
 */
(function (root) {
  'use strict';
  const FATAL = new Set(['not-allowed','service-not-allowed','audio-capture','language-not-supported','bad-grammar']);
  const clean = text => String(text || '').replace(/\s+/g, ' ').trim();
  const key = text => clean(text).replace(/[.,!?。！？]+$/u, '').toLocaleLowerCase();
  function create(options = {}) {
    const env = options.environment || root;
    const doc = env.document;
    const Recognition = env.SpeechRecognition || env.webkitSpeechRecognition;
    const now = () => (env.Date || Date).now();
    const later = (fn, delay) => env.setTimeout(fn, delay);
    const cancel = handle => { if (handle !== null) env.clearTimeout(handle); };
    const emit = (name, value) => { if (typeof options[name] === 'function') options[name](value); };
    let destroyed = false, desired = false, phase = 'idle', reason = '', retryInMs = 0;
    const instanceId = now().toString(36)+'-'+Math.random().toString(36).slice(2,8);
    let active = null, run = 0, sequence = 0, sessionSequence = 0, runLocal = false;
    let segments = [], lastAccepted = null, startedAt = [], emptyEnds = 0;
    let restartTimer = null, stopTimer = null, errorTimer = null;
    let stopWaiters = [], local = false;
    let capability = {supported: !!Recognition, local: false, status: Recognition ? 'checking' : 'unsupported'};
    let capabilityPromise = null;

    function getState() {
      return {phase, desired, active: !!active, local, reason, retryInMs,
        canStart: !destroyed && !active && !desired && phase !== 'stopping'};
    }
    function state(next, why = '', delay = 0) {
      phase = next; reason = why; retryInMs = delay;
      emit('onState', getState());
    }
    function snapshot() {
      const visible = segments.filter(s => s.text && !s.suppressed).map(s => ({
        id:s.id, text:s.text, isFinal:s.isFinal, unconfirmed:!!s.unconfirmed,
        sessionId:s.sessionId, index:s.index
      }));
      return {text:visible.map(s => s.text).join(' '),
        finalText:visible.filter(s => s.isFinal).map(s => s.text).join(' '),
        interimText:visible.filter(s => !s.isFinal).map(s => s.text).join(' '),
        segments:visible, local};
    }
    function draft() { emit('onDraft', snapshot()); }
    function markUnconfirmed(session) {
      if (!session) return;
      for (const s of session.slots.values()) if (!s.isFinal) s.unconfirmed = true;
    }
    function resolveStops() {
      const waiters = stopWaiters; stopWaiters = [];
      for (const resolve of waiters) resolve(getState());
    }
    function clearTimers() {
      cancel(restartTimer); cancel(stopTimer); cancel(errorTimer);
      restartTimer = stopTimer = errorTimer = null;
    }
    function detach(session) {
      if (!session) return;
      const r = session.recognizer;
      r.onstart = r.onresult = r.onerror = r.onend = r.onspeechstart = r.onspeechend = null;
    }
    function valid(session) { return !destroyed && active === session && session.run === run; }
    function abortSession(session) {
      detach(session);
      try { session.recognizer.abort(); } catch (_) { /* Already ended. */ }
    }
    function pause(why, error) {
      desired = false; clearTimers();
      const session = active; active = null;
      markUnconfirmed(session); if (session) abortSession(session);
      draft(); state(error ? 'error' : 'paused', why);
      if (error) emit('onError', {code:why, recoverable:false});
      resolveStops();
    }
    async function checkCapability() {
      if (capabilityPromise) return capabilityPromise;
      capabilityPromise = (async () => {
        let result = {supported:!!Recognition, local:false, status:Recognition ? 'browser' : 'unsupported'};
        if (Recognition && typeof Recognition.available === 'function') {
          let timer = null;
          try {
            const availability = await Promise.race([
              Promise.resolve(Recognition.available({langs:['ko-KR'], processLocally:true})),
              new Promise(resolve => { timer = later(() => resolve('unknown'), 1500); })
            ]);
            result = {supported:true, local:availability === 'available', status:String(availability)};
          } catch (_) {
            result = {supported:true, local:false, status:'browser'};
          } finally { cancel(timer); }
        }
        capability = result;
        if (!destroyed) emit('onCapability', {...result});
        return {...result};
      })();
      return capabilityPromise;
    }

    // Canonical text is tied to slots, not repeated result-event deliveries.
    function receive(session, event) {
      if (!valid(session)) return;
      const results = event.results;
      if (!results) return;
      const eventTime = now();
      const changed = Number.isInteger(event.resultIndex) ? event.resultIndex : 0;
      for (const [index, s] of session.slots) {
        if (index >= results.length && !s.isFinal) {
          segments = segments.filter(x => x !== s); session.slots.delete(index);
        }
      }
      for (let index = Math.max(0, changed); index < results.length; index++) {
        const result = results[index];
        const raw = clean(result && result[0] && result[0].transcript);
        let s = session.slots.get(index);
        if (s && s.isFinal) continue; // A final slot is immutable, including a replay.
        if (!s) {
          s = {id:'voice-'+instanceId+'-'+run+'-'+(++sequence), sessionId:session.id, index,
            raw:'', text:'', isFinal:false, unconfirmed:false, suppressed:false,
            turn:session.speechTurn, hadInterim:false, firstSeen:eventTime, prefix:''};
          session.slots.set(index,s); segments.push(s);
        }
        const hadInterim = s.hadInterim;
        s.raw = raw; s.text = raw; s.unconfirmed = false;
        s.suppressed = false;
        const newTurn = session.speechTurn > session.lastFinalTurn;
        const freshSpeech = newTurn || hadInterim;
        const sameBurst = lastAccepted && eventTime - lastAccepted.seenAt < 1400;
        const previous = lastAccepted && lastAccepted.text;
        if (raw && sameBurst && !freshSpeech) {
          if (key(raw) === key(previous)) {
            s.text = ''; s.suppressed = true;
            lastAccepted.seenAt = eventTime;
          } else if (!s.prefix && session.lastRaw && raw.startsWith(session.lastRaw + ' ')) {
            // Some engines append a cumulative hypothesis in a new slot.
            s.prefix = session.lastRaw;
          }
        }
        if (s.prefix && raw.startsWith(s.prefix+' ')) s.text = raw.slice(s.prefix.length).trim();
        // Replace an unfinished tail when the next engine confirms/extends it.
        if (s.text && !s.suppressed && index === 0) {
          const earlier = segments.slice(0,segments.indexOf(s));
          const tail = earlier[earlier.length-1];
          if (tail && tail.sessionId !== session.id && !tail.isFinal && tail.unconfirmed) {
            const a=key(tail.text), b=key(s.text);
            if (a===b || (Math.min(a.length,b.length)>=3 && (a.startsWith(b) || b.startsWith(a)))) {
              segments=segments.filter(x=>x!==tail);
            }
          }
        }
        if (!result.isFinal) {
          // Empty/repeated interim callbacks do not count as new speech evidence.
          if (raw && (!previous || key(raw) !== key(previous))) s.hadInterim = true;
          continue;
        }
        s.isFinal = true;
        if (s.text && !s.suppressed) {
          // A reconnect may confirm the immediately preceding unfinished tail.
          const earlier = segments.slice(0,segments.indexOf(s));
          const tail = earlier[earlier.length-1];
          if (tail && !tail.isFinal && tail.unconfirmed && key(tail.text) === key(s.text)) {
            segments = segments.filter(x => x !== tail);
          }
          session.hadOutput = true; emptyEnds = 0;
          session.lastFinalTurn = session.speechTurn;
          lastAccepted = {text:s.text, seenAt:eventTime};
          session.lastRaw = raw;
          emit('onFinal', {id:s.id,text:s.text,sessionId:session.id,index,local:session.local});
        }
      }
      draft();
    }

    function ended(session) {
      if (!valid(session)) return;
      cancel(stopTimer); stopTimer = null; cancel(errorTimer); errorTimer = null;
      markUnconfirmed(session); detach(session); active = null; draft();
      if (!desired) { state('idle', 'stopped'); resolveStops(); return; }
      if (doc && doc.hidden) { pause('page-hidden'); return; }
      const lifetime = now() - session.startedAt;
      const failedQuickly = lifetime < 2500;
      const serviceError = session.error && session.error !== 'no-speech';
      // Healthy engines may end after waiting silently. That must not cancel
      // the user's continue-listening intent; only real/rapid failures count.
      if (!session.hadOutput && (failedQuickly || serviceError)) emptyEnds++;
      else emptyEnds = 0;
      if (emptyEnds >= 4) { pause('recognizer-keeps-ending'); return; }
      const delay = session.hadOutput ? 220 : emptyEnds ? [650,1600,3600][emptyEnds-1] : 650;
      state('reconnecting', session.error || 'engine-ended', delay);
      const expectedRun = run;
      restartTimer = later(() => {
        restartTimer = null;
        if (desired && !active && expectedRun === run && !destroyed) begin();
      }, delay);
    }
    function begin() {
      if (!desired || active || destroyed) return;
      if (doc && doc.hidden) { pause('page-hidden'); return; }
      startedAt = startedAt.filter(t => now()-t < 15000);
      if (emptyEnds > 0 && startedAt.length >= 7) { pause('reconnect-rate-limit'); return; }
      let recognizer;
      try { recognizer = new Recognition(); }
      catch (_) { pause('start-failed',true); return; }
      const session = {recognizer,run,id:++sessionSequence,slots:new Map(),startedAt:now(),
        speechTurn:0,lastFinalTurn:0,lastRaw:'',hadOutput:false,error:'',local:false};
      active = session;
      recognizer.lang = 'ko-KR'; recognizer.continuous = true;
      recognizer.interimResults = true; recognizer.maxAlternatives = 1;
      session.local = runLocal && 'processLocally' in recognizer;
      if (session.local) recognizer.processLocally = true;
      local = session.local;
      recognizer.onstart = () => { if (valid(session) && desired) state('listening'); };
      recognizer.onspeechstart = () => { if (valid(session)) session.speechTurn++; };
      recognizer.onspeechend = () => {}; // Silence never ends app intent.
      recognizer.onresult = event => receive(session,event);
      recognizer.onend = () => ended(session);
      recognizer.onerror = event => {
        if (!valid(session)) return;
        const code = event.error || 'unknown'; session.error = code;
        if (!desired) return;
        if (FATAL.has(code)) { pause(code,true); return; }
        if (code === 'aborted') { pause('recognizer-aborted'); return; }
        emit('onError',{code,recoverable:true});
        // Do not launch a second engine if this one never reports ending.
        cancel(errorTimer);
        errorTimer = later(() => { if (valid(session)) pause('recognizer-unresponsive'); },1800);
      };
      state('starting'); startedAt.push(now());
      try { recognizer.start(); }
      catch (error) { if (valid(session)) pause(error && error.name === 'NotAllowedError' ? 'not-allowed' : 'start-failed',true); }
    }
    function start() {
      if (destroyed || desired || active || phase === 'stopping') return false;
      if (!Recognition) { state('unsupported','unsupported'); return false; }
      if (env.isSecureContext === false) { state('unsupported','insecure-context'); return false; }
      if (doc && doc.hidden) { state('paused','page-hidden'); return false; }
      clearTimers(); run++; sequence=0; segments=[]; lastAccepted=null; emptyEnds=0; startedAt=[];
      runLocal=capability.local;
      desired = true; draft(); begin(); return desired;
    }
    function stop(settings = {}) {
      if (phase === 'stopping' && active && !settings.discard) {
        return new Promise(resolve => stopWaiters.push(resolve));
      }
      desired = false; clearTimers();
      if (settings.discard) {
        run++; const session=active; active=null;
        if (session) abortSession(session);
        segments=[]; lastAccepted=null;
        state('idle','discarded'); resolveStops(); return Promise.resolve(getState());
      }
      if (!active) {
        // A consumer may have manually edited its text since the last snapshot.
        // Idle stop is idempotent and must not replay an empty or stale draft.
        state('idle','stopped'); resolveStops(); return Promise.resolve(getState());
      }
      const session=active;
      const result=new Promise(resolve => stopWaiters.push(resolve));
      state('stopping','user-stop');
      stopTimer=later(() => {
        if (!valid(session)) return;
        markUnconfirmed(session); active=null; abortSession(session);
        stopTimer=null; draft(); state('idle','stop-timeout'); resolveStops();
      },1800);
      try { session.recognizer.stop(); }
      catch (_) {
        cancel(stopTimer); stopTimer=null;
        markUnconfirmed(session); active=null; abortSession(session);
        draft(); state('idle','stopped'); resolveStops();
      }
      return result;
    }
    function hidden() { if (doc && doc.hidden && (desired || active)) pause('page-hidden'); }
    function pagehide() { if (desired || active) pause('page-hidden'); }
    function destroy() {
      if (destroyed) return;
      stop({discard:true}); destroyed=true;
      if (doc) doc.removeEventListener('visibilitychange',hidden);
      if (env.removeEventListener) env.removeEventListener('pagehide',pagehide);
    }
    if (doc) doc.addEventListener('visibilitychange',hidden);
    if (env.addEventListener) env.addEventListener('pagehide',pagehide);
    checkCapability();
    return {start,stop,destroy,getState,checkCapability,getSnapshot:snapshot};
  }
  root.DoctorPetSpeech = Object.freeze({create});
  if (typeof module !== 'undefined' && module.exports) module.exports = root.DoctorPetSpeech;
})(typeof window !== 'undefined' ? window : globalThis);
