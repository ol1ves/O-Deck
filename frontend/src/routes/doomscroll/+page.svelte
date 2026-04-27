<script lang="ts">
  import { appStore } from '$lib/ws';
  import ODScreen from '$lib/components/ODScreen.svelte';
  import ODStatusBar from '$lib/components/ODStatusBar.svelte';
  import ODDock from '$lib/components/ODDock.svelte';
  import SectionLabel from '$lib/components/SectionLabel.svelte';
  import type { RSSItem } from '$lib/types';

  const state = $derived($appStore);
  const rss = $derived(state.rss);
  const mode = $derived(state.motionMode);
  const items = $derived(rss?.items ?? []);

  let selectedIdx = $state(0);
  const selected = $derived((items[selectedIdx] as RSSItem | undefined) ?? null);

  let qrDataUrl = $state('');

  async function generateQR(url: string) {
    if (!url) {
      qrDataUrl = '';
      return;
    }
    try {
      const QRCode = (await import('qrcode')).default;
      qrDataUrl = await QRCode.toDataURL(url, {
        width: 220,
        color: { dark: '#1a1508', light: '#f5ecd6' },
        margin: 2
      });
    } catch {
      qrDataUrl = '';
    }
  }

  $effect(() => {
    const link = selected?.link;
    if (link) void generateQR(link);
    else qrDataUrl = '';
  });

  function srcColor(src: string): string {
    const colors: Record<string, string> = {
      TLDR: 'var(--sand)',
      HN: 'var(--rose)',
      default: 'var(--ink-dim)'
    };
    if (src.startsWith('r/')) return 'var(--sage)';
    if (src === 'YT') return 'var(--rose)';
    return colors[src] ?? colors.default;
  }
</script>

<ODScreen {mode}>
  <ODStatusBar app="DOOMSCROLL · {items.length} items · all sources" accent="var(--sand)" />

  <main class="doom-grid">
    <div class="feed-col">
      <SectionLabel>// FEED</SectionLabel>
      <div class="feed-list">
        {#each items as item, i}
          <button
            type="button"
            class="feed-item"
            class:selected={i === selectedIdx}
            onclick={() => {
              selectedIdx = i;
            }}
          >
            <span class="feed-src" style:color={srcColor(item.src)}>{item.src}</span>
            <div style="min-width:0">
              <div class="feed-title" class:selected-title={i === selectedIdx}>{item.title}</div>
              <div class="feed-summary">{item.summary}</div>
            </div>
            <span class="feed-age">{item.age}</span>
          </button>
        {/each}
        {#if !items.length}
          <div style="color:var(--ink-sub);font-size:11px">feed loading…</div>
        {/if}
      </div>
    </div>

    <aside class="qr-panel">
      <SectionLabel accent="var(--sand)">// READ ON PHONE</SectionLabel>
      {#if qrDataUrl}
        <img src={qrDataUrl} alt="QR code" class="qr-img" />
      {:else}
        <div class="qr-placeholder">QR</div>
      {/if}
      {#if selected}
        <div class="qr-title">{selected.title}</div>
        <div class="qr-meta">
          scan with phone camera<br />
          {selected.src.toLowerCase()} · tap to open
        </div>
      {/if}
      <div style="flex:1"></div>
      <div
        style="font-size:10px;color:var(--ink-sub);letter-spacing:1px;line-height:1.4;font-family:var(--font-mono)"
      >
        tap any story above<br />to load its QR code
      </div>
    </aside>
  </main>

  <ODDock active="DOOM" />
</ODScreen>

<style>
  .doom-grid {
    flex: 1;
    display: grid;
    grid-template-columns: 1fr 320px;
    gap: 24px;
    min-height: 0;
  }
  .feed-col {
    display: flex;
    flex-direction: column;
    gap: 8px;
    min-height: 0;
    overflow: hidden;
  }
  .feed-list {
    display: flex;
    flex-direction: column;
    gap: 10px;
    flex: 1;
    min-height: 0;
    overflow: hidden;
  }
  .feed-item {
    display: grid;
    grid-template-columns: 48px 1fr auto;
    gap: 12px;
    align-items: flex-start;
    padding: 8px 10px;
    border-radius: 8px;
    text-align: left;
    background: transparent;
    border: 1px solid transparent;
    cursor: pointer;
    width: 100%;
    font-family: inherit;
  }
  .feed-item.selected {
    background: rgba(230, 200, 155, 0.06);
    border-color: rgba(230, 200, 155, 0.2);
  }
  .feed-src {
    font-family: var(--font-mono);
    font-size: 9px;
    letter-spacing: 1px;
    margin-top: 2px;
  }
  .feed-title {
    font-family: var(--font-sans);
    font-size: 13.5px;
    color: var(--ink);
    line-height: 1.3;
    font-weight: 400;
  }
  .feed-title.selected-title {
    font-weight: 500;
  }
  .feed-summary {
    font-family: var(--font-sans);
    font-size: 11px;
    color: var(--ink-dim);
    margin-top: 3px;
    line-height: 1.4;
  }
  .feed-age {
    font-size: 9px;
    color: var(--ink-sub);
    letter-spacing: 0.8px;
    font-family: var(--font-mono);
    margin-top: 2px;
  }
  .qr-panel {
    display: flex;
    flex-direction: column;
    gap: 10px;
    min-height: 0;
    padding-left: 18px;
    border-left: 1px solid var(--line);
  }
  .qr-img {
    width: 220px;
    height: 220px;
    border-radius: 8px;
  }
  .qr-placeholder {
    width: 220px;
    height: 220px;
    background: rgba(240, 232, 214, 0.05);
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--ink-sub);
    font-size: 24px;
  }
  .qr-title {
    font-family: var(--font-sans);
    font-size: 13px;
    color: var(--ink);
    font-weight: 500;
    line-height: 1.3;
    margin-top: 4px;
  }
  .qr-meta {
    font-family: var(--font-mono);
    font-size: 9px;
    color: var(--ink-dim);
    letter-spacing: 0.8px;
    line-height: 1.5;
  }
</style>
