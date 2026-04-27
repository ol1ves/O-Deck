<script lang="ts">
  import { appStore } from '$lib/ws';
  import { goto } from '$app/navigation';

  const state = $derived($appStore);
  const photos = $derived(state.photos);
  const url = $derived(photos?.url ?? null);
  const index = $derived(photos?.index ?? 0);
  const total = $derived(photos?.total ?? 0);
  const rotation = $derived(photos?.rotation_seconds ?? 30);
  const source = $derived(photos?.source ?? 'local');
  const progress = $derived(total > 0 ? (index + 1) / total : 0);
</script>

<div class="photo-screen">
  {#if url}
    <img src={url} alt="Photo {index + 1}" class="photo-img" />
  {:else}
    <div class="photo-placeholder"></div>
  {/if}

  <div class="chrome-top">
    <button type="button" class="chrome-home" onclick={() => goto('/')}>O—DECK / PHOTO</button>
    <span>{index + 1} of {total} · auto-rotate {rotation}s · ◐</span>
  </div>

  <div class="caption">
    [{source.replace('_', ' ')}]
  </div>
  <div class="progress-bar" style:width="{(progress * 100).toFixed(1)}%"></div>
</div>

<style>
  .photo-screen {
    width: 100vw;
    height: 100vh;
    background: #0a0908;
    position: relative;
    overflow: hidden;
    font-family: var(--font-mono);
    color: var(--ink);
  }
  .photo-img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
  }
  .photo-placeholder {
    width: 100%;
    height: 100%;
    background:
      repeating-linear-gradient(118deg, rgba(255, 255, 255, 0.02) 0 2px, transparent 2px 8px),
      radial-gradient(70% 60% at 30% 40%, #d49a8e 0%, transparent 60%),
      linear-gradient(180deg, #c8a377 0%, #6b4838 100%);
  }
  .chrome-top {
    position: absolute;
    top: 14px;
    left: 18px;
    right: 18px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 9px;
    color: rgba(255, 255, 255, 0.55);
    letter-spacing: 1.5px;
  }
  .chrome-home {
    background: none;
    border: none;
    color: rgba(255, 255, 255, 0.55);
    font-family: var(--font-mono);
    font-size: 9px;
    letter-spacing: 1.5px;
    cursor: pointer;
    padding: 0;
  }
  .caption {
    position: absolute;
    bottom: 16px;
    left: 50%;
    transform: translateX(-50%);
    font-size: 10px;
    color: rgba(255, 255, 255, 0.55);
    letter-spacing: 2px;
    padding: 4px 10px;
    background: rgba(0, 0, 0, 0.25);
    border-radius: 4px;
    backdrop-filter: blur(6px);
  }
  .progress-bar {
    position: absolute;
    bottom: 0;
    left: 0;
    height: 1px;
    background: rgba(255, 255, 255, 0.4);
  }
</style>
