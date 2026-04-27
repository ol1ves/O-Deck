<script lang="ts">
  import { onMount } from 'svelte';
  import { appStore } from '$lib/ws';
  import { startPomodoro, pausePomodoro, stopPomodoro } from '$lib/api';
  import ODScreen from '$lib/components/ODScreen.svelte';
  import ODStatusBar from '$lib/components/ODStatusBar.svelte';
  import ODDock from '$lib/components/ODDock.svelte';

  const state = $derived($appStore);
  const pomo = $derived(state.pomodoro);
  const mode = $derived(state.motionMode);

  let localRemaining = $state(0);
  $effect(() => {
    const p = pomo;
    if (!p) {
      localRemaining = 0;
      return;
    }
    localRemaining = p.remaining_seconds;
    if (!p.running) return;
    const id = setInterval(() => {
      localRemaining = Math.max(0, localRemaining - 1);
    }, 1000);
    return () => clearInterval(id);
  });

  const mm = $derived(String(Math.floor(localRemaining / 60)).padStart(2, '0'));
  const ss = $derived(String(localRemaining % 60).padStart(2, '0'));
  const total = $derived((pomo?.work_min ?? 25) * 60);
  const elapsed = $derived(total - localRemaining);
  const progress = $derived(total > 0 ? elapsed / total : 0);
  const circum = 2 * Math.PI * 110;
  const dashArray = $derived(`${circum * progress} ${circum}`);

  type Preset = { name: string; work_min: number; break_min: number; cycles: number; long_break_min: number };

  let presets: Preset[] = $state([
    { name: 'Classic', work_min: 25, break_min: 5, cycles: 4, long_break_min: 15 },
    { name: 'Deep', work_min: 50, break_min: 10, cycles: 3, long_break_min: 20 }
  ]);
  let selectedPreset = $state<Preset>({
    name: 'Classic',
    work_min: 25,
    break_min: 5,
    cycles: 4,
    long_break_min: 15
  });

  onMount(() => {
    void (async () => {
      try {
        const r = await fetch('/api/config');
        if (!r.ok) return;
        const j = (await r.json()) as { pomodoro?: { presets?: Preset[] } };
        if (j.pomodoro?.presets?.length) {
          presets = j.pomodoro.presets;
          selectedPreset = presets[0];
        }
      } catch {
        /* ignore */
      }
    })();
  });

  async function handleStart() {
    await startPomodoro(selectedPreset);
  }
  async function handlePause() {
    await pausePomodoro();
  }
  async function handleStop() {
    await stopPomodoro();
  }

  const isIdle = $derived(!pomo || pomo.phase === 'idle');
  const isRunning = $derived(pomo?.running === true);

  const tickmarks = [0, 1, 2, 3, 4];
</script>

<ODScreen {mode}>
  <ODStatusBar
    app="POMODORO · {pomo?.preset_name || 'IDLE'} · cycle {pomo?.cycle ?? 0}/{pomo?.cycles_total ?? 4}"
    accent="var(--rose)"
  />

  <main class="pomo-main">
    <div class="ring-wrap">
      <svg width="240" height="240" viewBox="0 0 240 240">
        <circle cx="120" cy="120" r="110" fill="none" stroke="rgba(240,232,214,0.06)" stroke-width="2" />
        <circle
          cx="120"
          cy="120"
          r="110"
          fill="none"
          stroke="var(--rose)"
          stroke-width="3"
          stroke-dasharray={dashArray}
          stroke-linecap="round"
          transform="rotate(-90 120 120)"
        />
        {#each tickmarks as i}
          {@const a = -Math.PI / 2 + ((i + 1) / 5) * Math.PI * 2}
          <line
            x1={120 + Math.cos(a) * 102}
            y1={120 + Math.sin(a) * 102}
            x2={120 + Math.cos(a) * 116}
            y2={120 + Math.sin(a) * 116}
            stroke="var(--ink-sub)"
            stroke-width="1"
          />
        {/each}
      </svg>
      <div class="countdown">
        <div style="font-size:11px;letter-spacing:2.5px;color:var(--ink-dim);margin-bottom:4px">
          {isIdle ? 'IDLE' : (pomo?.phase?.toUpperCase() ?? 'FOCUS')}
        </div>
        <div class="countdown-time" style="font-family:var(--font-sans)">
          {mm}<span class="blink" style="color:var(--rose)">:</span>{ss}
        </div>
        <div style="font-size:11px;letter-spacing:2px;color:var(--ink-sub);margin-top:6px">
          of {pomo?.work_min ?? 25}:00
        </div>
      </div>
    </div>

    <div class="cycle-dots">
      {#each Array.from({ length: pomo?.cycles_total ?? 4 }, (_, i) => i) as i}
        <div
          class="cycle-dot"
          style:background={i < (pomo?.cycle ?? 0)
            ? 'var(--rose)'
            : i === (pomo?.cycle ?? 0)
              ? 'rgba(212,154,142,0.33)'
              : 'transparent'}
          style:border={i >= (pomo?.cycle ?? 0) ? '1.5px solid var(--ink-sub)' : 'none'}
        ></div>
      {/each}
      <div style="font-size:10px;letter-spacing:1.5px;color:var(--ink-dim);margin-left:8px">
        cycle {pomo?.cycle ?? 0} of {pomo?.cycles_total ?? 4}
      </div>
    </div>

    {#if isIdle}
      <div class="preset-selector">
        {#each presets as preset}
          <button
            type="button"
            class="preset-btn"
            class:active={selectedPreset.name === preset.name}
            onclick={() => {
              selectedPreset = preset;
            }}
          >
            {preset.name} · {preset.work_min}m
          </button>
        {/each}
      </div>
    {/if}

    <div class="controls">
      {#if isIdle}
        <button type="button" class="ctrl-btn primary" onclick={handleStart}>Start</button>
      {:else if isRunning}
        <button type="button" class="ctrl-btn" onclick={handlePause}>Pause</button>
        <button type="button" class="ctrl-btn danger" onclick={handleStop}>Stop</button>
      {:else}
        <button
          type="button"
          class="ctrl-btn primary"
          onclick={async () => {
            await fetch('/api/pomodoro/resume', { method: 'POST' });
          }}>Resume</button
        >
        <button type="button" class="ctrl-btn danger" onclick={handleStop}>Stop</button>
      {/if}
    </div>
  </main>

  <ODDock active="POMO" />
</ODScreen>

<style>
  .pomo-main {
    flex: 1;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    gap: 14px;
    position: relative;
  }
  .ring-wrap {
    position: relative;
    width: 240px;
    height: 240px;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .ring-wrap :global(svg) {
    position: absolute;
    inset: 0;
  }
  .countdown {
    text-align: center;
    position: relative;
    z-index: 1;
  }
  .countdown-time {
    font-weight: 200;
    font-size: 78px;
    letter-spacing: -3px;
    line-height: 0.95;
    font-variant-numeric: tabular-nums;
    color: var(--ink);
  }
  .cycle-dots {
    display: flex;
    gap: 12px;
    align-items: center;
  }
  .cycle-dot {
    width: 10px;
    height: 10px;
    border-radius: 10px;
  }
  .preset-selector {
    display: flex;
    gap: 12px;
  }
  .preset-btn {
    font-family: var(--font-mono);
    font-size: 10px;
    letter-spacing: 1.5px;
    padding: 6px 14px;
    border-radius: 6px;
    border: 1px solid var(--line);
    background: transparent;
    color: var(--ink-dim);
    cursor: pointer;
  }
  .preset-btn.active {
    border-color: var(--rose);
    color: var(--rose);
    background: rgba(212, 154, 142, 0.08);
  }
  .controls {
    display: flex;
    gap: 12px;
  }
  .ctrl-btn {
    font-family: var(--font-mono);
    font-size: 11px;
    letter-spacing: 1.5px;
    padding: 8px 24px;
    border-radius: 8px;
    border: 1px solid var(--line);
    background: rgba(240, 232, 214, 0.06);
    color: var(--ink);
    cursor: pointer;
  }
  .ctrl-btn.primary {
    border-color: var(--rose);
    color: var(--rose);
    background: rgba(212, 154, 142, 0.1);
  }
  .ctrl-btn.danger {
    border-color: rgba(212, 154, 142, 0.3);
    color: var(--ink-sub);
  }
</style>
