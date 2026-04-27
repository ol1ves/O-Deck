<script lang="ts">
  import { appStore } from '$lib/ws';
  import ODScreen from '$lib/components/ODScreen.svelte';
  import ODStatusBar from '$lib/components/ODStatusBar.svelte';
  import ODDock from '$lib/components/ODDock.svelte';
  import MTAPill from '$lib/components/MTAPill.svelte';

  const state = $derived($appStore);
  const transit = $derived(state.transit);
  const mode = $derived(state.motionMode);

  const LINE_COLORS: Record<string, string> = {
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

  const allStations = $derived(
    [...(transit?.stations ?? []), ...(transit?.secondary ?? [])].slice(0, 4)
  );
</script>

<ODScreen {mode}>
  <ODStatusBar app="TRANSIT · LIVE · 4 stations" />

  <main class="station-grid">
    {#each allStations as stn, si}
      <div
        class="station-cell"
        style="
          padding-right:{si % 2 === 0 ? '18px' : '0'};
          border-right:{si % 2 === 0 ? '1px solid var(--line)' : 'none'};
          padding-bottom:{si < 2 ? '14px' : '0'};
          border-bottom:{si < 2 ? '1px solid var(--line)' : 'none'};
          padding-left:{si % 2 === 1 ? '4px' : '0'};
        "
      >
        <div class="station-header">
          <div>
            <div class="station-name">{stn.name}</div>
            <div style="font-size:10px;letter-spacing:1.5px;color:var(--ink-dim);margin-top:2px">
              {stn.primary ? 'PRIMARY' : 'SECONDARY · return home'}
            </div>
          </div>
          <span class="live-dot" style="color:var(--sage)">●</span>
        </div>

        <div class="train-list">
          {#each stn.trains.slice(0, stn.primary ? 4 : 3) as train}
            <div class="train-row">
              <MTAPill line={train.line} color={LINE_COLORS[train.line] ?? '#888'} size={26} />
              <div style="flex:1;min-width:0">
                <div
                  style="font-family:var(--font-sans);font-size:13px;color:var(--ink);font-weight:500;line-height:1.2"
                >
                  to {train.dest}
                </div>
                <div
                  style="font-size:10px;color:{train.delay > 0
                    ? 'var(--rose)'
                    : 'var(--sage)'};letter-spacing:0.6px;margin-top:1px"
                >
                  {train.status}
                </div>
              </div>
              <div class="train-mins" style="font-family:var(--font-sans)">
                {train.mins}<span style="font-size:11px;color:var(--ink-dim);margin-left:2px;font-weight:400"
                  >min</span
                >
              </div>
            </div>
          {/each}
        </div>
      </div>
    {/each}
  </main>

  {#if transit?.alerts.length}
    <div class="alert-banner">
      {#each transit.alerts as alert}
        <div>! {alert}</div>
      {/each}
    </div>
  {/if}

  <ODDock active="HOME" />
</ODScreen>

<style>
  .station-grid {
    flex: 1;
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 18px;
    min-height: 0;
    padding-top: 6px;
  }
  .station-cell {
    display: flex;
    flex-direction: column;
    gap: 8px;
    min-height: 0;
  }
  .station-header {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
  }
  .station-name {
    font-family: var(--font-sans);
    font-size: 18px;
    font-weight: 500;
    letter-spacing: -0.3px;
    color: var(--ink);
  }
  .train-list {
    display: flex;
    flex-direction: column;
    gap: 4px;
    flex: 1;
    min-height: 0;
  }
  .train-row {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 4px 0;
  }
  .train-mins {
    font-weight: 300;
    font-size: 32px;
    letter-spacing: -1px;
    font-variant-numeric: tabular-nums;
    line-height: 1;
    color: var(--ink);
  }
  .alert-banner {
    font-size: 10px;
    color: var(--rose);
    letter-spacing: 1px;
    padding: 6px 10px;
    background: rgba(212, 154, 142, 0.1);
    border: 1px solid rgba(212, 154, 142, 0.22);
    border-radius: 8px;
  }
</style>
