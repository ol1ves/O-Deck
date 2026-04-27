<script lang="ts">
  import { goto } from '$app/navigation';

  let {
    app = '',
    accent = 'var(--sand)',
  }: {
    app?: string;
    accent?: string;
  } = $props();
</script>

<header class="od-status-bar" style:--od-status-accent={accent}>
  <div class="od-status-bar__left">
    <button type="button" class="od-status-bar__brand od-status-bar__brand-button" onclick={() => goto('/')} aria-label="home">O-DECK</button>
    {#if app}
      <span class="od-status-bar__separator">/</span>
      <span class="od-status-bar__app">{app}</span>
    {/if}
    <span class="od-status-bar__host"><span class="live-dot">●</span> host</span>
  </div>

  <div class="od-status-bar__right" aria-label="connection and date">
    <span>wifi link</span>
    <span class="od-status-bar__date">26 APR · EDT</span>
  </div>
</header>

<style>
  .od-status-bar {
    position: relative;
    z-index: 2;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 18px;
    padding-bottom: 10px;
    border-bottom: 1px solid var(--line);
    color: var(--ink-dim);
    font-family: var(--font-mono);
    font-size: 10px;
    letter-spacing: 1.5px;
    text-transform: uppercase;
  }

  .od-status-bar__left,
  .od-status-bar__right {
    display: flex;
    align-items: center;
    gap: 14px;
    min-width: 0;
  }

  .od-status-bar__left {
    gap: 18px;
  }

  .od-status-bar__brand {
    color: var(--ink);
    font-weight: 500;
  }

  .od-status-bar__brand-button {
    padding: 0;
    border: 0;
    background: none;
    color: var(--ink);
    font: inherit;
    font-weight: 500;
    letter-spacing: inherit;
    text-transform: inherit;
    cursor: pointer;
  }

  .od-status-bar__separator {
    color: var(--ink-sub);
  }

  .od-status-bar__app,
  .od-status-bar__date {
    color: var(--od-status-accent);
    letter-spacing: 1.8px;
  }

  .od-status-bar__host :global(.live-dot) {
    color: var(--sage);
  }

  .od-status-bar__right {
    flex: 0 0 auto;
    color: var(--ink-sub);
  }
</style>
