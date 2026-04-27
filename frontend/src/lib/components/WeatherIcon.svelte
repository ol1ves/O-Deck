<script lang="ts">
  type WeatherKind = 'cloud-sun' | 'sun' | 'cloud' | 'rain' | 'snow' | string;

  let {
    kind = 'cloud-sun',
    size = 28,
    stroke = 'currentColor',
  }: {
    kind?: WeatherKind;
    size?: number;
    stroke?: string;
  } = $props();
</script>

<svg
  class="weather-icon"
  width={size}
  height={size}
  viewBox="0 0 32 32"
  fill="none"
  stroke={stroke}
  stroke-width="2"
  stroke-linecap="round"
  stroke-linejoin="round"
  role="img"
  aria-label={kind}
>
  {#if kind === 'cloud-sun'}
    <circle cx="11" cy="10" r="4" opacity="0.85" />
    <path d="M11 2.5v2" />
    <path d="M11 15.5v2" />
    <path d="m5.7 4.7 1.4 1.4" />
    <path d="m14.9 13.9 1.4 1.4" />
    <path d="M3.5 10h2" />
    <path d="M16.5 10h2" />
    <path d="M12 24h11a5 5 0 0 0 .8-9.9 7 7 0 0 0-13.3 2.2A3.9 3.9 0 0 0 12 24Z" />
  {:else if kind === 'sun'}
    <circle cx="16" cy="16" r="5.5" />
    <path d="M16 3v3" />
    <path d="M16 26v3" />
    <path d="m6.8 6.8 2.1 2.1" />
    <path d="m23.1 23.1 2.1 2.1" />
    <path d="M3 16h3" />
    <path d="M26 16h3" />
    <path d="m6.8 25.2 2.1-2.1" />
    <path d="m23.1 8.9 2.1-2.1" />
  {:else if kind === 'cloud'}
    <path d="M9.5 24h13a6 6 0 0 0 .8-11.9A8 8 0 0 0 8 14.8 4.7 4.7 0 0 0 9.5 24Z" />
  {:else if kind === 'rain'}
    <path d="M9.5 20h13a6 6 0 0 0 .8-11.9A8 8 0 0 0 8 10.8 4.7 4.7 0 0 0 9.5 20Z" />
    <path d="m10 25-1 3" />
    <path d="m16 24-1 4" />
    <path d="m22 25-1 3" />
  {:else if kind === 'snow'}
    <path d="M9.5 19h13a6 6 0 0 0 .8-11.9A8 8 0 0 0 8 9.8 4.7 4.7 0 0 0 9.5 19Z" />
    <path d="M11 25h4" />
    <path d="m13 23-2 4" />
    <path d="m13 23 2 4" />
    <path d="M20 25h4" />
    <path d="m22 23-2 4" />
    <path d="m22 23 2 4" />
  {:else}
    <circle cx="16" cy="16" r="9" />
  {/if}
</svg>

<style>
  .weather-icon {
    display: inline-block;
    overflow: visible;
    vertical-align: middle;
  }
</style>
