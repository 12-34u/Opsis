import React, { useState, useEffect, useRef, useCallback } from 'react';
import '../styles/OutputPanel.css';

const REGS_8085 = ['A', 'B', 'C', 'D', 'E', 'H', 'L'];
const FLAG_NAMES = ['Z', 'C', 'S', 'P', 'O'];

function fmtHex(v, pad = 2) {
  return '0x' + ((v ?? 0) >>> 0).toString(16).toUpperCase().padStart(pad, '0');
}
function fmtBin(v, bits = 8) {
  return ((v ?? 0) >>> 0).toString(2).padStart(bits, '0');
}

function diffRegs(before, after) {
  if (!before?.registers || !after?.registers) return {};
  const d = {};
  for (const r of REGS_8085) {
    if (before.registers[r] !== after.registers[r])
      d[r] = { from: before.registers[r], to: after.registers[r] };
  }
  return d;
}

function diffFlags(before, after) {
  if (!before?.flags || !after?.flags) return {};
  const d = {};
  for (const f of FLAG_NAMES) {
    if (before.flags[f] !== after.flags[f])
      d[f] = { from: before.flags[f], to: after.flags[f] };
  }
  return d;
}

function diffMem(before, after) {
  if (!before?.memory || !after?.memory) return [];
  const out = [];
  for (let i = 0, len = Math.min(before.memory.length, after.memory.length); i < len; i++) {
    if (before.memory[i] !== after.memory[i])
      out.push({ addr: i, from: before.memory[i], to: after.memory[i] });
  }
  return out;
}

/* ────────────────────────────────────────── */
export default function OutputPanel({
  output = [],
  error = null,
  instructionCount = 0,
  isRunning = false,
  steps = [],
  assemblerState = null,
}) {
  const [step, setStep] = useState(-1);     // -1 = summary
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(700);
  const timerRef = useRef(null);
  const tlRef = useRef(null);
  const total = steps.length;
  const has = total > 0;
  const cur = has && step >= 0 ? steps[step] : null;

  // reset on new execution
  useEffect(() => { setStep(-1); setPlaying(false); }, [steps, error]);

  // autoplay
  useEffect(() => {
    if (playing && has) {
      timerRef.current = setInterval(() => {
        setStep(p => { if (p >= total - 1) { setPlaying(false); return p; } return p + 1; });
      }, speed);
    }
    return () => clearInterval(timerRef.current);
  }, [playing, speed, total, has]);

  // scroll timeline
  useEffect(() => {
    if (tlRef.current && step >= 0) {
      const el = tlRef.current.children[step];
      if (el) el.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' });
    }
  }, [step]);

  const play  = useCallback(() => { if (step >= total - 1) setStep(0); setPlaying(true); }, [step, total]);
  const pause = useCallback(() => setPlaying(false), []);
  const next  = useCallback(() => { setPlaying(false); setStep(p => Math.min(p + 1, total - 1)); }, [total]);
  const prev  = useCallback(() => { setPlaying(false); setStep(p => Math.max(p - 1, 0)); }, []);
  const reset = useCallback(() => { setPlaying(false); setStep(-1); }, []);

  // current step data
  const regCh   = cur ? diffRegs(cur.before, cur.after)  : {};
  const flagCh  = cur ? diffFlags(cur.before, cur.after)  : {};
  const memCh   = cur ? diffMem(cur.before, cur.after)    : [];

  // which register state to display in the sidebar
  const regs  = cur ? cur.after.registers : (has ? steps[total - 1].after.registers : assemblerState?.registers ?? null);
  const flags = cur ? cur.after.flags     : (has ? steps[total - 1].after.flags     : assemblerState?.flags ?? null);
  const pc    = cur ? cur.after.pc        : (has ? steps[total - 1].after.pc        : assemblerState?.pc ?? 0);
  const sp    = cur ? cur.after.sp        : (has ? steps[total - 1].after.sp        : assemblerState?.sp ?? 0xFFFE);

  // summary mem diff
  const summaryMem = [];
  if (!cur && has) {
    const ini = steps[0].before.memory, fin = steps[total - 1].after.memory;
    if (ini && fin) for (let i = 0; i < ini.length; i++) if (ini[i] !== fin[i]) summaryMem.push({ addr: i, from: ini[i], to: fin[i] });
  }

  const errLines = error ? String(error).split('\n').filter(Boolean) : [];

  return (
    <div className="op-root">
      {/* ─── LEFT: main content area ─── */}
      <div className="op-main">
        {/* header bar */}
        <div className="op-bar">
          <span className="op-title">Terminal — Execution</span>
          <div className="op-bar-right">
            {isRunning && <span className="op-running">● Running</span>}
            {instructionCount > 0 && <span className="op-badge">{instructionCount} instr</span>}
          </div>
        </div>

        {/* error */}
        {error && (
          <div className="op-error">
            <span className="op-error-icon">✖</span>
            <div>{errLines.map((l, i) => <div key={i}>{l}</div>)}</div>
          </div>
        )}

        {/* body */}
        <div className="op-body">
          {!has && !error ? (
            <div className="op-empty">
              <span className="op-empty-icon">▶</span>
              <span>Run code to see execution trace</span>
            </div>
          ) : has ? (
            <>
              {/* controls */}
              <div className="op-controls">
                <button className="op-ctrl" onClick={reset} title="Summary">⏮</button>
                <button className="op-ctrl" onClick={prev} disabled={step <= 0} title="Prev">◀</button>
                {playing
                  ? <button className="op-ctrl op-ctrl-main" onClick={pause} title="Pause">⏸</button>
                  : <button className="op-ctrl op-ctrl-main" onClick={play}  title="Play">▶</button>}
                <button className="op-ctrl" onClick={next} disabled={step >= total - 1} title="Next">▶</button>
                <button className="op-ctrl" onClick={() => { setPlaying(false); setStep(total - 1); }} title="End">⏭</button>
                <div className="op-speed">
                  <span>Speed</span>
                  <input type="range" min={100} max={2000} step={100}
                    value={2100 - speed} onChange={e => setSpeed(2100 - +e.target.value)} />
                </div>
                <span className="op-step-label">
                  {step < 0 ? 'Summary' : `Step ${step + 1}/${total}`}
                </span>
              </div>

              {/* timeline */}
              <div className="op-tl-wrap">
                <div className="op-tl" ref={tlRef}>
                  {steps.map((s, i) => {
                    const act = i === step, past = step >= 0 && i < step;
                    const rc = Object.keys(diffRegs(s.before, s.after)).length > 0;
                    const mc = diffMem(s.before, s.after).length > 0;
                    const oc = s.output !== null;
                    return (
                      <button key={i} className={`op-tl-step ${act ? 'act' : ''} ${past ? 'past' : ''}`}
                        onClick={() => { setPlaying(false); setStep(i); }} title={s.instruction}>
                        <span className="op-tl-n">{i + 1}</span>
                        <span className="op-tl-ins">{s.instruction}</span>
                        <span className="op-tl-tags">
                          {rc && <span className="op-tag tag-r">R</span>}
                          {mc && <span className="op-tag tag-m">M</span>}
                          {oc && <span className="op-tag tag-o">O</span>}
                        </span>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* ─── step detail ─── */}
              {cur ? (
                <div className="op-detail">
                  <div className="op-instr-bar">
                    <span className="op-pc">PC:{cur.pc}</span>
                    <code className="op-instr">{cur.instruction}</code>
                    {Object.keys(regCh).length > 0 && <span className="op-chg">{Object.keys(regCh).length} reg changed</span>}
                  </div>

                  {/* memory writes this step */}
                  {memCh.length > 0 && (
                    <div className="op-mem-section">
                      <div className="op-sec-title">Memory Writes</div>
                      {memCh.map((m, i) => (
                        <div key={i} className="op-mem-row">
                          <span className="op-mem-addr">[{fmtHex(m.addr, 4)}]</span>
                          <span className="op-mem-old">{fmtHex(m.from)}</span>
                          <span className="op-arrow">→</span>
                          <span className="op-mem-new">{fmtHex(m.to)}</span>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* output this step */}
                  {cur.output && (
                    <div className="op-out-section">
                      <div className="op-sec-title">Output</div>
                      <div className="op-out-vals">
                        <span className="op-oval op-o-hex">{cur.output.hex}</span>
                        <span className="op-oval op-o-dec">{cur.output.decimal}</span>
                        <span className="op-oval op-o-bin">{cur.output.binary}</span>
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                /* ─── summary ─── */
                <div className="op-detail">
                  {summaryMem.length > 0 && (
                    <div className="op-mem-section">
                      <div className="op-sec-title">Memory Changes (total)</div>
                      {summaryMem.slice(0, 32).map((m, i) => (
                        <div key={i} className="op-mem-row">
                          <span className="op-mem-addr">[{fmtHex(m.addr, 4)}]</span>
                          <span className="op-mem-old">{fmtHex(m.from)}</span>
                          <span className="op-arrow">→</span>
                          <span className="op-mem-new">{fmtHex(m.to)}</span>
                        </div>
                      ))}
                      {summaryMem.length > 32 && <div className="op-more">…and {summaryMem.length - 32} more</div>}
                    </div>
                  )}
                </div>
              )}

              {/* ─── OUTPUT VALUES (always visible at bottom) ─── */}
              {output.length > 0 && (
                <div className="op-output-block">
                  <div className="op-sec-title">Program Output</div>
                  {output.map((item, idx) => (
                    <div key={idx} className="op-out-row">
                      <span className="op-out-idx">#{idx + 1}</span>
                      <span className="op-oval op-o-hex">{item.hex}</span>
                      <span className="op-oval op-o-dec">{item.decimal}</span>
                      <span className="op-oval op-o-bin">{item.binary}</span>
                    </div>
                  ))}
                </div>
              )}
            </>
          ) : null}
        </div>
      </div>

      {/* ─── RIGHT SIDEBAR: Register Blocks ─── */}
      <div className="op-sidebar">
        <div className="op-sb-title">Registers</div>
        <div className="op-reg-blocks">
          {REGS_8085.map(r => {
            const val = regs ? regs[r] : 0;
            const changed = regCh[r];
            return (
              <div key={r} className={`op-reg-block ${changed ? 'op-reg-hit' : ''}`}>
                <div className="op-reg-name">{r}</div>
                <div className="op-reg-hex">{fmtHex(val)}</div>
                <div className="op-reg-dec">{val}</div>
                <div className="op-reg-bin">{fmtBin(val)}</div>
                {changed && (
                  <div className="op-reg-delta">
                    <span className="op-delta-from">{fmtHex(changed.from)}</span>
                    <span className="op-arrow">→</span>
                    <span className="op-delta-to">{fmtHex(changed.to)}</span>
                  </div>
                )}
              </div>
            );
          })}
        </div>

        <div className="op-sb-title">Flags</div>
        <div className="op-flag-row">
          {FLAG_NAMES.map(f => {
            const val = flags ? flags[f] : false;
            const hit = flagCh[f];
            return (
              <div key={f} className={`op-flag ${val ? 'op-flag-on' : ''} ${hit ? 'op-flag-hit' : ''}`}>
                <span className="op-flag-n">{f}</span>
                <span className="op-flag-v">{val ? '1' : '0'}</span>
              </div>
            );
          })}
        </div>

        <div className="op-sb-title">Pointers</div>
        <div className="op-ptr-row">
          <div className="op-ptr"><span>PC</span><span>{pc}</span></div>
          <div className="op-ptr"><span>SP</span><span>{fmtHex(sp, 4)}</span></div>
        </div>
      </div>
    </div>
  );
}
