<script lang="ts">
  import { goto } from '$app/navigation';
  import { onMount } from 'svelte';
  import AlbumArt from '$lib/components/AlbumArt.svelte';
  import CommitHeartbeat from '$lib/components/CommitHeartbeat.svelte';
  import EQBars from '$lib/components/EQBars.svelte';
  import MTAPill from '$lib/components/MTAPill.svelte';
  import ODScreen from '$lib/components/ODScreen.svelte';
  import Sparkline from '$lib/components/Sparkline.svelte';
  import Ticker from '$lib/components/Ticker.svelte';
  import WeatherIcon from '$lib/components/WeatherIcon.svelte';
  import { format_uptime_label } from '$lib/format';
  import { appStore, tapTheme, tapWeatherWindow } from '$lib/ws';

  const lineColors: Record<string, string> = {
    A: '#0039A6',
    C: '#0039A6',
    E: '#0039A6',
    B: '#FF6319',
    D: '#FF6319',
    F: '#FF6319',
    M: '#FF6319',
    N: '#FCCC0A',
    Q: '#FCCC0A',
    R: '#FCCC0A',
    W: '#FCCC0A',
    '1': '#EE352E',
    '2': '#EE352E',
    '3': '#EE352E',
    '4': '#00933C',
    '5': '#00933C',
    '6': '#00933C',
    L: '#A7A9AC',
    G: '#6CBE45',
    J: '#996633',
    Z: '#996633'
  };

  const dockItems = [
    { key: 'POMO', href: '/pomodoro' },
    { key: 'GH', href: '/github' },
    { key: 'MAP', href: '/subway' },
    { key: 'DOOM', href: '/doomscroll' },
    { key: 'PHOTO', href: '/photos' },
    { key: 'SHOW', href: '/showcase' }
  ];

  let now = $state(new Date());

  onMount(() => {
    const clock = setInterval(() => {
      now = new Date();
    }, 1_000);

    return () => clearInterval(clock);
  });

  let tapCount = $state(0);
  let tapTimer: ReturnType<typeof setTimeout> | undefined;

  function handleTimeTap() {
    tapCount++;
    if (tapTimer) clearTimeout(tapTimer);
    tapTimer = setTimeout(() => {
      tapCount = 0;
    }, 2000);
    if (tapCount >= 5) {
      tapCount = 0;
      void goto('/diagnostics');
    }
  }

  const weatherIconKind = (code: number | undefined) => {
    if (code === 0 || code === 1) return 'sun';
    if (code === 2 || code === 3 || code === undefined) return 'cloud-sun';
    if ([61, 63, 65, 80, 81, 82].includes(code)) return 'rain';
    if ([71, 73, 75].includes(code)) return 'snow';
    return 'cloud';
  };

  const state = $derived($appStore);
  const device = $derived(state.device);
  const liveUptimeSeconds = $derived(
    state.uptimeOriginSeconds + (now.getTime() - state.uptimePolledAt) / 1000
  );
  const uptimeLabel = $derived(format_uptime_label(liveUptimeSeconds));
  const callsign = $derived(device?.callsign ? `/${device.callsign}` : '');
  const lanLabel = $derived(device?.lan_ip ?? device?.hostname ?? '...');
  const weather = $derived(state.weather);
  const weatherWindow = $derived(state.weatherWindow);
  const weatherSeries = $derived(
    weather ? (weatherWindow === '6h' ? weather.hourly.slice(0, 6) : weather.hourly.slice(0, 24)) : []
  );
  const weatherEndLabel = $derived(weatherWindow === '6h' ? '+6H' : 'TODAY');
  const transit = $derived(state.transit);
  const spotify = $derived(state.spotify);
  const calendar = $derived(state.calendar);
  const github = $derived(state.github);
  const commitSeries = $derived.by(() => {
    if (!github?.commits.length) return [] as number[];
    const out = new Array(36).fill(0);
    const recent = github.commits.slice(0, 36);
    for (let i = 0; i < recent.length; i++) {
      out[36 - recent.length + i] = 1;
    }
    return out;
  });
  const rss = $derived(state.rss);
  const mode = $derived(state.motionMode);
  const nowPlaying = $derived(spotify?.is_playing ? spotify : null);
  const trains = $derived((transit?.stations.flatMap((station) => station.trains) ?? []).slice(0, 5));
  const dateLabel = $derived(
    now.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' }).toUpperCase()
  );
  const hh = $derived(String(now.getHours() % 12 || 12).padStart(2, '0'));
  const mm = $derived(String(now.getMinutes()).padStart(2, '0'));
  const ss = $derived(String(now.getSeconds()).padStart(2, '0'));
  const ampm = $derived(now.getHours() >= 12 ? 'PM' : 'AM');
</script>

<svelte:head>
  <title>O-DECK</title>
</svelte:head>

<ODScreen {mode}>
  <header class="status-bar">
    <div class="status-left">
      <button type="button" class="brand brand-button" onclick={() => goto('/')} aria-label="home">O-DECK</button>
      {#if callsign}<span class="callsign">{callsign}</span>{/if}
      <span><span class="live-dot">●</span> {lanLabel}</span>
      <span class="dim">up {uptimeLabel}</span>
    </div>
    <div class="status-right">
      <button
        type="button"
        class="theme-tap"
        class:music={mode === 'music'}
        class:rain={mode === 'rain'}
        class:thunder={mode === 'thunder'}
        class:overridden={state.themeOverride !== null}
        onclick={tapTheme}
        aria-label="cycle theme"
      >◌ {mode}</button>
      <span class="callsign">{state.connected ? 'ws live' : 'ws idle'}</span>
      <span class="date">{dateLabel}</span>
    </div>
  </header>

  <section class="main-grid" aria-label="O-DECK home dashboard">
    <!-- svelte-ignore a11y_click_events_have_key_events -->
    <div
      class="time-block"
      role="button"
      tabindex="-1"
      onclick={handleTimeTap}
      aria-label="time — tap 5× for diagnostics"
    >
      <div class="clock-row">
        <span class="clock-hhmm">{hh}<span class="blink colon">:</span>{mm}</span>
        <div class="clock-meta">
          <span class="clock-ss">:{ss}</span>
          <span>{ampm} · EDT</span>
        </div>
      </div>

      <div class="weather-row">
        {#if weather}
          <div class="weather-temp">
            <span class="sand"><WeatherIcon kind={weatherIconKind(weather.code)} size={28} /></span>
            <span class="temp-num">{Math.round(weather.tempF)}°</span>
          </div>
          <div class="weather-detail">
            <div>{weather.cond.toLowerCase()}</div>
            <div class="sub">H{Math.round(weather.highF)}° L{Math.round(weather.lowF)}° · feels {Math.round(weather.feelsLikeF)}°</div>
          </div>
          <button
            type="button"
            class="weather-sparkline-btn"
            onclick={tapWeatherWindow}
            aria-label="toggle weather window"
          >
            <Sparkline
              points={weatherSeries}
              color="var(--sage)"
              width={140}
              height={36}
              nowLabel="NOW"
              endLabel={weatherEndLabel}
            />
          </button>
        {:else}
          <span class="loading">weather loading...</span>
        {/if}
      </div>
    </div>

    <aside class="now-playing-rail">
      <div class="rail-label">
        {#if nowPlaying}
          <EQBars count={4} size={10} width={2} color="var(--sage)" />
        {/if}
        <span>NOW PLAYING</span>
      </div>

      {#if nowPlaying}
        <AlbumArt
          palette={{ dom: '#6b5a8a', accent: '#c9a36c', ink: '#f5efe6' }}
          artUrl={nowPlaying.art_url}
          size={170}
          label={nowPlaying.album ?? ''}
          glyph="◇"
        />
        <div class="np-text">
          <div class="np-track">{nowPlaying.track}</div>
          <div class="np-artist">{nowPlaying.artist}</div>
          <div class="np-album">from {(nowPlaying.album ?? '').toUpperCase()}</div>
        </div>
        <div class="np-progress">
          <div class="progress-track">
            <div class="progress-fill" style:width={`${Math.round(nowPlaying.progress * 100)}%`}></div>
          </div>
          <div class="progress-times">
            <span>{nowPlaying.elapsed}</span>
            <span>{nowPlaying.total}</span>
          </div>
        </div>
      {:else}
        <div class="loading">nothing playing</div>
      {/if}

      {#if rss?.headlines.length}
        <div class="rss-stack">
          <div class="rail-label">FEED</div>
          {#each rss.headlines.slice(0, 2) as headline}
            <article>
              <div class="rss-source">{headline.src} · {headline.age}</div>
              <div class="rss-title">{headline.title}</div>
            </article>
          {/each}
        </div>
      {/if}
    </aside>

    <div class="bottom-left">
      <section class="transit-block" aria-label="Next trains">
        <div class="section-header">
          <span>NEXT TRAINS</span>
          <span class="rule"></span>
          {#if transit?.alerts.length}
            <span class="alert">! delays</span>
          {/if}
        </div>

        {#if trains.length}
          <div class="transit-hero">
            <MTAPill line={trains[0].line} color={lineColors[trains[0].line] ?? '#888'} size={32} />
            <div class="train-copy">
              <div class="train-kicker">{transit?.stations[0]?.name.toUpperCase() ?? 'NEXT'} · {trains[0].dest.toUpperCase()}</div>
              <div class:alert={trains[0].delay > 0} class="train-status">{trains[0].status}</div>
            </div>
            <div class="transit-mins">{trains[0].mins}<span>min</span></div>
          </div>

          {#each trains.slice(1) as train}
            <div class="transit-row">
              <MTAPill line={train.line} color={lineColors[train.line] ?? '#888'} size={18} />
              <div class="train-copy">
                <div class="train-dest">{train.dest}</div>
                <div class:alert={train.delay > 0} class="train-status">{train.status}</div>
              </div>
              <div class="train-mins">{train.mins}<span>m</span></div>
            </div>
          {/each}
        {:else}
          <div class="loading">transit loading...</div>
        {/if}
      </section>

      <section class="calendar-block" aria-label="Today at a glance">
        <div class="section-header">
          <span>TODAY · {calendar?.events.length ?? 0} EVENTS</span>
          <span class="rule"></span>
          {#if calendar?.next_in}
            <span class="sub">next in {calendar.next_in}</span>
          {/if}
        </div>

        <div class="timeline">
          <span class="timeline-spine"></span>
          {#each calendar?.events ?? [] as event, index}
            <article class="timeline-event">
              <span class="timeline-node" class:active={index === 0}></span>
              <time>{event.time}</time>
              <div>
                <div class="event-title">{event.title}</div>
                <div class="event-meta">
                  {event.location.toLowerCase()}
                  {#if event.notion}
                    <span> · notion/{event.notion.project}</span>
                  {/if}
                </div>
              </div>
            </article>
          {/each}

          {#if !calendar?.events.length}
            <div class="loading">calendar loading...</div>
          {/if}
        </div>
      </section>
    </div>
  </section>

  <footer class="home-footer">
    <div class="git-strip">
      <span>git</span>
      <CommitHeartbeat color="var(--sage)" series={commitSeries} />
      <span class="sub">{github?.commits.length ?? 0}↑ {github?.prs.length ?? 0}pr</span>
    </div>
    <span class="footer-rule"></span>
    <nav class="launcher-dock" aria-label="App launcher">
      {#each dockItems as item, index}
        <button class="dock-btn" onclick={() => goto(item.href)} aria-label={item.key}>
          <span class="dock-dot" class:first={index === 0}></span>
          {item.key}
        </button>
      {/each}
    </nav>
    <span class="footer-rule"></span>
    <div class="footer-ticker">
      <Ticker items={rss?.ticker ?? []} color="var(--ink)" opacity={0.45} fontSize={10} />
    </div>
  </footer>
</ODScreen>

<style>
  :global(.odeck-screen) {
    background: var(--bg);
  }

  .status-bar,
  .status-left,
  .status-right,
  .clock-row,
  .weather-row,
  .section-header,
  .transit-hero,
  .transit-row,
  .home-footer,
  .git-strip,
  .launcher-dock {
    display: flex;
    align-items: center;
  }

  .status-bar {
    justify-content: space-between;
    color: var(--ink-dim);
    font-family: var(--font-mono);
    font-size: 10px;
    letter-spacing: 0.15em;
  }

  .status-left,
  .status-right {
    gap: 18px;
  }

  .status-right {
    gap: 14px;
  }

  .theme-tap {
    padding: 0;
    border: 0;
    background: none;
    color: inherit;
    font: inherit;
    letter-spacing: inherit;
    cursor: pointer;
  }

  .theme-tap.overridden {
    text-decoration: underline dotted currentColor;
    text-underline-offset: 3px;
  }

  .brand {
    color: var(--ink);
    font-weight: 500;
  }

  .brand-button {
    padding: 0;
    border: 0;
    background: none;
    color: var(--ink);
    font: inherit;
    font-weight: 500;
    letter-spacing: inherit;
    cursor: pointer;
  }

  .callsign,
  .dim,
  .sub {
    color: var(--ink-sub);
  }

  .live-dot,
  .date,
  .sand,
  .music {
    color: var(--sand);
  }

  .rain {
    color: #aac0d6;
  }

  .thunder,
  .alert {
    color: var(--rose);
  }

  .main-grid {
    display: grid;
    flex: 1;
    grid-template-columns: minmax(0, 1fr) 320px;
    grid-template-rows: auto minmax(0, 1fr);
    gap: 18px 28px;
    min-height: 0;
    margin-top: 4px;
  }

  .time-block {
    grid-column: 1;
    grid-row: 1;
  }

  .clock-row {
    align-items: baseline;
    gap: 14px;
  }

  .clock-hhmm,
  .clock-ss,
  .temp-num,
  .transit-mins,
  .train-mins,
  .np-track,
  .np-artist,
  .event-title,
  .timeline time,
  .train-dest {
    font-family: var(--font-sans);
  }

  .clock-hhmm {
    color: var(--ink);
    font-size: clamp(88px, 14vw, 148px);
    font-variant-numeric: tabular-nums;
    font-weight: 200;
    letter-spacing: -0.055em;
    line-height: 0.85;
  }

  .colon {
    font-weight: 200;
  }

  .clock-meta {
    display: flex;
    flex-direction: column;
    gap: 4px;
    padding-bottom: 10px;
    color: var(--ink-sub);
    font-size: 11px;
    letter-spacing: 0.18em;
  }

  .clock-ss {
    color: var(--ink-dim);
    font-size: 36px;
    font-variant-numeric: tabular-nums;
    font-weight: 300;
    letter-spacing: -0.04em;
    line-height: 1;
  }

  .weather-row {
    gap: 18px;
    margin-top: 6px;
  }

  .weather-temp {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .temp-num {
    font-size: 32px;
    font-variant-numeric: tabular-nums;
    font-weight: 300;
    letter-spacing: -0.04em;
  }

  .weather-detail,
  .loading {
    color: var(--ink-dim);
    font-size: 11px;
    letter-spacing: 0.09em;
    line-height: 1.5;
  }

  .weather-sparkline-btn {
    margin-left: auto;
    padding: 0;
    border: 0;
    background: none;
    cursor: pointer;
  }

  .now-playing-rail {
    display: flex;
    flex-direction: column;
    grid-column: 2;
    grid-row: 1 / span 2;
    gap: 14px;
    min-height: 0;
    padding-left: 22px;
    border-left: 1px solid var(--line);
  }

  .rail-label,
  .section-header {
    display: flex;
    align-items: center;
    gap: 8px;
    color: var(--ink-dim);
    font-size: 10px;
    letter-spacing: 0.2em;
  }

  .np-text {
    display: flex;
    flex-direction: column;
    gap: 3px;
  }

  .np-track {
    color: var(--ink);
    font-size: 24px;
    font-weight: 600;
    letter-spacing: -0.02em;
    line-height: 1.15;
  }

  .np-artist {
    color: var(--ink-dim);
    font-size: 14px;
  }

  .np-album,
  .progress-times,
  .rss-source {
    color: var(--ink-sub);
    font-size: 10px;
    letter-spacing: 0.1em;
  }

  .np-progress {
    display: flex;
    flex-direction: column;
    gap: 5px;
    margin-top: auto;
  }

  .progress-track {
    height: 2px;
    overflow: hidden;
    border-radius: 999px;
    background: rgb(240 232 214 / 10%);
  }

  .progress-fill {
    height: 100%;
    background: var(--sand);
  }

  .progress-times {
    display: flex;
    justify-content: space-between;
    font-variant-numeric: tabular-nums;
  }

  .rss-stack {
    display: flex;
    flex-direction: column;
    gap: 8px;
    padding-top: 12px;
    border-top: 1px solid var(--line);
  }

  .rss-source {
    color: var(--rose);
    font-size: 9px;
  }

  .rss-title {
    color: var(--ink);
    font-family: var(--font-sans);
    font-size: 12px;
    line-height: 1.3;
  }

  .bottom-left {
    display: grid;
    grid-column: 1;
    grid-row: 2;
    grid-template-columns: minmax(0, 1fr) minmax(0, 1.1fr);
    gap: 24px;
    min-height: 0;
  }

  .transit-block,
  .calendar-block {
    display: flex;
    flex-direction: column;
    gap: 8px;
    min-height: 0;
  }

  .rule {
    flex: 1;
    height: 1px;
    background: var(--line);
  }

  .transit-hero {
    gap: 12px;
  }

  .train-copy {
    flex: 1;
    min-width: 0;
  }

  .train-kicker,
  .train-status,
  .event-meta {
    color: var(--ink-dim);
    font-size: 9px;
    letter-spacing: 0.06em;
  }

  .train-dest {
    overflow: hidden;
    color: var(--ink-dim);
    font-size: 10.5px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .train-status:not(.alert) {
    color: var(--sage);
  }

  .transit-mins {
    color: var(--ink);
    font-size: 54px;
    font-variant-numeric: tabular-nums;
    font-weight: 300;
    letter-spacing: -0.04em;
    line-height: 0.9;
  }

  .transit-mins span,
  .train-mins span {
    margin-left: 2px;
    color: var(--ink-dim);
    font-size: 14px;
    font-weight: 400;
  }

  .transit-row {
    gap: 9px;
  }

  .train-mins {
    color: var(--ink);
    font-size: 16px;
    font-variant-numeric: tabular-nums;
    font-weight: 500;
    letter-spacing: -0.03em;
  }

  .train-mins span {
    color: var(--ink-sub);
    font-size: 9px;
  }

  .timeline {
    position: relative;
    display: flex;
    flex: 1;
    flex-direction: column;
    gap: 6px;
    min-height: 0;
    padding-left: 14px;
  }

  .timeline-spine {
    position: absolute;
    top: 8px;
    bottom: 8px;
    left: 4px;
    width: 1px;
    background: linear-gradient(180deg, rgb(230 200 155 / 47%), var(--line));
  }

  .timeline-event {
    position: relative;
    display: flex;
    align-items: flex-start;
    gap: 10px;
  }

  .timeline-node {
    position: absolute;
    top: 6px;
    left: -14px;
    width: 9px;
    height: 9px;
    border: 1.5px solid rgb(240 232 214 / 40%);
    border-radius: 999px;
  }

  .timeline-node.active {
    border-color: var(--sand);
    background: var(--sand);
  }

  .timeline time {
    width: 46px;
    flex-shrink: 0;
    color: var(--ink);
    font-size: 12.5px;
    font-variant-numeric: tabular-nums;
    font-weight: 500;
  }

  .event-title {
    color: var(--ink);
    font-size: 13px;
    font-weight: 500;
    line-height: 1.2;
  }

  .event-meta span {
    color: var(--sage);
  }

  .home-footer {
    gap: 16px;
    margin-top: auto;
    padding-top: 10px;
    border-top: 1px solid var(--line);
  }

  .git-strip {
    flex-shrink: 0;
    gap: 8px;
    color: var(--ink-dim);
    font-size: 9px;
    letter-spacing: 0.15em;
  }

  .footer-rule {
    width: 1px;
    height: 14px;
    flex-shrink: 0;
    background: var(--line);
  }

  .launcher-dock {
    flex-shrink: 0;
    gap: 14px;
  }

  .dock-btn {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 0;
    border: 0;
    background: none;
    color: var(--ink-dim);
    cursor: pointer;
    font-family: var(--font-mono);
    font-size: 10px;
    letter-spacing: 0.15em;
  }

  .dock-dot {
    width: 5px;
    height: 5px;
    border-radius: 999px;
    background: rgb(240 232 214 / 25%);
  }

  .dock-dot.first {
    background: var(--sand);
  }

  .footer-ticker {
    min-width: 0;
    flex: 1;
  }

  @media (max-width: 760px) {
    .main-grid {
      grid-template-columns: 1fr;
    }

    .now-playing-rail {
      display: none;
    }

    .bottom-left {
      grid-template-columns: 1fr;
    }
  }
</style>
