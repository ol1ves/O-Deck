<script lang="ts">
  type SparkPoint = {
    h: number;
    t: number;
  };

  let {
    points = [],
    color = 'currentColor',
    width = 120,
    height = 28,
  }: {
    points?: SparkPoint[];
    color?: string;
    width?: number;
    height?: number;
  } = $props();

  const path = $derived.by(() => {
    if (points.length < 2) return '';

    const values = points.map((point) => point.h);
    const min = Math.min(...values);
    const max = Math.max(...values);
    const range = max - min || 1;
    const last = points.length - 1;

    return points
      .map((point, index) => {
        const x = (index / last) * width;
        const y = height - ((point.h - min) / range) * height;
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
</svg>

<style>
  .sparkline {
    display: block;
    overflow: visible;
  }
</style>
