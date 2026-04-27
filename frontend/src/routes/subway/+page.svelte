<script lang="ts">
  import { appStore } from '$lib/ws';
  import ODScreen from '$lib/components/ODScreen.svelte';
  import ODStatusBar from '$lib/components/ODStatusBar.svelte';
  import ODDock from '$lib/components/ODDock.svelte';
  import SectionLabel from '$lib/components/SectionLabel.svelte';

  const state = $derived($appStore);
  const transit = $derived(state.transit);
  const mode = $derived(state.motionMode);

  const LINES = [
    { color: '#0039A6', label: 'A/C', y: 130 },
    { color: '#FF6319', label: 'F', y: 200 },
    { color: '#FCCC0A', label: 'Q/R', y: 270 },
    { color: '#00933C', label: '4/5/6', y: 340 }
  ];

  const STATIONS = [
    { x: 120, label: 'High St' },
    { x: 240, label: 'Jay St' },
    { x: 360, label: 'Court St' },
    { x: 480, label: 'DeKalb' },
    { x: 600, label: 'Atlantic' },
    { x: 720, label: '14 St' },
    { x: 820, label: 'W 4 St' }
  ];

  const allStations = $derived(
    transit ? transit.stations.concat(transit.secondary) : []
  );
  const onTimeCount = $derived(
    transit
      ? allStations.flatMap((s) => s.trains).filter((t) => t.delay === 0).length
      : 134
  );
  const delayedCount = $derived(
    transit
      ? allStations.flatMap((s) => s.trains).filter((t) => t.delay > 0).length
      : 8
  );
</script>

<ODScreen {mode}>
  <ODStatusBar app="SUBWAY · LIVE · GTFS-RT" />

  <main style="flex:1;position:relative;min-height:0;">
    <SectionLabel>// MTA · abstract live diagram</SectionLabel>

    <svg viewBox="0 0 920 420" style="width:100%;height:calc(100% - 20px)">
      {#each LINES as l}
        <g>
          <path
            d="M 60 {l.y} Q 300 {l.y - 20} 460 {l.y} T 860 {l.y}"
            stroke={l.color}
            stroke-width="6"
            fill="none"
            stroke-linecap="round"
            opacity="0.9"
          />
          <text
            x="20"
            y={l.y + 5}
            fill="var(--ink)"
            font-size="13"
            font-family="var(--font-mono)"
            letter-spacing="1">{l.label}</text
          >
        </g>
      {/each}

      {#each STATIONS as s, xi}
        <g>
          {#each LINES as l, li}
            <circle
              cx={s.x}
              cy={l.y + Math.sin((xi + li) * 0.7) * 6}
              r={xi === 1 ? 8 : 4}
              fill="var(--bg)"
              stroke={l.color}
              stroke-width="2"
            />
          {/each}
        </g>
      {/each}

      {#each STATIONS as s}
        <text
          x={s.x}
          y="70"
          fill="var(--ink-dim)"
          font-size="10"
          font-family="var(--font-mono)"
          text-anchor="middle"
          letter-spacing="0.5">{s.label}</text
        >
      {/each}

      {#each LINES as l, i}
        <g>
          <circle cx={180 + i * 40} cy={l.y - 1} r="6" fill="var(--ink)" stroke={l.color} stroke-width="2.5">
            <animate
              attributeName="cx"
              from={180 + i * 40}
              to={780 + i * 15}
              dur="{30 + i * 8}s"
              repeatCount="indefinite"
            />
          </circle>
          <circle cx={420 + i * 30} cy={l.y - 1} r="6" fill="var(--ink)" stroke={l.color} stroke-width="2.5">
            <animate
              attributeName="cx"
              from={420 + i * 30}
              to={120 + i * 15}
              dur="{28 + i * 5}s"
              repeatCount="indefinite"
            />
          </circle>
        </g>
      {/each}

      <g>
        <circle cx="240" cy="200" r="14" fill="none" stroke="var(--sand)" stroke-width="2">
          <animate attributeName="r" from="10" to="22" dur="2.5s" repeatCount="indefinite" />
          <animate attributeName="opacity" from="0.9" to="0" dur="2.5s" repeatCount="indefinite" />
        </circle>
        <circle cx="240" cy="200" r="6" fill="var(--sand)" />
        <text
          x="240"
          y="395"
          fill="var(--sand)"
          font-size="11"
          font-family="var(--font-mono)"
          text-anchor="middle"
          letter-spacing="1.5">YOU · JAY ST</text
        >
      </g>
    </svg>
  </main>

  <div class="legend">
    <span><span style="color:var(--sage)">●</span> on time · {onTimeCount}</span>
    <span><span style="color:var(--rose)">●</span> delayed · {delayedCount}</span>
    <span style="color:var(--ink-sub)">tap a station for arrivals</span>
  </div>

  <ODDock active="MAP" />
</ODScreen>

<style>
  .legend {
    display: flex;
    gap: 18px;
    font-family: var(--font-mono);
    font-size: 10px;
    letter-spacing: 1px;
    color: var(--ink-dim);
  }
</style>
