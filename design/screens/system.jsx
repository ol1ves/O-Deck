// O-Deck design system tokens — shared across all screens (home + fullscreen apps).
// Mirrors C v3 ("Atelier"): paper-dark, two-accent (sand + sage + rose), monospace+Inter.

window.OD = {
  // colors
  bg:        '#15130f',
  bgRaised:  'rgba(31,28,24,0.78)',
  bgSolid:   '#1f1c18',
  ink:       '#f0e8d6',
  inkDim:    'rgba(240,232,214,0.55)',
  inkSub:    'rgba(240,232,214,0.32)',
  accentSand:'#e6c89b',
  accentSage:'#a8c19a',
  accentRose:'#d49a8e',
  accentLav: '#a08fb3',
  line:      'rgba(240,232,214,0.08)',

  // type
  mono: "'IBM Plex Mono', monospace",
  sans: "'Inter', system-ui, sans-serif",
};

// Section label component used everywhere
function SectionLabel({ children, accent }) {
  return (
    <div style={{
      display:'flex', alignItems:'center', gap:8, marginBottom:9,
      fontFamily: OD.mono, fontSize:10, letterSpacing:1.5, color: accent || OD.inkDim,
    }}>
      <span style={{flex:'0 0 auto'}}>{children}</span>
      <span style={{flex:1, height:1, background: OD.line}} />
    </div>
  );
}

// Header strip used on every fullscreen app
function ODStatusBar({ app, palette }) {
  const D = window.ODECK_DATA;
  const accent = palette || OD.accentSand;
  return (
    <header style={{
      display:'flex', alignItems:'center', justifyContent:'space-between',
      fontSize:10, letterSpacing:1.5, color: OD.inkDim, fontFamily: OD.mono,
      paddingBottom: 10, borderBottom:`1px solid ${OD.line}`, position:'relative', zIndex:2,
    }}>
      <div style={{display:'flex', gap:18, alignItems:'center'}}>
        <span style={{color: OD.ink, fontWeight:500}}>O—DECK</span>
        <span style={{color: OD.inkSub}}>/{D.device.callsign}</span>
        {app && <>
          <span style={{color: OD.inkSub}}>›</span>
          <span style={{color: accent, letterSpacing:1.8}}>{app}</span>
        </>}
        <span><span style={{color: OD.accentSage}}>●</span> {D.status.host}</span>
        <span style={{color: OD.inkDim}}>cpu <span style={{color: OD.accentSage}}><BlockBar value={D.status.cpu/100} width={6} /></span> {D.status.cpu}%</span>
      </div>
      <div style={{display:'flex', gap:14}}>
        <span style={{color: OD.inkSub}}>{D.status.wifi}</span>
        <span style={{color: OD.accentSand}}>{D.time.date} · {D.time.tz}</span>
      </div>
    </header>
  );
}

// Reusable bottom dock (small launcher icons)
function ODDock({ active }) {
  const items = [
    {k:'HOME', g:'⌂'},
    {k:'POMO', g:'◑'},
    {k:'GH',   g:'◇'},
    {k:'MAP',  g:'▤'},
    {k:'DOOM', g:'□'},
    {k:'PHOTO',g:'◐'},
    {k:'SHOW', g:'✦'},
  ];
  return (
    <footer style={{
      display:'flex', gap:14, alignItems:'center',
      paddingTop:10, borderTop:`1px solid ${OD.line}`,
      fontFamily: OD.mono, fontSize:10, letterSpacing:1.5, color: OD.inkDim,
    }}>
      {items.map(({k,g}, i) => (
        <span key={i} style={{
          display:'inline-flex', gap:5, alignItems:'center',
          color: active === k ? OD.ink : OD.inkDim,
        }}>
          <span style={{
            width:5, height:5, borderRadius:5,
            background: active === k ? OD.accentSand : 'rgba(240,232,214,0.25)',
          }} />
          <span style={{color: active === k ? OD.accentSand : OD.inkDim, marginRight:2}}>{g}</span>
          {k}
        </span>
      ))}
      <span style={{flex:1}} />
      <span style={{color: OD.inkSub}}>tap <span style={{color: OD.accentSand}}>⌂</span> for home</span>
    </footer>
  );
}

// Screen frame — every fullscreen app uses this
function ODScreen({ children, mode = 'calm', orbs = true }) {
  const orbPalette = {
    calm:    [OD.accentSand, OD.accentSage, '#7a5f4a', '#5a6a78'],
    music:   [OD.accentLav, OD.accentRose, OD.accentSand, '#7a90a8'],
    rain:    ['#5a7088', '#7a90a8', '#3e556a', OD.accentSage],
    thunder: ['#c8b89a', '#7a6a8a', '#3e3a4a', OD.accentRose],
  }[mode] || [OD.accentSand, OD.accentSage];

  return (
    <div className="odeck-screen" style={{
      background: OD.bg, color: OD.ink, fontFamily: OD.mono,
      position:'relative', overflow:'hidden', padding:'16px 22px',
      display:'flex', flexDirection:'column', gap:10,
    }}>
      {orbs && <DriftOrbs palette={orbPalette} mode={mode} count={6} />}
      {orbs && <Grain />}
      <div style={{position:'relative', zIndex:1, display:'flex', flexDirection:'column', gap:10, height:'100%'}}>
        {children}
      </div>
    </div>
  );
}

Object.assign(window, { SectionLabel, ODStatusBar, ODDock, ODScreen });
