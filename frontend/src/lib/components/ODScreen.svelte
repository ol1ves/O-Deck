<script lang="ts">
  import type { Snippet } from 'svelte';
  import DriftOrbs from './DriftOrbs.svelte';
  import Grain from './Grain.svelte';
  import RainOverlay from './RainOverlay.svelte';

  type Mode = 'calm' | 'music' | 'rain' | 'thunder';

  const palettes: Record<Mode, string[]> = {
    calm: ['#e6c89b', '#a8c19a', '#7a5f4a', '#5a6a78'],
    music: ['#a08fb3', '#d49a8e', '#e6c89b', '#7a90a8'],
    rain: ['#5a7088', '#7a90a8', '#3e556a', '#9bb38b'],
    thunder: ['#c8b89a', '#7a6a8a', '#3e3a4a', '#d49a8e'],
  };

  let {
    mode = 'calm',
    orbs = true,
    children,
  }: {
    mode?: Mode;
    orbs?: boolean;
    children?: Snippet;
  } = $props();

  const palette = $derived(palettes[mode] ?? palettes.calm);
</script>

<div class="odeck-screen">
  {#if orbs}
    <DriftOrbs {palette} {mode} count={6} />
    {#if mode === 'rain' || mode === 'thunder'}
      <RainOverlay
        intensity={mode === 'thunder' ? 0.9 : 0.5}
        color={mode === 'thunder' ? '#c8b8a0' : '#aac0d6'}
      />
    {/if}
    <Grain />
  {/if}

  <div class="odeck-screen__inner">
    {@render children?.()}
  </div>
</div>

<style>
  .odeck-screen {
    position: relative;
    overflow: hidden;
    height: 100vh;
    background: var(--od-bg);
    color: var(--od-ink);
    font-family: var(--font-mono);
  }

  .odeck-screen__inner {
    position: relative;
    z-index: 1;
    display: flex;
    flex-direction: column;
    gap: 10px;
    box-sizing: border-box;
    height: 100%;
    padding: 10px 16px;
  }
</style>
