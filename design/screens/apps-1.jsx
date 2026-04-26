// Fullscreen apps batch 1: Pomodoro, Transit detail, Calendar
// All use ODScreen + ODStatusBar + ODDock + tokens from system.jsx

// ─────────────────────────────────────────────────────────────────
// POMODORO — running session, ambient
// ─────────────────────────────────────────────────────────────────
function PomoApp() {
  const [t, setT] = React.useState(15 * 60 + 47); // 15:47 remaining
  React.useEffect(() => {
    const id = setInterval(() => setT(p => Math.max(0, p - 1)), 1000);
    return () => clearInterval(id);
  }, []);
  const total = 25 * 60;
  const elapsed = total - t;
  const progress = elapsed / total;
  const mm = String(Math.floor(t / 60)).padStart(2, '0');
  const ss = String(t % 60).padStart(2, '0');

  return (
    <ODScreen mode="calm">
      <ODStatusBar app="POMODORO · CLASSIC · cycle 2/4" palette={OD.accentRose} />

      <main style={{flex:1, display:'flex', flexDirection:'column', justifyContent:'center', alignItems:'center', gap:24, position:'relative'}}>
        {/* Ring + countdown */}
        <div style={{position:'relative', width:340, height:340, display:'flex', alignItems:'center', justifyContent:'center'}}>
          <svg width="340" height="340" viewBox="0 0 340 340" style={{position:'absolute', inset:0}}>
            <circle cx="170" cy="170" r="160" fill="none" stroke="rgba(240,232,214,0.06)" strokeWidth="2" />
            <circle cx="170" cy="170" r="160" fill="none" stroke={OD.accentRose} strokeWidth="3"
              strokeDasharray={`${2*Math.PI*160*progress} ${2*Math.PI*160}`}
              strokeLinecap="round" transform="rotate(-90 170 170)" />
            {/* tick marks every 5min */}
            {Array.from({length:5}).map((_,i) => {
              const a = -Math.PI/2 + (i+1)/5 * Math.PI * 2;
              return <line key={i} x1={170 + Math.cos(a)*150} y1={170 + Math.sin(a)*150}
                x2={170 + Math.cos(a)*166} y2={170 + Math.sin(a)*166}
                stroke={OD.inkSub} strokeWidth="1" />;
            })}
          </svg>
          <div style={{textAlign:'center'}}>
            <div style={{fontSize:11, letterSpacing:2.5, color:OD.inkDim, marginBottom:4}}>FOCUS</div>
            <div style={{fontFamily:OD.sans, fontWeight:200, fontSize:118, letterSpacing:-5, lineHeight:0.95, fontVariantNumeric:'tabular-nums', color:OD.ink}}>
              {mm}<span className="blink" style={{color:OD.accentRose}}>:</span>{ss}
            </div>
            <div style={{fontSize:11, letterSpacing:2, color:OD.inkSub, marginTop:6}}>
              of 25:00 · break in {mm}:{ss}
            </div>
          </div>
        </div>

        {/* cycle dots */}
        <div style={{display:'flex', gap:12, alignItems:'center'}}>
          {[1,2,3,4].map(i => (
            <div key={i} style={{
              width:10, height:10, borderRadius:10,
              background: i <= 1 ? OD.accentRose : i === 2 ? `${OD.accentRose}55` : 'transparent',
              border: i > 2 ? `1.5px solid ${OD.inkSub}` : 'none',
            }} />
          ))}
          <div style={{fontSize:10, letterSpacing:1.5, color:OD.inkDim, marginLeft:8}}>
            cycle 2 of 4 · long break after #4
          </div>
        </div>

        <div style={{
          fontFamily:OD.sans, fontSize:14, color:OD.inkDim, fontStyle:'italic', textAlign:'center', maxWidth:380, marginTop:14,
        }}>
          "O-Deck install on Pi"
          <div style={{fontFamily:OD.mono, fontSize:10, color:OD.inkSub, marginTop:6, fontStyle:'normal', letterSpacing:1}}>
            notion/cyberdeck · started 9:13 AM
          </div>
        </div>
      </main>

      <ODDock active="POMO" />
    </ODScreen>
  );
}

// ─────────────────────────────────────────────────────────────────
// TRANSIT DETAIL — all 4 stations
// ─────────────────────────────────────────────────────────────────
function TransitApp() {
  const D = window.ODECK_DATA;
  return (
    <ODScreen mode="calm">
      <ODStatusBar app="TRANSIT · LIVE · 4 stations" />

      <main style={{flex:1, display:'grid', gridTemplateColumns:'1fr 1fr', gap:18, minHeight:0, paddingTop:6}}>
        {[...D.transit.stations, ...D.transit.secondary || [
          {name:'14 St–Union Sq', dir:'Downtown', trains:[
            {line:'4', mins:3, color:'#00933C', dest:'Bowling Green', status:'on time', delay:0},
            {line:'5', mins:7, color:'#00933C', dest:'Brooklyn',     status:'on time', delay:0},
            {line:'6', mins:5, color:'#00933C', dest:'Brooklyn Br', status:'+1m delay', delay:1},
            {line:'Q', mins:11, color:'#FCCC0A', dest:'Coney Is',   status:'on time', delay:0},
          ]},
          {name:'W 4 St–Wash Sq', dir:'Downtown', trains:[
            {line:'F', mins:4, color:'#FF6319', dest:'Coney Is',    status:'slow · signals', delay:5},
            {line:'A', mins:8, color:'#0039A6', dest:'Far Rockaway', status:'on time', delay:0},
            {line:'C', mins:12,color:'#0039A6', dest:'Euclid Av',   status:'on time', delay:0},
          ]},
        ]].slice(0,4).map((stn, si) => (
          <div key={si} style={{
            display:'flex', flexDirection:'column', gap:8, minHeight:0,
            paddingRight: si % 2 === 0 ? 18 : 0,
            borderRight: si % 2 === 0 ? `1px solid ${OD.line}` : 'none',
            paddingBottom: si < 2 ? 14 : 0,
            borderBottom: si < 2 ? `1px solid ${OD.line}` : 'none',
            paddingLeft: si % 2 === 1 ? 4 : 0,
          }}>
            <div style={{display:'flex', alignItems:'baseline', justifyContent:'space-between'}}>
              <div>
                <div style={{fontFamily:OD.sans, fontSize:18, fontWeight:500, letterSpacing:-0.3, color:OD.ink}}>
                  {stn.name}
                </div>
                <div style={{fontSize:10, letterSpacing:1.5, color:OD.inkDim, marginTop:2}}>
                  {stn.dir.toUpperCase()} {si < 2 ? '· PRIMARY' : '· SECONDARY · return home'}
                </div>
              </div>
              <span className="live-dot" style={{width:6, height:6, borderRadius:6, background:OD.accentSage}} />
            </div>

            <div style={{display:'flex', flexDirection:'column', gap:4, flex:1, minHeight:0}}>
              {stn.trains.slice(0, si < 2 ? 4 : 3).map((t,i) => (
                <div key={i} style={{display:'flex', alignItems:'center', gap:12, padding:'4px 0'}}>
                  <MTAPill line={t.line} color={t.color} size={26} />
                  <div style={{flex:1, minWidth:0}}>
                    <div style={{fontFamily:OD.sans, fontSize:13, color:OD.ink, fontWeight:500, lineHeight:1.2}}>
                      to {t.dest}
                    </div>
                    <div style={{fontSize:10, color: t.delay > 0 ? OD.accentRose : OD.accentSage, letterSpacing:0.6, marginTop:1}}>
                      {t.status}
                    </div>
                  </div>
                  <div style={{
                    fontFamily:OD.sans, fontWeight:300, fontSize:32, letterSpacing:-1,
                    fontVariantNumeric:'tabular-nums', lineHeight:1, color:OD.ink,
                  }}>
                    {t.mins}<span style={{fontSize:11, color:OD.inkDim, marginLeft:2, fontWeight:400, letterSpacing:0}}>min</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </main>

      <div style={{
        fontSize:10, color:OD.accentRose, letterSpacing:1, padding:'6px 10px',
        background:'rgba(212,154,142,0.10)', border:`1px solid rgba(212,154,142,0.22)`, borderRadius:8,
      }}>! F line: signal delays at Bergen St · expect +3-5 min on Manhattan-bound trains</div>

      <ODDock active="HOME" />
    </ODScreen>
  );
}

// ─────────────────────────────────────────────────────────────────
// CALENDAR — today day-view
// ─────────────────────────────────────────────────────────────────
function CalendarApp() {
  const D = window.ODECK_DATA;
  const hours = ['9 AM','10 AM','11 AM','12 PM','1 PM','2 PM','3 PM','4 PM','5 PM','6 PM','7 PM','8 PM','9 PM'];
  // pixel position helper: hour offset → top
  const slot = 32;
  const startH = 9;
  const eventTop = (time) => {
    const m = time.match(/(\d+):(\d+)/);
    let h = parseInt(m[1]); const min = parseInt(m[2]);
    if (time.includes('PM') || h < 9) h += (h < 9 ? 12 : 0);
    if (time.includes('PM') && h !== 12) h += 0;
    // events use 24h-ish e.g. "12:30", "2:00", "4:30", "7:30" — interpret as PM if before 9
    let h24 = h;
    if (h < 9) h24 = h + 12;
    return (h24 - startH) * slot + (min/60) * slot;
  };
  const eventHeight = (dur) => {
    if (dur.includes('h')) {
      const parts = dur.match(/(\d+)h(?:\s*(\d+)m)?/);
      return (parseInt(parts[1])*60 + (parseInt(parts[2]||'0'))) / 60 * slot;
    }
    return (parseInt(dur)/60) * slot;
  };

  const events = D.calendar.events;
  const nowTop = (11 + 47/60 - startH) * slot;

  return (
    <ODScreen mode="calm">
      <ODStatusBar app="CALENDAR · TODAY · 4 events" />

      <main style={{flex:1, display:'grid', gridTemplateColumns:'1.2fr 1fr', gap:24, minHeight:0, overflow:'hidden'}}>

        {/* day timeline */}
        <div style={{display:'flex', flexDirection:'column', minHeight:0}}>
          <SectionLabel>// SUNDAY · APR 26</SectionLabel>
          <div style={{position:'relative', flex:1, overflow:'hidden'}}>
            {hours.map((h,i) => (
              <div key={i} style={{
                position:'absolute', left:0, right:0, top: i*slot, height: slot,
                display:'flex', alignItems:'flex-start', gap:10,
                borderTop: `1px solid ${OD.line}`,
              }}>
                <span style={{fontSize:9, color:OD.inkSub, letterSpacing:1, paddingTop:3, width:42, fontFamily:OD.mono}}>{h}</span>
              </div>
            ))}

            {/* now line */}
            <div style={{
              position:'absolute', left:42, right:0, top: nowTop, height:1,
              background: OD.accentRose, zIndex:3,
            }}>
              <div style={{
                position:'absolute', left:-6, top:-4, width:8, height:8, borderRadius:8, background:OD.accentRose,
              }} />
              <div style={{
                position:'absolute', right:0, top:-14, fontSize:9, color:OD.accentRose, letterSpacing:1,
                fontFamily:OD.mono, background:OD.bg, padding:'0 6px',
              }}>NOW · 11:47</div>
            </div>

            {/* events */}
            {events.map((e,i) => (
              <div key={i} style={{
                position:'absolute', left:54, right:0,
                top: eventTop(e.time), height: eventHeight(e.dur) - 2,
                background: `${e.color}22`, borderLeft:`3px solid ${e.color}`,
                borderRadius:6, padding:'5px 9px',
                display:'flex', flexDirection:'column', justifyContent:'flex-start',
              }}>
                <div style={{fontFamily:OD.sans, fontSize:13, fontWeight:500, color:OD.ink, lineHeight:1.2}}>
                  {e.title}
                </div>
                <div style={{fontFamily:OD.mono, fontSize:9, color:OD.inkDim, letterSpacing:0.8, marginTop:1}}>
                  {e.time} · {e.dur} · {e.loc.toLowerCase()}
                  {e.notion && <span style={{color:OD.accentSand, marginLeft:6}}>· notion/{e.project}</span>}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* week mini + agenda */}
        <div style={{display:'flex', flexDirection:'column', gap:14, minHeight:0}}>
          <div>
            <SectionLabel>// WEEK</SectionLabel>
            <div style={{display:'grid', gridTemplateColumns:'repeat(7, 1fr)', gap:4}}>
              {['M','T','W','T','F','S','S'].map((d,i) => (
                <div key={i} style={{
                  aspectRatio:'1', display:'flex', flexDirection:'column', alignItems:'center', justifyContent:'center',
                  background: i === 6 ? `${OD.accentRose}1f` : 'rgba(240,232,214,0.04)',
                  border: i === 6 ? `1px solid ${OD.accentRose}55` : `1px solid ${OD.line}`,
                  borderRadius:6,
                }}>
                  <div style={{fontSize:9, color:OD.inkDim, letterSpacing:1}}>{d}</div>
                  <div style={{fontFamily:OD.sans, fontSize:18, fontWeight:i===6?600:400, color: i===6 ? OD.accentRose : OD.ink, fontVariantNumeric:'tabular-nums', letterSpacing:-0.5}}>{20+i}</div>
                  <div style={{display:'flex', gap:1.5, marginTop:1}}>
                    {Array.from({length: [3,2,4,1,5,2,4][i]}).map((_,j) => (
                      <span key={j} style={{width:3, height:3, borderRadius:3, background: i===6 ? OD.accentRose : OD.inkDim}} />
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div style={{flex:1, display:'flex', flexDirection:'column', minHeight:0}}>
            <SectionLabel>// UP NEXT · {D.calendar.nextIn}</SectionLabel>
            <div style={{display:'flex', flexDirection:'column', gap:10, flex:1, minHeight:0}}>
              {events.map((e,i) => (
                <div key={i} style={{
                  display:'grid', gridTemplateColumns:'58px 1fr', gap:12, paddingBottom:10,
                  borderBottom: i < events.length-1 ? `1px dashed ${OD.line}` : 'none',
                }}>
                  <div>
                    <div style={{fontFamily:OD.sans, fontSize:14, fontWeight:500, color:OD.ink, fontVariantNumeric:'tabular-nums', letterSpacing:-0.3}}>{e.time}</div>
                    <div style={{fontSize:9, color:OD.inkSub, letterSpacing:1, fontFamily:OD.mono, marginTop:1}}>{e.dur}</div>
                  </div>
                  <div>
                    <div style={{fontFamily:OD.sans, fontSize:13, fontWeight:500, color:OD.ink, lineHeight:1.2}}>{e.title}</div>
                    <div style={{fontSize:10, color:OD.inkDim, marginTop:2, letterSpacing:0.4}}>
                      {e.loc.toLowerCase()}
                      {e.notion && <div style={{
                        display:'inline-block', marginLeft:6, color:OD.accentSand,
                      }}>· notion/{e.project} · status: in progress</div>}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </main>

      <ODDock active="HOME" />
    </ODScreen>
  );
}

window.PomoApp = PomoApp;
window.TransitApp = TransitApp;
window.CalendarApp = CalendarApp;
