<script lang="ts">
  let {
    items = [],
    color = 'currentColor',
    opacity = 0.72,
    fontSize = 11,
  }: {
    items?: string[];
    color?: string;
    opacity?: number;
    fontSize?: number;
  } = $props();

</script>

<div
  class="ticker"
  style:--ticker-color={color}
  style:--ticker-opacity={opacity}
  style:--ticker-size={`${fontSize}px`}
>
  <div class="ticker-track">
    <div class="ticker-group">
      {#each items as item}
        <span>{item}</span>
      {/each}
    </div>
    <div class="ticker-group" aria-hidden="true">
      {#each items as item}
        <span>{item}</span>
      {/each}
    </div>
  </div>
</div>

<style>
  .ticker {
    width: 100%;
    overflow: hidden;
    color: var(--ticker-color);
    font-family: var(--font-mono);
    font-size: var(--ticker-size);
    letter-spacing: 0.12em;
    opacity: var(--ticker-opacity);
    text-transform: uppercase;
    white-space: nowrap;
    mask-image: linear-gradient(90deg, transparent, #000 12%, #000 88%, transparent);
  }

  .ticker :global(.ticker-track) {
    display: inline-flex;
    min-width: max-content;
    animation: ticker-loop 24s linear infinite;
    will-change: transform;
  }

  .ticker-group {
    display: inline-flex;
    flex: 0 0 auto;
    gap: 24px;
    padding-right: 24px;
  }

  .ticker-group span {
    flex: 0 0 auto;
  }

  @keyframes ticker-loop {
    from {
      transform: translateX(0);
    }

    to {
      transform: translateX(-50%);
    }
  }
</style>
