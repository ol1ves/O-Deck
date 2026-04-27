<script lang="ts">
  type AlbumPalette = {
    dom: string;
    accent: string;
    ink: string;
  };

  const fallbackPalette: AlbumPalette = {
    dom: '#1f1c18',
    accent: '#e6c89b',
    ink: '#f0e8d6',
  };

  const clamp = (value: number) => Math.max(0, Math.min(255, value));

  const normalizeHex = (hex: string) => {
    const value = hex.trim().replace(/^#/, '');
    if (/^[0-9a-fA-F]{3}$/.test(value)) {
      return value
        .split('')
        .map((part) => part + part)
        .join('');
    }

    if (/^[0-9a-fA-F]{6}$/.test(value)) return value;
    return null;
  };

  const shade = (hex: string, amount: number) => {
    const normalized = normalizeHex(hex);
    if (!normalized) return hex;

    const channel = (start: number) => clamp(parseInt(normalized.slice(start, start + 2), 16) + amount);
    return `#${[channel(0), channel(2), channel(4)]
      .map((value) => value.toString(16).padStart(2, '0'))
      .join('')}`;
  };

  let {
    palette = fallbackPalette,
    size = 170,
    label = '',
    glyph = '◊',
    artUrl = null,
  }: {
    palette?: AlbumPalette;
    size?: number;
    label?: string;
    glyph?: string;
    artUrl?: string | null;
  } = $props();

  const dom = $derived(palette.dom || fallbackPalette.dom);
  const accent = $derived(palette.accent || fallbackPalette.accent);
  const ink = $derived(palette.ink || fallbackPalette.ink);
  const shadow = $derived(shade(dom, -34));
  const glow = $derived(shade(accent, 26));
</script>

<figure
  class="album-art"
  style:--album-size={`${size}px`}
  style:--album-dom={dom}
  style:--album-accent={accent}
  style:--album-ink={ink}
  style:--album-shadow={shadow}
  style:--album-glow={glow}
  aria-label={label || 'album art'}
>
  {#if artUrl}
    <img src={artUrl} alt={label || 'album art'} />
  {:else}
    <div class="album-art__orb album-art__orb--one"></div>
    <div class="album-art__orb album-art__orb--two"></div>
    <div class="album-art__glyph" aria-hidden="true">{glyph}</div>
    {#if label}
      <figcaption>{label}</figcaption>
    {/if}
  {/if}
</figure>

<style>
  .album-art {
    position: relative;
    display: grid;
    place-items: center;
    width: var(--album-size);
    height: var(--album-size);
    margin: 0;
    overflow: hidden;
    border: 1px solid color-mix(in srgb, var(--album-ink) 18%, transparent);
    border-radius: 22px;
    background:
      radial-gradient(circle at 28% 24%, color-mix(in srgb, var(--album-glow) 68%, transparent), transparent 28%),
      radial-gradient(circle at 72% 70%, color-mix(in srgb, var(--album-accent) 54%, transparent), transparent 34%),
      linear-gradient(135deg, var(--album-dom), var(--album-shadow));
    box-shadow:
      inset 0 1px 0 color-mix(in srgb, var(--album-ink) 18%, transparent),
      0 18px 46px color-mix(in srgb, var(--album-shadow) 48%, transparent);
    color: var(--album-ink);
    isolation: isolate;
  }

  .album-art img {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }

  .album-art__orb {
    position: absolute;
    border-radius: 999px;
    filter: blur(0.5px);
    opacity: 0.78;
  }

  .album-art__orb--one {
    top: 18%;
    left: 15%;
    width: 46%;
    height: 46%;
    background: color-mix(in srgb, var(--album-accent) 58%, transparent);
  }

  .album-art__orb--two {
    right: 12%;
    bottom: 10%;
    width: 58%;
    height: 58%;
    background: color-mix(in srgb, var(--album-ink) 12%, transparent);
  }

  .album-art__glyph {
    position: relative;
    z-index: 1;
    color: color-mix(in srgb, var(--album-ink) 82%, transparent);
    font-family: var(--font-mono);
    font-size: calc(var(--album-size) * 0.34);
    line-height: 1;
    text-shadow: 0 0 24px color-mix(in srgb, var(--album-accent) 58%, transparent);
  }

  figcaption {
    position: absolute;
    right: 14px;
    bottom: 12px;
    left: 14px;
    z-index: 1;
    overflow: hidden;
    color: color-mix(in srgb, var(--album-ink) 72%, transparent);
    font-family: var(--font-mono);
    font-size: 10px;
    letter-spacing: 0.14em;
    text-align: center;
    text-overflow: ellipsis;
    text-transform: uppercase;
    white-space: nowrap;
  }
</style>
