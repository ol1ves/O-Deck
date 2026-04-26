// Variation C v3 — "Atelier"
// Less car-play, more editorial cyberdeck.
// • Asymmetric layout — TIME is the hero, not boxed in a card
// • Blurred drifting orbs replace flow field (slow, lava-lamp / aurora)
// • Two accents: warm sand + dusty sage (not just brown/grey)
// • Now Playing as a vertical strip on the right, art smaller, type-forward
// • Calendar as a vertical timeline ribbon
// • Cleaner whites, slightly cooler

// ── Drifting orbs background ─────────────────────────────────────
function DriftOrbs({ palette = ['#dcb98a','#9bb38b','#a08fb3','#c79880'], mode = 'calm', count = 6 }) {
  const flashRef = React.useRef(0);
  const ref = React.useRef(null);
  const stateRef = React.useRef({ orbs: [], raf: 0, t: 0 });

  React.useEffect(() => {
    const cv = ref.current; if (!cv) return;
    const ctx = cv.getContext('2d');
    const dpr = Math.min(window.devicePixelRatio || 1, 1.5);

    const resize = () => {
      const r = cv.getBoundingClientRect();
      cv.width = r.width * dpr; cv.height = r.height * dpr;
      ctx.setTransform(1,0,0,1,0,0);
      ctx.scale(dpr, dpr);
    };
    resize();
    const ro = new ResizeObserver(resize); ro.observe(cv);

    const w0 = cv.clientWidth, h0 = cv.clientHeight;
    stateRef.current.orbs = Array.from({length: count}).map((_, i) => ({
      x: Math.random() * w0, y: Math.random() * h0,
      r: 90 + Math.random() * 140,
      // slow drift speeds
      vx: (Math.random() - 0.5) * 0.18,
      vy: (Math.random() - 0.5) * 0.14,
      color: palette[i % palette.length],
      phase: Math.random() * Math.PI * 2,
      ampX: 30 + Math.random() * 50,
      ampY: 20 + Math.random() * 40,
      bx: Math.random() * w0,
      by: Math.random() * h0,
    }));

    let last = performance.now();
    const step = (now) => {
      const dt = Math.min(50, now - last); last = now;
      const s = stateRef.current; s.t += dt * 0.001;
      const w = cv.clientWidth, h = cv.clientHeight;

      // clear with deep base — full clear so orbs stay clean (no trails)
      ctx.globalCompositeOperation = 'source-over';
      ctx.clearRect(0, 0, w, h);

      // mode tweaks
      const speedMul = mode === 'thunder' ? 2.4 : mode === 'rain' ? 1.3 : mode === 'music' ? 1.5 : 1;
      const alphaMul = mode === 'rain' ? 0.6 : mode === 'thunder' ? 1.1 : 1;

      // thunder: occasional bright flash
      if (mode === 'thunder') {
        if (Math.random() < 0.005) flashRef.current = 1;
        if (flashRef.current > 0) {
          ctx.globalCompositeOperation = 'source-over';
          ctx.fillStyle = `rgba(220, 200, 220, ${flashRef.current * 0.18})`;
          ctx.fillRect(0, 0, w, h);
          flashRef.current *= 0.78;
        }
      }

      ctx.globalCompositeOperation = 'screen';
      for (const o of s.orbs) {
        // base position drifts slowly + sinusoidal wobble
        o.bx += o.vx * speedMul; o.by += o.vy * speedMul;
        if (o.bx < -o.r) o.bx = w + o.r;
        if (o.bx > w + o.r) o.bx = -o.r;
        if (o.by < -o.r) o.by = h + o.r;
        if (o.by > h + o.r) o.by = -o.r;

        const x = o.bx + Math.sin(s.t * 0.3 + o.phase) * o.ampX;
        const y = o.by + Math.cos(s.t * 0.27 + o.phase) * o.ampY;

        // music breathes radius
        const beat = mode === 'music' ? 1 + Math.max(0, Math.sin(s.t * 4.2)) * 0.18 : 1;
        const rr = o.r * beat;

        const grad = ctx.createRadialGradient(x, y, 0, x, y, rr);
        grad.addColorStop(0, `${o.color}55`);
        grad.addColorStop(0.4, `${o.color}1f`);
        grad.addColorStop(1, `${o.color}00`);
        ctx.globalAlpha = 0.55 * alphaMul;
        ctx.fillStyle = grad;
        ctx.beginPath(); ctx.arc(x, y, rr, 0, Math.PI * 2); ctx.fill();
      }
      ctx.globalAlpha = 1;
      stateRef.current.raf = requestAnimationFrame(step);
    };
    stateRef.current.raf = requestAnimationFrame(step);
    return () => { cancelAnimationFrame(stateRef.current.raf); ro.disconnect(); };
  }, [mode, count, palette.join(',')]);

  return <canvas ref={ref} style={{
    position:'absolute', inset:0, width:'100%', height:'100%',
    pointerEvents:'none', filter:'blur(36px)', opacity: 0.85,
  }} />;
}

// Rain overlay: sparse, slow, fine streaks (separate from orbs so we can stack)
function RainOverlay({ intensity = 0.5, color = '#aac0d6' }) {
  const ref = React.useRef(null);
  const raf = React.useRef(0);
  React.useEffect(() => {
    const cv = ref.current; if (!cv) return;
    const ctx = cv.getContext('2d');
    const dpr = Math.min(window.devicePixelRatio || 1, 1.5);
    const resize = () => {
      const r = cv.getBoundingClientRect();
      cv.width = r.width * dpr; cv.height = r.height * dpr;
      ctx.setTransform(1,0,0,1,0,0); ctx.scale(dpr, dpr);
    };
    resize();
    const ro = new ResizeObserver(resize); ro.observe(cv);
    const w0 = cv.clientWidth, h0 = cv.clientHeight;
    const drops = Array.from({length: Math.floor(60 * intensity)}).map(() => ({
      x: Math.random() * w0, y: Math.random() * h0,
      vy: 1.2 + Math.random() * 1.4, len: 8 + Math.random() * 14,
    }));
    const step = () => {
      const w = cv.clientWidth, h = cv.clientHeight;
      ctx.clearRect(0,0,w,h);
      ctx.strokeStyle = color; ctx.lineWidth = 0.7; ctx.globalAlpha = 0.35;
      for (const d of drops) {
        d.y += d.vy; d.x -= 0.3;
        if (d.y > h) { d.y = -10; d.x = Math.random() * w; }
        if (d.x < 0) d.x = w;
        ctx.beginPath(); ctx.moveTo(d.x, d.y); ctx.lineTo(d.x + 1.5, d.y + d.len); ctx.stroke();
      }
      raf.current = requestAnimationFrame(step);
    };
    raf.current = requestAnimationFrame(step);
    return () => { cancelAnimationFrame(raf.current); ro.disconnect(); };
  }, [intensity, color]);
  return <canvas ref={ref} style={{position:'absolute', inset:0, width:'100%', height:'100%', pointerEvents:'none'}} />;
}

// Subtle grain overlay (CSS only — cheap)
function Grain() {
  return <div style={{
    position:'absolute', inset:0, pointerEvents:'none', opacity:0.10, mixBlendMode:'overlay',
    backgroundImage: `url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='160' height='160'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2'/><feColorMatrix values='0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 0.6 0'/></filter><rect width='160' height='160' filter='url(%23n)'/></svg>")`,
  }} />;
}

// Live clock w/ seconds
function useLiveClock3() {
  const [t, setT] = React.useState(() => new Date(2026, 3, 26, 11, 47, 18));
  React.useEffect(() => {
    const id = setInterval(() => setT(prev => new Date(prev.getTime() + 1000)), 1000);
    return () => clearInterval(id);
  }, []);
  return t;
}

// Animated counter (transit minutes ticking down on a slow loop, just for liveness)
function useDriftMins(initial) {
  const [m, setM] = React.useState(initial);
  React.useEffect(() => {
    const id = setInterval(() => {
      setM(prev => prev <= 1 ? initial + Math.floor(Math.random()*3) : prev - 1);
    }, 12000);
    return () => clearInterval(id);
  }, [initial]);
  return m;
}

function ScreenCv3({ flowMode = 'music' }) {
  const D = window.ODECK_DATA;
  const bg = '#15130f';
  const ink = '#f0e8d6';
  const inkDim = 'rgba(240,232,214,0.55)';
  const inkSub = 'rgba(240,232,214,0.32)';
  const accentSand = '#e6c89b';
  const accentSage = '#a8c19a';
  const accentRose = '#d49a8e';
  const line = 'rgba(240,232,214,0.08)';

  const palette = { dom:'#7a5f4a', accent:accentSand, ink:'#f4ead7' };

  // pick orb palette per mode
  const orbPalettes = {
    calm:    ['#e6c89b', '#a8c19a', '#7a5f4a', '#5a6a78'],
    music:   ['#a08fb3', '#d49a8e', '#e6c89b', '#7a90a8'],
    rain:    ['#5a7088', '#7a90a8', '#3e556a', '#9bb38b'],
    thunder: ['#c8b89a', '#7a6a8a', '#3e3a4a', '#d49a8e'],
  }[flowMode] || ['#e6c89b','#a8c19a'];

  const clock = useLiveClock3();
  const hh = String(clock.getHours() % 12 || 12).padStart(2, '0');
  const mm = String(clock.getMinutes()).padStart(2, '0');
  const ss = String(clock.getSeconds()).padStart(2, '0');
  const ampm = clock.getHours() >= 12 ? 'PM' : 'AM';

  const tMins = useDriftMins(2);

  const allTrains = [...D.transit.stations[0].trains, ...D.transit.stations[1].trains];

  return (
    <div className="odeck-screen" style={{
      background: bg,
      color: ink, fontFamily:"'IBM Plex Mono', monospace",
      position:'relative', overflow:'hidden',
    }}>

      {/* background layers */}
      <DriftOrbs palette={orbPalettes} mode={flowMode} count={7} />
      {(flowMode === 'rain' || flowMode === 'thunder') && (
        <RainOverlay intensity={flowMode === 'thunder' ? 0.9 : 0.5} color={flowMode === 'thunder' ? '#c8b8a0' : '#aac0d6'} />
      )}
      <Grain />

      {/* foreground content — asymmetric, no rounded-card grid */}
      <div style={{
        position:'absolute', inset:0, padding:'16px 22px',
        display:'flex', flexDirection:'column',
      }}>

        {/* status line — top */}
        <header style={{
          display:'flex', alignItems:'center', justifyContent:'space-between',
          fontSize:10, letterSpacing:1.5, color:inkDim, fontFamily:"'IBM Plex Mono', monospace",
        }}>
          <div style={{display:'flex', gap:18}}>
            <span style={{color:ink, fontWeight:500}}>O—DECK</span>
            <span style={{color:inkSub}}>/{D.device.callsign}</span>
            <span><span style={{color:accentSage}}>●</span> {D.status.host}</span>
            <span style={{color:inkSub}}>up {D.status.uptime}</span>
            <span style={{color:inkDim}}>cpu <span style={{color:accentSage}}><BlockBar value={D.status.cpu/100} width={6} /></span> {D.status.cpu}%</span>
            <span style={{color:inkDim}}>ram <span style={{color:accentSage}}><BlockBar value={0.42} width={6} /></span> 42%</span>
          </div>
          <div style={{display:'flex', gap:14}}>
            <span style={{color: flowMode === 'music' ? accentSand : flowMode === 'rain' ? '#aac0d6' : flowMode === 'thunder' ? accentRose : accentSage}}>
              ◌ {flowMode}
            </span>
            <span style={{color:inkSub}}>{D.status.wifi}</span>
            <span style={{color:accentSand}}>{D.time.date}</span>
          </div>
        </header>

        {/* Main asymmetric area */}
        <div style={{
          flex:1, display:'grid',
          gridTemplateColumns:'1fr 320px',
          gridTemplateRows:'auto 1fr',
          gap:'18px 28px', marginTop:14,
        }}>

          {/* TIME — hero, raw, no card */}
          <div style={{gridColumn:'1', gridRow:'1', position:'relative'}}>
            <div style={{display:'flex', alignItems:'baseline', gap:14}}>
              <div style={{
                fontFamily:"'Inter', sans-serif", fontWeight:200, fontSize:148,
                lineHeight:0.85, letterSpacing:-7, fontVariantNumeric:'tabular-nums',
                color: ink,
              }}>
                {hh}<span className="blink" style={{color:accentSand, fontWeight:200}}>:</span>{mm}
              </div>
              <div style={{display:'flex', flexDirection:'column', gap:4, paddingBottom:10}}>
                <div style={{
                  fontFamily:"'Inter', sans-serif", fontWeight:300, fontSize:36,
                  letterSpacing:-1.5, color:inkDim, lineHeight:1, fontVariantNumeric:'tabular-nums',
                }}>:{ss}</div>
                <div style={{fontSize:11, letterSpacing:2, color:inkSub}}>{ampm} · EDT</div>
              </div>
            </div>
            {/* weather under the time, inline */}
            <div style={{
              display:'flex', alignItems:'center', gap:18, marginTop:6,
              fontFamily:"'Inter', sans-serif",
            }}>
              <div style={{display:'flex', alignItems:'center', gap:10}}>
                <span style={{color:accentSand}}><WeatherIcon size={28} /></span>
                <span style={{
                  fontWeight:300, fontSize:32, letterSpacing:-1.2, fontVariantNumeric:'tabular-nums',
                }}>{D.weather.tempF}°</span>
              </div>
              <div style={{
                fontFamily:"'IBM Plex Mono', monospace", fontSize:11, color:inkDim, letterSpacing:1, lineHeight:1.5,
              }}>
                <div>{D.weather.cond.toLowerCase()}</div>
                <div style={{color:inkSub}}>H{D.weather.high}° L{D.weather.low}° · feels {D.weather.feelsLike}°</div>
              </div>
              <div style={{flex:1}} />
              <div style={{paddingBottom:4}}>
                <Sparkline points={D.weather.hourly} color={accentSage} width={140} height={30} />
              </div>
            </div>
          </div>

          {/* NOW PLAYING — sidebar strip, vertical, type-forward */}
          <aside style={{
            gridColumn:'2', gridRow:'1 / span 2',
            position:'relative',
            display:'flex', flexDirection:'column', gap:14,
            paddingLeft:22, borderLeft:`1px solid ${line}`,
          }}>
            <div style={{
              fontSize:10, letterSpacing:2, color:inkDim,
              display:'flex', alignItems:'center', gap:8,
            }}>
              <EQBars count={4} size={10} width={2} color={accentSage} />
              <span>NOW PLAYING</span>
            </div>

            <AlbumArt palette={palette} size={170} label="AMNESIAC" glyph="◊" />

            <div>
              <div style={{
                fontFamily:"'Inter', sans-serif", fontWeight:600, fontSize:24, lineHeight:1.15,
                letterSpacing:-0.4, color:ink, textWrap:'balance',
              }}>{D.nowPlaying.track}</div>
              <div style={{
                fontFamily:"'Inter', sans-serif", fontSize:14, color:inkDim, marginTop:8, letterSpacing:0.2,
              }}>
                <span style={{color:ink}}>{D.nowPlaying.artist}</span>
              </div>
              <div style={{
                fontFamily:"'IBM Plex Mono', monospace", fontSize:10, color:inkSub, marginTop:3, letterSpacing:1,
              }}>
                from <span style={{textTransform:'uppercase'}}>{D.nowPlaying.album}</span>
              </div>
            </div>

            <div style={{display:'flex', flexDirection:'column', gap:5, marginTop:'auto'}}>
              <div style={{height:2, background:'rgba(240,232,214,0.10)', borderRadius:2, overflow:'hidden'}}>
                <div style={{width:`${D.nowPlaying.progress*100}%`, height:'100%', background:accentSand}} />
              </div>
              <div style={{display:'flex', justifyContent:'space-between', fontSize:10, color:inkDim, fontVariantNumeric:'tabular-nums', letterSpacing:1}}>
                <span>{D.nowPlaying.elapsed}</span>
                <span>{D.nowPlaying.total}</span>
              </div>
            </div>

            {/* RSS, tucked */}
            <div style={{
              borderTop:`1px solid ${line}`, paddingTop:12, display:'flex', flexDirection:'column', gap:8,
            }}>
              <div style={{fontSize:10, letterSpacing:2, color:inkDim}}>FEED</div>
              {D.rss.headlines.slice(0,2).map((h,i) => (
                <div key={i}>
                  <div style={{fontSize:9, color:accentRose, letterSpacing:1.2, marginBottom:2}}>{h.src} · {h.age}</div>
                  <div style={{fontFamily:"'Inter', sans-serif", fontSize:12, color:ink, lineHeight:1.3, textWrap:'pretty'}}>
                    {h.title}
                  </div>
                </div>
              ))}
            </div>
          </aside>

          {/* LEFT BOTTOM — split: TRANSIT (typographic) and CALENDAR (timeline ribbon) */}
          <div style={{
            gridColumn:'1', gridRow:'2',
            display:'grid', gridTemplateColumns:'1fr 1.1fr', gap:24,
            minHeight:0,
          }}>
            {/* Transit — typographic, no card */}
            <div style={{display:'flex', flexDirection:'column', gap:8, minHeight:0}}>
              <div style={{
                fontSize:10, letterSpacing:2, color:inkDim, display:'flex', alignItems:'center', gap:8,
              }}>
                <span>NEXT TRAINS</span>
                <span style={{flex:1, height:1, background:line}} />
                <span style={{color:accentRose}}>! delays</span>
              </div>

              {/* Hero next train — large with status */}
              <div style={{display:'flex', alignItems:'center', gap:12}}>
                <MTAPill line={allTrains[0].line} color={allTrains[0].color} size={32} />
                <div style={{flex:1, minWidth:0}}>
                  <div style={{fontSize:10, color:inkDim, letterSpacing:1}}>JAY ST · {allTrains[0].dest.toUpperCase()}</div>
                  <div style={{fontSize:9, color: allTrains[0].delay > 0 ? accentRose : accentSage, letterSpacing:0.5, marginTop:1}}>
                    {allTrains[0].status}
                  </div>
                </div>
                <div style={{
                  fontFamily:"'Inter', sans-serif", fontWeight:300, fontSize:54,
                  fontVariantNumeric:'tabular-nums', letterSpacing:-2, lineHeight:0.9,
                  color:ink,
                }}>
                  {tMins}<span style={{fontSize:14, color:inkDim, marginLeft:2, fontWeight:400, letterSpacing:0}}>min</span>
                </div>
              </div>

              {/* the rest, compact w/ status */}
              <div style={{display:'flex', flexDirection:'column', gap:5, marginTop:2}}>
                {allTrains.slice(1,5).map((t,i) => (
                  <div key={i} style={{display:'flex', alignItems:'center', gap:9}}>
                    <MTAPill line={t.line} color={t.color} size={18} />
                    <div style={{flex:1, minWidth:0}}>
                      <div style={{fontSize:10.5, color:inkDim, letterSpacing:0.4, whiteSpace:'nowrap', overflow:'hidden', textOverflow:'ellipsis', fontFamily:"'Inter', sans-serif"}}>
                        {t.dest}
                      </div>
                      <div style={{fontSize:8.5, color: t.delay > 0 ? accentRose : inkSub, letterSpacing:0.6, marginTop:1}}>
                        {t.status}
                      </div>
                    </div>
                    <div style={{fontFamily:"'Inter', sans-serif", fontSize:16, fontWeight:500, fontVariantNumeric:'tabular-nums', letterSpacing:-0.4}}>
                      {t.mins}<span style={{fontSize:9, color:inkSub, marginLeft:1, fontWeight:400}}>m</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Calendar — vertical timeline ribbon */}
            <div style={{display:'flex', flexDirection:'column', gap:6, minHeight:0}}>
              <div style={{
                fontSize:10, letterSpacing:2, color:inkDim, display:'flex', alignItems:'center', gap:8,
              }}>
                <span>TODAY · 4 EVENTS</span>
                <span style={{flex:1, height:1, background:line}} />
                <span style={{color:inkSub}}>next in {D.calendar.nextIn}</span>
              </div>

              <div style={{
                position:'relative', flex:1, paddingLeft:14, display:'flex', flexDirection:'column', gap:6,
              }}>
                {/* spine */}
                <div style={{
                  position:'absolute', left:4, top:8, bottom:8,
                  width:1, background:`linear-gradient(180deg, ${accentSand}77, ${line})`,
                }} />
                {D.calendar.events.map((e,i) => (
                  <div key={i} style={{display:'flex', alignItems:'flex-start', gap:10, position:'relative'}}>
                    {/* node */}
                    <div style={{
                      position:'absolute', left:-14, top:6, width:9, height:9, borderRadius:9,
                      background: i === 0 ? accentSand : 'transparent',
                      border: `1.5px solid ${i === 0 ? accentSand : 'rgba(240,232,214,0.4)'}`,
                    }} />
                    <div style={{
                      width:46, fontFamily:"'Inter', sans-serif", fontSize:12.5, fontWeight:500,
                      fontVariantNumeric:'tabular-nums', letterSpacing:-0.2, color:ink, paddingTop:1, flexShrink:0,
                    }}>{e.time}</div>
                    <div style={{flex:1, minWidth:0}}>
                      <div style={{fontFamily:"'Inter', sans-serif", fontSize:13, fontWeight:500, lineHeight:1.2, color:ink}}>
                        {e.title}
                      </div>
                      <div style={{fontSize:9.5, color:inkDim, marginTop:2, letterSpacing:0.5}}>
                        {e.loc.toLowerCase()}
                        {e.notion && <span style={{color:accentSage, marginLeft:6}}>· notion/{e.project}</span>}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Bottom: commits + dock + ticker — single line, low chrome */}
        <footer style={{
          display:'flex', alignItems:'center', gap:16, marginTop:8,
          paddingTop:10, borderTop:`1px solid ${line}`,
        }}>
          <div style={{display:'flex', alignItems:'center', gap:8, flexShrink:0}}>
            <span style={{fontSize:9, letterSpacing:1.5, color:inkDim}}>git</span>
            <CommitHeartbeat color={accentSage} count={36} />
            <span style={{fontSize:9, letterSpacing:1.2, color:inkSub, fontVariantNumeric:'tabular-nums'}}>
              {D.github.commits}↑ {D.github.prs}pr
            </span>
          </div>
          <span style={{width:1, height:14, background:line}} />
          <div style={{display:'flex', gap:14, fontSize:10, letterSpacing:1.5, color:inkDim, flexShrink:0}}>
            {['POMO','GH','MAP','DOOM','PHOTO','SHOW'].map((k,i) => (
              <span key={i} style={{display:'inline-flex', gap:4, alignItems:'center'}}>
                <span style={{
                  width:5, height:5, borderRadius:5, background: i === 0 ? accentSand : 'rgba(240,232,214,0.25)',
                }} />
                {k}
              </span>
            ))}
          </div>
          <span style={{width:1, height:14, background:line}} />
          <div style={{flex:1, minWidth:0}}>
            <Ticker items={D.rss.ticker} color={ink} opacity={0.45} fontSize={10} monospace />
          </div>
        </footer>
      </div>
    </div>
  );
}

window.ScreenCv3 = ScreenCv3;
