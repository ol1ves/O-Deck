// Shared mock data for the O-Deck home-screen explorations.
// Same content across variations so aesthetic differences are isolated.

const ODECK_DATA = {
  device: { name: 'O-DECK', callsign: 'OD-04', host: 'odeck.local' },
  time: { hh: '11', mm: '47', ampm: 'AM', date: 'SUN · APR 26', tz: 'EDT' },
  weather: {
    tempF: 58,
    cond: 'Partly cloudy',
    icon: 'cloud-sun',
    high: 64, low: 49,
    feelsLike: 56,
    alerts: [], // could include {type:'rain', label:'Light rain · 4pm'}
    hourly: [
      { h: '12', t: 60 }, { h: '1', t: 62 }, { h: '2', t: 64 },
      { h: '3', t: 63 }, { h: '4', t: 61 }, { h: '5', t: 58 },
    ],
  },
  transit: {
    stations: [
      { name: 'Jay St–MetroTech', dir: 'Uptown', trains: [
        { line: 'A', mins: 2, color: '#0039A6', dest: 'Inwood',       status: 'on time',           delay: 0 },
        { line: 'C', mins: 6, color: '#0039A6', dest: '168 St',       status: '+2m delay',         delay: 2 },
        { line: 'F', mins: 9, color: '#FF6319', dest: 'Forest Hills', status: 'slow · signals',    delay: 4 },
        { line: 'R', mins: 14, color: '#FCCC0A', dest: 'Forest Hills',status: 'on time',           delay: 0 },
      ]},
      { name: 'DeKalb Av', dir: 'Uptown', trains: [
        { line: 'Q', mins: 4, color: '#FCCC0A', dest: '96 St',        status: 'on time',           delay: 0 },
      ]},
    ],
    alert: 'F: delays at Bergen St',
  },
  calendar: {
    events: [
      { time: '12:30', dur: '30m', title: 'Lunch w/ Maya', loc: 'Devoción', notion: false, color: '#9bb38b' },
      { time: '2:00',  dur: '1h',  title: 'O-Deck install on Pi', loc: 'Desk', notion: true, project: 'cyberdeck', color: '#c9a26f' },
      { time: '4:30',  dur: '45m', title: 'Yoga · Y7', loc: 'Williamsburg', notion: false, color: '#7a9aa8' },
      { time: '7:30',  dur: '2h',  title: 'Dinner @ Thai Diner', loc: 'Nolita', notion: false, color: '#b48a7a' },
    ],
    nextIn: '43 min',
  },
  nowPlaying: {
    track: 'Pyramid Song',
    artist: 'Radiohead',
    album: 'Amnesiac',
    progress: 0.34,
    elapsed: '1:54',
    total: '4:50',
    // ambient color extracted from "art"
    palette: { dom: '#6b5a8a', accent: '#c9a36c', ink: '#f5efe6' },
  },
  rss: {
    ticker: [
      'TLDR · Apple unveils on-device LLM API for iOS 19',
      'HN · Show HN: A 50-line distributed lock manager',
      'r/nyc · L train weekend service back to normal',
      'YT · Veritasium: The most useless machine ever built',
      'TLDR · Anthropic publishes update to Claude 4 model card',
      'HN · Why is everyone suddenly using Bun?',
    ],
    headlines: [
      { src: 'TLDR', title: 'Apple unveils on-device LLM runtime for iOS 19', age: '12m' },
      { src: 'HN',   title: 'Show HN: A 50-line distributed lock manager', age: '38m' },
      { src: 'r/nyc',title: 'L train weekend service back to normal', age: '1h' },
    ],
  },
  github: { commits: 7, prs: 2, issues: 4 },
  status: { wifi: 'home-5G', ip: '10.0.0.42', uptime: '4d 11h', cpu: 8, ram: 'OK' },
};

window.ODECK_DATA = ODECK_DATA;

// Common helpers ─────────────────────────────────────────────
function MTAPill({ line, color, size = 22, ink = '#fff' }) {
  // Single-letter rounded square pill, matches MTA conventions in shape
  // (color is data; we don't recreate proprietary type).
  const isYellow = ['N','Q','R','W'].includes(line);
  const fg = isYellow ? '#1a1a1a' : ink;
  return (
    <span style={{
      display:'inline-flex', alignItems:'center', justifyContent:'center',
      width:size, height:size, borderRadius:size/2, background:color,
      color:fg, fontWeight:700, fontSize:size*0.55, fontFamily:'Inter, sans-serif',
      letterSpacing:0,
    }}>{line}</span>
  );
}

function WeatherIcon({ kind = 'cloud-sun', size = 28, stroke = 'currentColor' }) {
  const s = size, sw = 1.6;
  if (kind === 'cloud-sun') return (
    <svg width={s} height={s} viewBox="0 0 32 32" fill="none" stroke={stroke} strokeWidth={sw} strokeLinecap="round" strokeLinejoin="round">
      <circle cx="11" cy="11" r="4" />
      <path d="M11 3v2M11 17v2M3 11h2M17 11h2M5.5 5.5l1.4 1.4M15.1 15.1l1.4 1.4M5.5 16.5l1.4-1.4M15.1 6.9l1.4-1.4" />
      <path d="M14 22h10a4 4 0 1 0-1.2-7.8A6 6 0 0 0 11 17a4 4 0 0 0 3 5z" />
    </svg>
  );
  return null;
}

function EQBars({ count = 5, color = 'currentColor', size = 14, gap = 2, width = 2 }) {
  return (
    <span style={{display:'inline-flex', alignItems:'flex-end', gap, height:size}}>
      {Array.from({length:count}).map((_,i) => (
        <span key={i} className="eq-bar" style={{
          width, height:size, background:color, borderRadius:1,
          animationDelay: `${i*0.13}s`,
        }} />
      ))}
    </span>
  );
}

function Ticker({ items, color = 'currentColor', opacity = 0.7, fontSize = 13, monospace = false }) {
  // Render the list twice for seamless loop
  const seq = [...items, ...items];
  return (
    <div style={{overflow:'hidden', whiteSpace:'nowrap', maskImage:'linear-gradient(90deg, transparent, #000 4%, #000 96%, transparent)'}}>
      <div className="ticker-track" style={{
        display:'inline-flex', gap:48, opacity, fontSize,
        fontFamily: monospace ? "'JetBrains Mono', monospace" : 'inherit',
        color, letterSpacing: monospace ? 0 : 0.1,
      }}>
        {seq.map((s,i) => <span key={i}>· {s}</span>)}
      </div>
    </div>
  );
}

// Fake album art — color-block composition tied to nowPlaying.palette.
// Gives us "ambient color extraction" for free without needing a real image.
function AlbumArt({ palette, size = 220, label = 'AMNESIAC', glyph = '◊' }) {
  const { dom, accent, ink } = palette;
  return (
    <div style={{
      width:size, height:size, borderRadius: 18,
      background: `linear-gradient(155deg, ${dom} 0%, ${shade(dom,-20)} 60%, ${shade(dom,-35)} 100%)`,
      position:'relative', overflow:'hidden', flexShrink:0,
      boxShadow:'0 18px 40px rgba(0,0,0,0.35), inset 0 1px 0 rgba(255,255,255,0.08)',
    }}>
      <div style={{
        position:'absolute', inset:0,
        background:`radial-gradient(circle at 30% 25%, ${accent}55 0%, transparent 45%)`,
      }} />
      <div style={{
        position:'absolute', left:'50%', top:'46%', transform:'translate(-50%,-50%)',
        fontFamily:"'Instrument Serif', serif", fontSize:size*0.5, color:ink, opacity:0.92, lineHeight:1,
      }}>{glyph}</div>
      <div style={{
        position:'absolute', left:size*0.07, bottom:size*0.07, color:ink,
        fontFamily:"'JetBrains Mono', monospace", fontSize: size*0.055, letterSpacing:1.5, opacity:0.78,
      }}>{label}</div>
    </div>
  );
}

// shade helper: lightens/darkens hex by amount (-100..100)
function shade(hex, amt) {
  const n = parseInt(hex.slice(1), 16);
  const r = Math.max(0, Math.min(255, ((n>>16)&0xff) + amt));
  const g = Math.max(0, Math.min(255, ((n>>8)&0xff) + amt));
  const b = Math.max(0, Math.min(255, (n&0xff) + amt));
  return '#' + ((r<<16)|(g<<8)|b).toString(16).padStart(6,'0');
}

Object.assign(window, { MTAPill, WeatherIcon, EQBars, Ticker, AlbumArt, shade });
