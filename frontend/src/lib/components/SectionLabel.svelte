<script lang="ts">
  import type { Snippet } from 'svelte';

  let {
    accent = 'var(--ink-dim)',
    children,
  }: {
    accent?: string;
    children?: Snippet;
  } = $props();
</script>

<div class="section-label" style:color={accent}>
  <span class="section-label__text">{@render children?.()}</span>
  <span class="section-label__rule" aria-hidden="true"></span>
</div>

<style>
  .section-label {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 9px;
    font-family: var(--font-mono);
    font-size: 10px;
    letter-spacing: 1.5px;
    text-transform: uppercase;
  }

  .section-label__text {
    flex: 0 0 auto;
  }

  .section-label__rule {
    flex: 1;
    height: 1px;
    background: var(--line);
  }
</style>
