<script lang="ts">
  let {
    count = 4,
    color = 'currentColor',
    size = 10,
    width = 2,
  }: {
    count?: number;
    color?: string;
    size?: number;
    width?: number;
  } = $props();

  const bars = $derived(Array.from({ length: Math.max(0, count) }, (_, index) => index));
</script>

<span
  class="eq"
  style:--eq-color={color}
  style:--eq-size={`${size}px`}
  style:--eq-width={`${width}px`}
  aria-hidden="true"
>
  {#each bars as bar}
    <span class="eq-bar" style:animation-delay={`${bar * -0.17}s`}></span>
  {/each}
</span>

<style>
  .eq {
    display: inline-flex;
    align-items: end;
    gap: max(1px, calc(var(--eq-width) * 0.8));
    height: var(--eq-size);
    color: var(--eq-color);
    vertical-align: middle;
  }

  .eq :global(.eq-bar) {
    display: block;
    width: var(--eq-width);
    height: var(--eq-size);
    border-radius: 999px;
    background: currentColor;
    animation: eq-pulse 1.1s ease-in-out infinite;
    transform-origin: center bottom;
  }

  @keyframes -global-eq-pulse {
    0%,
    100% {
      transform: scaleY(0.28);
    }

    50% {
      transform: scaleY(1);
    }
  }
</style>
