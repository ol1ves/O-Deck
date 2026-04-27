<script lang="ts">
  let {
    color = 'var(--sage)',
    series = [] as number[],
    bars = 36,
    height = 14
  }: {
    color?: string;
    series?: number[];
    bars?: number;
    height?: number;
  } = $props();

  const padded = $derived.by(() => {
    if (series.length >= bars) return series.slice(-bars);
    return Array(bars - series.length).fill(0).concat(series) as number[];
  });

  const max = $derived.by(() => Math.max(1, ...padded));
</script>

<div
  class="heartbeat"
  style:--hb-color={color}
  style:height={`${height}px`}
  aria-hidden="true"
>
  {#each padded as value}
    <span
      class="bar"
      class:zero={value === 0}
      style:height={`${Math.max(2, (value / max) * height)}px`}
      style:opacity={value === 0 ? 0.18 : 0.55 + (value / max) * 0.45}
    ></span>
  {/each}
</div>

<style>
  .heartbeat {
    display: inline-flex;
    align-items: flex-end;
    gap: 2px;
    vertical-align: middle;
  }

  .bar {
    width: 2px;
    background: var(--hb-color);
    border-radius: 1px;
  }

  .bar.zero {
    background: var(--ink-sub);
  }
</style>
