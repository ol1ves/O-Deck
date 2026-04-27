<script lang="ts">
  import { appStore } from '$lib/ws';
  import DriftOrbs from '$lib/components/DriftOrbs.svelte';
  import Grain from '$lib/components/Grain.svelte';
  import { goto } from '$app/navigation';
  import type { MotionMode } from '$lib/types';

  const state = $derived($appStore);
  const mode = $derived(state.motionMode);

  const palettes: Record<MotionMode, string[]> = {
    music: ['#a08fb3', '#d49a8e', '#e6c89b', '#7a90a8', '#a8c19a'],
    calm: ['#e6c89b', '#a8c19a', '#7a5f4a', '#5a6a78', '#d49a8e'],
    rain: ['#5a7088', '#7a90a8', '#3e556a', '#a8c19a', '#9bb38b'],
    thunder: ['#c8b89a', '#7a6a8a', '#3e3a4a', '#d49a8e', '#e6c89b']
  };
  const palette = $derived(palettes[mode] ?? palettes.calm);
</script>

<!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
<div class="showcase-screen" onclick={() => goto('/')}>
  <DriftOrbs {palette} {mode} count={10} />
  <Grain />
  <div class="identifier">SHOWCASE · {mode.toUpperCase()} · tap to return</div>
</div>

<style>
  .showcase-screen {
    width: 100vw;
    height: 100vh;
    background: #0c0a08;
    position: relative;
    overflow: hidden;
    font-family: var(--font-mono);
    color: var(--ink);
    cursor: pointer;
  }
  .identifier {
    position: absolute;
    bottom: 14px;
    right: 18px;
    font-size: 9px;
    color: rgba(240, 232, 214, 0.35);
    letter-spacing: 2px;
    z-index: 2;
    pointer-events: none;
  }
</style>
