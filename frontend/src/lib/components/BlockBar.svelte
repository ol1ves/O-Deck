<script lang="ts">
  let {
    value = 0,
    width = 6,
    color = 'currentColor',
  }: {
    value?: number;
    width?: number;
    color?: string;
  } = $props();

  const blocks = $derived(Array.from({ length: Math.max(0, width) }, (_, index) => index));
  const activeCount = $derived(Math.max(0, Math.min(width, Math.round(value * width))));
</script>

<span
  class="block-bar"
  style:--block-color={color}
  aria-label={`${activeCount} of ${width} blocks active`}
>
  {#each blocks as block}
    <span class:block-bar__block--active={block < activeCount}></span>
  {/each}
</span>

<style>
  .block-bar {
    display: inline-flex;
    align-items: center;
    gap: 2px;
    color: var(--block-color);
    vertical-align: middle;
  }

  .block-bar span {
    width: 5px;
    height: 9px;
    border: 1px solid currentColor;
    opacity: 0.28;
  }

  .block-bar__block--active {
    background: currentColor;
    opacity: 0.9;
  }
</style>
