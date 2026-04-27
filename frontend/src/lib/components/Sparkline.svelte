<script lang="ts">
  type SparkPoint = {
    h: string;
    t: number;
  };

  let {
    points = [],
    color = 'currentColor',
    width = 120,
    height = 28,
    nowLabel = '',
    endLabel = '',
  }: {
    points?: SparkPoint[];
    color?: string;
    width?: number;
    height?: number;
    nowLabel?: string;
    endLabel?: string;
  } = $props();

  const path = $derived.by(() => {
    if (points.length < 2) return '';

    const values = points.map((point) => point.t);
    const min = Math.min(...values);
    const max = Math.max(...values);
    const range = max - min || 1;
    const last = points.length - 1;

    return points
      .map((point, index) => {
        const x = (index / last) * width;
        const y = height - ((point.t - min) / range) * height;
        return `${index === 0 ? 'M' : 'L'} ${x.toFixed(2)} ${y.toFixed(2)}`;
      })
      .join(' ');
  });
</script>

<svg
  class="sparkline"
  width={width}
  height={height}
  viewBox={`0 0 ${width} ${height}`}
  fill="none"
  aria-hidden="true"
>
  <path d={path} stroke={color} stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
  {#if nowLabel}
    <text x="0" y={height - 1} font-size="8" fill="var(--ink-dim)" font-family="var(--font-mono)">
      {nowLabel}
    </text>
  {/if}
  {#if endLabel}
    <text
      x={width}
      y={height - 1}
      text-anchor="end"
      font-size="8"
      fill="var(--ink-dim)"
      font-family="var(--font-mono)"
    >
      {endLabel}
    </text>
  {/if}
</svg>

<style>
  .sparkline {
    display: block;
    overflow: visible;
  }
</style>
