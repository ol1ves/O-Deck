// Fullscreen apps batch 2: GitHub, Doomscroll, Photo frame, Showcase, Subway map, Diagnostics

// ─────────────────────────────────────────────────────────────────
// GITHUB — recent commits, PRs, issues
// ─────────────────────────────────────────────────────────────────
function GitHubApp() {
  const commits = [
    {repo:'cyberdeck',  msg:'transit: handle GTFS feed reconnect',     time:'24m', sha:'a3f2c1', plus:42, minus:8},
    {repo:'cyberdeck',  msg:'pomodoro: persist preset across reload',  time:'1h',  sha:'b81e4d', plus:18, minus:3},
    {repo:'dotfiles',   msg:'add wezterm split bindings',              time:'3h',  sha:'9c2a17', plus:6,  minus:2},
    {repo:'cyberdeck',  msg:'rss: dedupe by canonical url',            time:'5h',  sha:'2d4f88', plus:23, minus:11},
    {repo:'odeck-ui',   msg:'home: tighten transit grid',              time:'8h',  sha:'7e1baf', plus:31, minus:14},
    {repo:'cyberdeck',  msg:'wip: showcase shader fragment',           time:'1d',  sha:'5b9c33', plus:64, minus:0},
  ];
  const prs = [
    {repo:'cyberdeck', title:'feat: notion ↔ google calendar join', num:42, status:'open',   age:'2d'},
    {repo:'odeck-ui',  title:'fix: tile staleness indicator',       num:18, status:'review', age:'5h'},
  ];
  const issues = [
    {repo:'cyberdeck', title:'F train delay banner overflows on 800×480', num:12, age:'1d', label:'bug'},
    {repo:'cyberdeck', title:'Pomodoro chime volume too quiet at default', num:9, age:'3d', label:'audio'},
    {repo:'odeck-ui',  title:'Showcase mode: add palette presets', num:21, age:'4d', label:'feat'},
    {repo:'cyberdeck', title:'Calendar: timezone bug crossing DST', num:7, age:'1w', label:'bug'},
  ];

  return (
    <ODScreen mode="calm">
      <ODStatusBar app="GITHUB · @oliver-s" />

      <main style={{flex:1, display:'grid', gridTemplateColumns:'1.4fr 1fr', gap:24, minHeight:0}}>
        {/* commits column */}
        <div style={{display:'flex', flexDirection:'column', minHeight:0, gap:12}}>
          <div>
            <SectionLabel>// HEARTBEAT · 7d</SectionLabel>
            <div style={{display:'flex', alignItems:'flex-end', gap:2, height:34}}>
              {Array.from({length:7*8}).map((_,i) => {
                const v = Math.max(0.05, Math.exp(-Math.pow((i%8 - 4)/3, 2)) * (0.4 + Math.random()*0.6));
                return <div key={i} style={{
                  flex:1, height:`${v*34}px`,
                  background: i > 7*8-9 ? OD.accentSage : `${OD.accentSage}55`,
                  borderRadius:1.5,
                }} />;
              })}
            </div>
          </div>

          <div style={{flex:1, display:'flex', flexDirection:'column', minHeight:0}}>
            <SectionLabel>// RECENT COMMITS</SectionLabel>
            <div style={{display:'flex', flexDirection:'column', gap:9, flex:1, minHeight:0}}>
              {commits.map((c,i) => (
                <div key={i} style={{display:'grid', gridTemplateColumns:'auto 1fr auto', gap:12, alignItems:'flex-start', paddingBottom:9, borderBottom: i < commits.length-1 ? `1px dashed ${OD.line}` : 'none'}}>
                  <span style={{fontFamily:OD.mono, fontSize:10, color:OD.accentSand, letterSpacing:0.5, marginTop:2}}>
                    {c.sha}
                  </span>
                  <div style={{minWidth:0}}>
                    <div style={{fontFamily:OD.sans, fontSize:13, color:OD.ink, lineHeight:1.25}}>{c.msg}</div>
                    <div style={{fontFamily:OD.mono, fontSize:9, color:OD.inkDim, letterSpacing:0.8, marginTop:2}}>
                      <span style={{color:OD.accentSage}}>+{c.plus}</span> <span style={{color:OD.accentRose}}>−{c.minus}</span> · {c.repo} · {c.time} ago
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* right column: PRs + issues */}
        <div style={{display:'flex', flexDirection:'column', gap:14, minHeight:0}}>
          <div>
            <SectionLabel>// OPEN PRs · {prs.length}</SectionLabel>
            <div style={{display:'flex', flexDirection:'column', gap:9}}>
              {prs.map((p,i) => (
                <div key={i} style={{display:'flex', alignItems:'flex-start', gap:10}}>
                  <span style={{
                    fontFamily:OD.mono, fontSize:9, letterSpacing:0.6,
                    color: p.status === 'review' ? OD.accentSand : OD.accentSage,
                    background: p.status === 'review' ? `${OD.accentSand}1f` : `${OD.accentSage}1f`,
                    padding:'3px 7px', borderRadius:5, marginTop:1,
                  }}>{p.status}</span>
                  <div style={{flex:1, minWidth:0}}>
                    <div style={{fontFamily:OD.sans, fontSize:12.5, color:OD.ink, lineHeight:1.3}}>{p.title}</div>
                    <div style={{fontSize:9, color:OD.inkSub, letterSpacing:0.7, marginTop:2}}>#{p.num} · {p.repo} · {p.age}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div style={{flex:1, display:'flex', flexDirection:'column', minHeight:0}}>
            <SectionLabel>// ASSIGNED ISSUES · {issues.length}</SectionLabel>
            <div style={{display:'flex', flexDirection:'column', gap:9}}>
              {issues.map((iss,i) => (
                <div key={i} style={{display:'flex', alignItems:'flex-start', gap:10}}>
                  <span style={{
                    fontFamily:OD.mono, fontSize:9, letterSpacing:0.6,
                    color: iss.label === 'bug' ? OD.accentRose : iss.label === 'feat' ? OD.accentLav : OD.accentSand,
                    background: iss.label === 'bug' ? `${OD.accentRose}1f` : iss.label === 'feat' ? `${OD.accentLav}1f` : `${OD.accentSand}1f`,
                    padding:'3px 7px', borderRadius:5, marginTop:1,
                  }}>{iss.label}</span>
                  <div style={{flex:1, minWidth:0}}>
                    <div style={{fontFamily:OD.sans, fontSize:12, color:OD.ink, lineHeight:1.3}}>{iss.title}</div>
                    <div style={{fontSize:9, color:OD.inkSub, letterSpacing:0.7, marginTop:2}}>#{iss.num} · {iss.repo} · {iss.age}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </main>

      <ODDock active="GH" />
    </ODScreen>
  );
}

// ─────────────────────────────────────────────────────────────────
// DOOMSCROLL — RSS list w/ active QR
// ─────────────────────────────────────────────────────────────────
function DoomApp() {
  // Fake QR — pseudo-random module pattern, deterministic per "url"
  const QR = ({size = 220, seed = 0}) => {
    const cells = 25;
    const out = [];
    let s = seed;
    const rng = () => { s = (s * 9301 + 49297) % 233280; return s / 233280; };
    for (let y = 0; y < cells; y++) for (let x = 0; x < cells; x++) {
      // finder patterns
      const corner = (x < 7 && y < 7) || (x >= cells-7 && y < 7) || (x < 7 && y >= cells-7);
      const inner =
        (x < 7 && y < 7 && (x === 0 || x === 6 || y === 0 || y === 6 || (x>=2 && x<=4 && y>=2 && y<=4))) ||
        (x >= cells-7 && y < 7 && (x === cells-7 || x === cells-1 || y === 0 || y === 6 || (x>=cells-5 && x<=cells-3 && y>=2 && y<=4))) ||
        (x < 7 && y >= cells-7 && (x === 0 || x === 6 || y === cells-7 || y === cells-1 || (x>=2 && x<=4 && y>=cells-5 && y<=cells-3)));
      const fill = corner ? inner : rng() > 0.55;
      if (fill) out.push(<rect key={`${x}-${y}`} x={x} y={y} width={1} height={1} fill={OD.ink} />);
    }
    return (
      <svg width={size} height={size} viewBox={`0 0 ${cells} ${cells}`} style={{
        background:OD.ink === '#f0e8d6' ? '#f5ecd6' : '#fff', borderRadius:8, padding:0,
      }}>
        <rect x="0" y="0" width={cells} height={cells} fill="#f5ecd6" />
        {out}
      </svg>
    );
  };

  const stories = [
    {src:'TLDR', title:'Apple unveils on-device LLM runtime for iOS 19', age:'12m', summary:'New CoreML primitives for streaming inference; 4-bit quantization native.', selected:true},
    {src:'HN',   title:'Show HN: A 50-line distributed lock manager', age:'38m',  summary:'Built on Postgres advisory locks. Author benchmarks 10k QPS.', selected:false},
    {src:'r/nyc',title:'L train weekend service back to normal',         age:'1h',   summary:'After 6 weeks of slow zones; MTA crews finished tie replacement.', selected:false},
    {src:'YT',   title:'Veritasium: The most useless machine ever built', age:'3h',  summary:'A 30-minute tour of mechanical absurdity.', selected:false},
    {src:'TLDR', title:'Anthropic publishes update to Claude 4 model card', age:'5h', summary:'Adds details on long-context evals and safety mitigations.', selected:false},
  ];
  const selected = stories.find(s => s.selected);

  return (
    <ODScreen mode="calm">
      <ODStatusBar app="DOOMSCROLL · 5 unread · all sources" />

      <main style={{flex:1, display:'grid', gridTemplateColumns:'1fr 320px', gap:24, minHeight:0}}>
        <div style={{display:'flex', flexDirection:'column', gap:8, minHeight:0, overflow:'hidden'}}>
          <SectionLabel>// FEED</SectionLabel>
          <div style={{display:'flex', flexDirection:'column', gap:10, flex:1, minHeight:0}}>
            {stories.map((s,i) => (
              <div key={i} style={{
                display:'grid', gridTemplateColumns:'48px 1fr auto', gap:12, alignItems:'flex-start',
                padding:'8px 10px', borderRadius:8,
                background: s.selected ? `${OD.accentSand}10` : 'transparent',
                border: s.selected ? `1px solid ${OD.accentSand}33` : `1px solid transparent`,
              }}>
                <span style={{fontFamily:OD.mono, fontSize:9, color:s.selected ? OD.accentSand : OD.accentRose, letterSpacing:1, marginTop:2}}>{s.src}</span>
                <div style={{minWidth:0}}>
                  <div style={{fontFamily:OD.sans, fontSize:13.5, color:OD.ink, lineHeight:1.3, fontWeight: s.selected ? 500 : 400}}>{s.title}</div>
                  <div style={{fontFamily:OD.sans, fontSize:11, color:OD.inkDim, marginTop:3, lineHeight:1.4}}>{s.summary}</div>
                </div>
                <span style={{fontSize:9, color:OD.inkSub, letterSpacing:0.8, fontFamily:OD.mono, marginTop:2}}>{s.age}</span>
              </div>
            ))}
          </div>
        </div>

        <aside style={{display:'flex', flexDirection:'column', gap:10, minHeight:0, paddingLeft:18, borderLeft:`1px solid ${OD.line}`}}>
          <SectionLabel accent={OD.accentSand}>// READ ON PHONE</SectionLabel>
          <QR size={240} seed={42} />
          <div style={{fontFamily:OD.sans, fontSize:13, color:OD.ink, fontWeight:500, lineHeight:1.3, marginTop:4}}>
            {selected.title}
          </div>
          <div style={{fontFamily:OD.mono, fontSize:9, color:OD.inkDim, letterSpacing:0.8, lineHeight:1.5}}>
            scan with phone camera{'\n'}
            {selected.src.toLowerCase()}.com/…/article
          </div>
          <div style={{flex:1}} />
          <div style={{fontSize:10, color:OD.inkSub, letterSpacing:1, lineHeight:1.4, fontFamily:OD.mono}}>
            tap any story above{'\n'}to load its QR code
          </div>
        </aside>
      </main>

      <ODDock active="DOOM" />
    </ODScreen>
  );
}

// ─────────────────────────────────────────────────────────────────
// PHOTO FRAME — single image, slow-rotate, minimal chrome
// ─────────────────────────────────────────────────────────────────
function PhotoApp() {
  return (
    <div className="odeck-screen" style={{
      background: '#0a0908', position:'relative', overflow:'hidden',
      fontFamily: OD.mono, color: OD.ink,
    }}>
      {/* Placeholder photo — striped warm gradient */}
      <div style={{
        position:'absolute', inset:0,
        background: `
          repeating-linear-gradient(118deg, rgba(255,255,255,0.02) 0 2px, transparent 2px 8px),
          radial-gradient(70% 60% at 30% 40%, #d49a8e 0%, transparent 60%),
          radial-gradient(60% 80% at 70% 80%, #7a5f4a 0%, transparent 60%),
          linear-gradient(180deg, #c8a377 0%, #6b4838 100%)
        `,
      }}>
        {/* placeholder caption */}
        <div style={{
          position:'absolute', bottom:16, left:'50%', transform:'translateX(-50%)',
          fontFamily: OD.mono, fontSize:10, color:'rgba(255,255,255,0.55)', letterSpacing:2,
          padding:'4px 10px',
          background:'rgba(0,0,0,0.25)', borderRadius:4, backdropFilter:'blur(6px)',
        }}>[ photo · prospect park · oct 2024 ]</div>
      </div>

      {/* minimal chrome */}
      <div style={{
        position:'absolute', top:14, left:18, right:18,
        display:'flex', justifyContent:'space-between', alignItems:'center',
        fontFamily:OD.mono, fontSize:9, color:'rgba(255,255,255,0.55)', letterSpacing:1.5,
      }}>
        <span>O—DECK / PHOTO · iCloud Shared</span>
        <span>3 of 47 · auto-rotate 30s · ◐</span>
      </div>

      {/* rotation progress */}
      <div style={{
        position:'absolute', bottom:0, left:0, height:1, width:'34%',
        background: 'rgba(255,255,255,0.4)',
      }} />
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────
// SHOWCASE — full-bleed generative
// ─────────────────────────────────────────────────────────────────
function ShowcaseApp({ mode = 'music' }) {
  const palette = mode === 'music'
    ? [OD.accentLav, OD.accentRose, OD.accentSand, '#7a90a8', '#a8c19a']
    : [OD.accentSand, OD.accentSage, '#7a5f4a', '#5a6a78', OD.accentRose];

  return (
    <div className="odeck-screen" style={{
      background:'#0c0a08', position:'relative', overflow:'hidden',
      fontFamily:OD.mono, color:OD.ink,
    }}>
      <DriftOrbs palette={palette} mode={mode} count={10} />
      <Grain />

      {/* whisper-quiet identifier in corner */}
      <div style={{
        position:'absolute', bottom:14, right:18,
        fontFamily:OD.mono, fontSize:9, color:'rgba(240,232,214,0.35)', letterSpacing:2,
      }}>SHOWCASE · {mode.toUpperCase()} · tap to return</div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────
// SUBWAY MAP — abstract live map
// ─────────────────────────────────────────────────────────────────
function SubwayApp() {
  // Original abstracted line diagram, not a recreation of the MTA map.
  // Three colored ribbons running diagonally, nodes for stations, animated dots for trains.
  const lines = [
    {color:'#0039A6', label:'A/C', y:130},
    {color:'#FF6319', label:'F',   y:200},
    {color:'#FCCC0A', label:'Q/R', y:270},
    {color:'#00933C', label:'4/5/6', y:340},
  ];

  return (
    <ODScreen mode="calm">
      <ODStatusBar app="SUBWAY · LIVE · GTFS-RT" />

      <main style={{flex:1, position:'relative', minHeight:0}}>
        <SectionLabel>// MTA · 142 trains tracked</SectionLabel>

        <svg viewBox="0 0 920 420" style={{width:'100%', height:'100%'}}>
          {/* lines */}
          {lines.map((l,i) => (
            <g key={i}>
              <path d={`M 60 ${l.y} Q ${300} ${l.y - 20} 460 ${l.y} T 860 ${l.y}`}
                stroke={l.color} strokeWidth="6" fill="none" strokeLinecap="round" opacity="0.9" />
              <text x="20" y={l.y + 5} fill={OD.ink} fontSize="13" fontFamily={OD.mono} letterSpacing="1">{l.label}</text>
            </g>
          ))}

          {/* stations as nodes */}
          {[120, 240, 360, 480, 600, 720, 820].map((x, xi) => (
            <g key={xi}>
              {lines.map((l, li) => (
                <circle key={li} cx={x} cy={l.y + (Math.sin((xi+li)*0.7) * 6)}
                  r={xi === 3 ? 8 : 4} fill={OD.bg} stroke={l.color} strokeWidth="2" />
              ))}
            </g>
          ))}

          {/* labeled stations (vertical text) */}
          {[
            {x:120, label:'High St'},
            {x:240, label:'Jay St'},
            {x:360, label:'Court St'},
            {x:480, label:'DeKalb'},
            {x:600, label:'Atlantic'},
            {x:720, label:'14 St'},
            {x:820, label:'W 4 St'},
          ].map((s, i) => (
            <text key={i} x={s.x} y={70} fill={OD.inkDim} fontSize="10" fontFamily={OD.mono} textAnchor="middle" letterSpacing="0.5">{s.label}</text>
          ))}

          {/* live train markers (positions interpolated) */}
          {lines.map((l,i) => (
            <g key={'t-'+i}>
              <circle cx={180 + i*40} cy={l.y - 1} r="6" fill={OD.ink} stroke={l.color} strokeWidth="2.5">
                <animate attributeName="cx" from={180 + i*40} to={780 + i*15} dur={`${30 + i*8}s`} repeatCount="indefinite" />
              </circle>
              <circle cx={420 + i*30} cy={l.y - 1} r="6" fill={OD.ink} stroke={l.color} strokeWidth="2.5">
                <animate attributeName="cx" from={420 + i*30} to={120 + i*15} dur={`${28 + i*5}s`} repeatCount="indefinite" />
              </circle>
            </g>
          ))}

          {/* "you are here" marker on Jay St */}
          <g>
            <circle cx="240" cy="200" r="14" fill="none" stroke={OD.accentSand} strokeWidth="2">
              <animate attributeName="r" from="10" to="22" dur="2.5s" repeatCount="indefinite" />
              <animate attributeName="opacity" from="0.9" to="0" dur="2.5s" repeatCount="indefinite" />
            </circle>
            <circle cx="240" cy="200" r="6" fill={OD.accentSand} />
            <text x="240" y="395" fill={OD.accentSand} fontSize="11" fontFamily={OD.mono} textAnchor="middle" letterSpacing="1.5">YOU · JAY ST</text>
          </g>
        </svg>
      </main>

      <div style={{display:'flex', gap:18, fontFamily:OD.mono, fontSize:10, letterSpacing:1, color:OD.inkDim}}>
        <span><span style={{color:OD.accentSage}}>●</span> on time · 134</span>
        <span><span style={{color:OD.accentRose}}>●</span> delayed · 8</span>
        <span style={{color:OD.inkSub}}>tap a station for arrivals</span>
      </div>

      <ODDock active="MAP" />
    </ODScreen>
  );
}

// ─────────────────────────────────────────────────────────────────
// DIAGNOSTICS — per-integration status
// ─────────────────────────────────────────────────────────────────
function DiagApp() {
  const integrations = [
    {name:'weather',  prov:'open-meteo',   status:'ok', last:'12s ago', errs:0,  ms:184},
    {name:'transit',  prov:'mta gtfs-rt',  status:'ok', last:'8s ago',  errs:0,  ms:421},
    {name:'calendar', prov:'google+notion',status:'ok', last:'46s ago', errs:0,  ms:912},
    {name:'spotify',  prov:'web api',      status:'ok', last:'4s ago',  errs:0,  ms:312},
    {name:'github',   prov:'rest api',     status:'warn',last:'2m ago', errs:1,  ms:1240},
    {name:'rss',      prov:'feedparser',   status:'ok', last:'1m ago',  errs:0,  ms:602},
    {name:'photos',   prov:'icloud share', status:'ok', last:'14m ago', errs:0,  ms:88},
  ];

  return (
    <ODScreen mode="calm" orbs={false}>
      <ODStatusBar app="DIAGNOSTICS · /diagnostics" />

      <main style={{flex:1, display:'grid', gridTemplateColumns:'1.3fr 1fr', gap:24, minHeight:0}}>
        <div style={{display:'flex', flexDirection:'column', gap:8, minHeight:0}}>
          <SectionLabel>// INTEGRATIONS</SectionLabel>
          <div style={{display:'flex', flexDirection:'column', gap:0}}>
            <div style={{
              display:'grid', gridTemplateColumns:'1.4fr 1.4fr 70px 1fr 60px 70px', gap:10,
              fontFamily:OD.mono, fontSize:9, letterSpacing:1.2, color:OD.inkSub, paddingBottom:6,
              borderBottom:`1px solid ${OD.line}`,
            }}>
              <span>NAME</span><span>PROVIDER</span><span>STATUS</span><span>LAST FETCH</span><span>ERRS</span><span>MS</span>
            </div>
            {integrations.map((it,i) => (
              <div key={i} style={{
                display:'grid', gridTemplateColumns:'1.4fr 1.4fr 70px 1fr 60px 70px', gap:10, padding:'9px 0',
                borderBottom: i < integrations.length-1 ? `1px dashed ${OD.line}` : 'none',
                fontFamily:OD.mono, fontSize:11, letterSpacing:0.5, color:OD.ink, alignItems:'center',
              }}>
                <span>{it.name}</span>
                <span style={{color:OD.inkDim}}>{it.prov}</span>
                <span style={{color: it.status === 'ok' ? OD.accentSage : OD.accentRose}}>
                  ● {it.status}
                </span>
                <span style={{color:OD.inkDim}}>{it.last}</span>
                <span style={{color: it.errs > 0 ? OD.accentRose : OD.inkSub, fontVariantNumeric:'tabular-nums'}}>{it.errs}</span>
                <span style={{color:OD.inkDim, fontVariantNumeric:'tabular-nums'}}>{it.ms}</span>
              </div>
            ))}
          </div>
        </div>

        <div style={{display:'flex', flexDirection:'column', gap:14, minHeight:0}}>
          <div>
            <SectionLabel>// SYSTEM</SectionLabel>
            <div style={{display:'flex', flexDirection:'column', gap:8, fontFamily:OD.mono, fontSize:11}}>
              {[
                ['cpu',     '8%',  0.08, OD.accentSage],
                ['ram',     '42%', 0.42, OD.accentSage],
                ['disk',    '28%', 0.28, OD.accentSage],
                ['temp',    '54°C', 0.54, OD.accentSand],
                ['uptime',  '4d 11h 32m', 0, OD.inkDim],
                ['load',    '0.42 0.51 0.48', 0, OD.inkDim],
              ].map(([k,v,p,c],i) => (
                <div key={i} style={{display:'grid', gridTemplateColumns:'58px 1fr auto', gap:10, alignItems:'center'}}>
                  <span style={{color:OD.inkDim, letterSpacing:1}}>{k}</span>
                  <span style={{color:c}}>{p > 0 ? <BlockBar value={p} width={18} /> : <span style={{color:OD.inkSub}}>—</span>}</span>
                  <span style={{color:OD.ink, fontVariantNumeric:'tabular-nums'}}>{v}</span>
                </div>
              ))}
            </div>
          </div>

          <div style={{flex:1, minHeight:0, display:'flex', flexDirection:'column'}}>
            <SectionLabel>// LOG TAIL</SectionLabel>
            <div style={{
              fontFamily:OD.mono, fontSize:10, color:OD.inkDim, letterSpacing:0.3, lineHeight:1.7,
              flex:1, overflow:'hidden',
            }}>
              <div><span style={{color:OD.accentSage}}>11:47:02</span> transit fetch ok · 4 stations · 421ms</div>
              <div><span style={{color:OD.accentSage}}>11:46:54</span> spotify track change → "Pyramid Song"</div>
              <div><span style={{color:OD.accentRose}}>11:46:31</span> github 502 → retry in 8s</div>
              <div><span style={{color:OD.accentSage}}>11:46:30</span> calendar fetch ok · 4 events · 912ms</div>
              <div><span style={{color:OD.accentSage}}>11:46:12</span> rss fetch ok · 23 items · 602ms</div>
              <div><span style={{color:OD.accentSand}}>11:46:00</span> ws client connected · 1 frontend</div>
              <div><span style={{color:OD.accentSage}}>11:45:48</span> weather fetch ok · 184ms</div>
              <div><span style={{color:OD.accentSage}}>11:45:30</span> transit fetch ok · 4 stations · 388ms</div>
            </div>
          </div>
        </div>
      </main>

      <ODDock />
    </ODScreen>
  );
}

window.GitHubApp = GitHubApp;
window.DoomApp = DoomApp;
window.PhotoApp = PhotoApp;
window.ShowcaseApp = ShowcaseApp;
window.SubwayApp = SubwayApp;
window.DiagApp = DiagApp;
