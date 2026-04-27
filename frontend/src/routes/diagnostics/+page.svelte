<script lang="ts">
  import { onMount } from 'svelte';
  import ODScreen from '$lib/components/ODScreen.svelte';
  import ODStatusBar from '$lib/components/ODStatusBar.svelte';
  import ODDock from '$lib/components/ODDock.svelte';
  import SectionLabel from '$lib/components/SectionLabel.svelte';
  import BlockBar from '$lib/components/BlockBar.svelte';

  interface IntegrationStatus {
    name: string;
    error_count: number;
    last_success: number | null;
  }

  interface StatusResponse {
    ws_clients: number;
    integrations: IntegrationStatus[];
  }

  let statusData = $state<StatusResponse | null>(null);
  let loading = $state(true);

  function relSec(ts: number | null): string {
    if (ts === null) return 'never';
    const s = Math.floor(Date.now() / 1000 - ts);
    if (s < 60) return `${s}s ago`;
    if (s < 3600) return `${Math.floor(s / 60)}m ago`;
    return `${Math.floor(s / 3600)}h ago`;
  }

  const SYS_METRICS = [
    { k: 'cpu', v: '8%', bar: 0.08, color: 'var(--sage)' },
    { k: 'ram', v: '42%', bar: 0.42, color: 'var(--sage)' },
    { k: 'disk', v: '28%', bar: 0.28, color: 'var(--sage)' },
    { k: 'temp', v: '54°C', bar: 0.54, color: 'var(--sand)' },
    { k: 'uptime', v: '4d 11h 32m', bar: 0, color: 'var(--ink-dim)' }
  ];

  onMount(() => {
    void (async () => {
      try {
        const resp = await fetch('/api/status');
        if (resp.ok) statusData = (await resp.json()) as StatusResponse;
      } catch {
        /* ignore */
      }
      loading = false;
    })();

    const interval = setInterval(async () => {
      try {
        const resp = await fetch('/api/status');
        if (resp.ok) statusData = (await resp.json()) as StatusResponse;
      } catch {
        /* ignore */
      }
    }, 5000);
    return () => clearInterval(interval);
  });
</script>

<ODScreen mode="calm" orbs={false}>
  <ODStatusBar app="DIAGNOSTICS · /diagnostics" />

  <main class="diag-grid">
    <div class="integrations-col">
      <SectionLabel>// INTEGRATIONS</SectionLabel>
      {#if loading}
        <div style="color:var(--ink-sub);font-size:11px">loading…</div>
      {:else}
        <div class="table-header">
          <span>NAME</span><span>STATUS</span><span>LAST FETCH</span><span>ERRS</span>
        </div>
        {#each statusData?.integrations ?? [] as it}
          <div class="table-row">
            <span>{it.name}</span>
            <span style:color={it.error_count > 0 ? 'var(--rose)' : 'var(--sage)'}
              >● {it.error_count > 0 ? 'warn' : 'ok'}</span
            >
            <span style:color="var(--ink-dim)">{relSec(it.last_success)}</span>
            <span style:color={it.error_count > 0 ? 'var(--rose)' : 'var(--ink-sub)'}>
              {it.error_count}
            </span>
          </div>
        {/each}
        {#if !(statusData?.integrations.length)}
          <div style="color:var(--ink-sub);font-size:11px">no integration data</div>
        {/if}
        <div style="font-size:10px;color:var(--ink-sub);margin-top:8px;letter-spacing:1px">
          {statusData?.ws_clients ?? 0} frontend client{statusData?.ws_clients !== 1 ? 's' : ''} connected
        </div>
      {/if}
    </div>

    <div class="system-col">
      <div>
        <SectionLabel>// SYSTEM</SectionLabel>
        <div class="sys-metrics">
          {#each SYS_METRICS as m}
            <div class="sys-row">
              <span style="color:var(--ink-dim);letter-spacing:1px">{m.k}</span>
              <span>
                {#if m.bar > 0}<BlockBar value={m.bar} width={18} color={m.color} />
                {:else}<span style="color:var(--ink-sub)">—</span>{/if}
              </span>
              <span style:color="var(--ink);font-variant-numeric:tabular-nums">{m.v}</span>
            </div>
          {/each}
        </div>
      </div>

      <div style="flex:1;display:flex;flex-direction:column;min-height:0;margin-top:14px">
        <SectionLabel>// LOG TAIL</SectionLabel>
        <div class="log-tail">
          <div><span style="color:var(--sage)">now</span> backend online · ws ready</div>
          <div><span style="color:var(--sage)">init</span> weather fetch ok</div>
          <div><span style="color:var(--sage)">init</span> transit fetch ok · 4 stations</div>
          <div><span style="color:var(--sand)">info</span> ws client connected</div>
          <div style="color:var(--ink-sub)">— more in journalctl —</div>
        </div>
      </div>
    </div>
  </main>

  <ODDock />
</ODScreen>

<style>
  .diag-grid {
    flex: 1;
    display: grid;
    grid-template-columns: 1.3fr 1fr;
    gap: 24px;
    min-height: 0;
  }
  .integrations-col,
  .system-col {
    display: flex;
    flex-direction: column;
    gap: 8px;
    min-height: 0;
  }
  .table-header {
    display: grid;
    grid-template-columns: 1.4fr 70px 1fr 50px;
    gap: 10px;
    font-family: var(--font-mono);
    font-size: 9px;
    letter-spacing: 1.2px;
    color: var(--ink-sub);
    padding-bottom: 6px;
    border-bottom: 1px solid var(--line);
  }
  .table-row {
    display: grid;
    grid-template-columns: 1.4fr 70px 1fr 50px;
    gap: 10px;
    padding: 9px 0;
    border-bottom: 1px dashed var(--line);
    font-family: var(--font-mono);
    font-size: 11px;
    letter-spacing: 0.5px;
    color: var(--ink);
    align-items: center;
  }
  .sys-metrics {
    display: flex;
    flex-direction: column;
    gap: 8px;
    font-family: var(--font-mono);
    font-size: 11px;
  }
  .sys-row {
    display: grid;
    grid-template-columns: 58px 1fr auto;
    gap: 10px;
    align-items: center;
  }
  .log-tail {
    font-family: var(--font-mono);
    font-size: 10px;
    color: var(--ink-dim);
    letter-spacing: 0.3px;
    line-height: 1.7;
    flex: 1;
    overflow: hidden;
  }
</style>
