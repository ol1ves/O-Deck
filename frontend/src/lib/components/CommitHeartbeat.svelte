<script lang="ts">
  let {
    color = 'currentColor',
    count = 36,
    barWidth = 2,
    maxHeight = 16,
  }: {
    color?: string;
    count?: number;
    barWidth?: number;
    maxHeight?: number;
  } = $props();

  const bars = $derived.by(() =>
    Array.from({ length: Math.max(0, count) }, (_, index) => {
      const wave = Math.sin(index * 1.7) * 0.5 + 0.5;
      const jitter = ((index * 37) % 11) / 10;
      const brightness = 0.28 + (index / Math.max(1, count - 1)) * 0.62;

      return {
        height: Math.max(2, Math.round(maxHeight * (0.22 + wave * 0.48 + jitter * 0.18))),
        opacity: brightness.toFixed(2),
      };
    }),
  );
</script>

<span
  class="commit-heartbeat"
  style:--heartbeat-color={color}
  style:--heartbeat-width={`${barWidth}px`}
  style:--heartbeat-height={`${maxHeight}px`}
  aria-hidden="true"
>
  {#each bars as bar}
    <span style:height={`${bar.height}px`} style:opacity={bar.opacity}></span>
  {/each}
</span>

<style>
  .commit-heartbeat {
    display: inline-flex;
    align-items: end;
    gap: max(1px, calc(var(--heartbeat-width) * 0.8));
    height: var(--heartbeat-height);
    color: var(--heartbeat-color);
    vertical-align: middle;
  }

  .commit-heartbeat span {
    width: var(--heartbeat-width);
    border-radius: 999px;
    background: currentColor;
  }
</style>
