<script lang="ts">
  const yellowLines = new Set(['N', 'Q', 'R', 'W']);

  let {
    line,
    color,
    size = 22,
  }: {
    line: string;
    color: string;
    size?: number;
  } = $props();

  const foreground = $derived(yellowLines.has(line.toUpperCase()) ? '#19160f' : '#ffffff');
</script>

<span
  class="pill"
  style:--pill-color={color}
  style:--pill-foreground={foreground}
  style:--pill-size={`${size}px`}
  aria-label={`${line} train`}
>
  {line}
</span>

<style>
  .pill {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: var(--pill-size);
    height: var(--pill-size);
    border-radius: 999px;
    background: var(--pill-color);
    color: var(--pill-foreground);
    font-family: var(--font-mono);
    font-size: calc(var(--pill-size) * 0.48);
    font-weight: 700;
    line-height: 1;
    letter-spacing: -0.08em;
    text-transform: uppercase;
  }
</style>
