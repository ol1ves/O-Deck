<script lang="ts">
  import { goto } from '$app/navigation';

  type DockItem = {
    key: string;
    glyph: string;
    href: string;
  };

  let {
    active = 'HOME',
  }: {
    active?: string;
  } = $props();

  const items: DockItem[] = [
    { key: 'HOME', glyph: '⌂', href: '/' },
    { key: 'POMO', glyph: '◑', href: '/pomodoro' },
    { key: 'GH', glyph: '◇', href: '/github' },
    { key: 'MAP', glyph: '▤', href: '/subway' },
    { key: 'DOOM', glyph: '□', href: '/doomscroll' },
    { key: 'PHOTO', glyph: '◐', href: '/photos' },
    { key: 'SHOW', glyph: '✦', href: '/showcase' },
  ];

  const handleClick = (event: MouseEvent, href: string) => {
    if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    void goto(href);
  };
</script>

<footer class="od-dock" aria-label="O-DECK dock">
  <nav class="od-dock__items">
    {#each items as item}
      <a
        class:od-dock__item--active={active === item.key}
        class="od-dock__item dock-btn"
        href={item.href}
        aria-current={active === item.key ? 'page' : undefined}
        onclick={(event) => handleClick(event, item.href)}
      >
        <span class="od-dock__dot" aria-hidden="true"></span>
        <span class="od-dock__glyph" aria-hidden="true">{item.glyph}</span>
        <span>{item.key}</span>
      </a>
    {/each}
  </nav>
  <span class="od-dock__hint">tap <span>⌂</span> for home</span>
</footer>

<style>
  .od-dock {
    display: flex;
    align-items: center;
    gap: 14px;
    padding-top: 10px;
    border-top: 1px solid var(--line);
    color: var(--ink-dim);
    font-family: var(--font-mono);
    font-size: 10px;
    letter-spacing: 1.5px;
    text-transform: uppercase;
  }

  .od-dock__items {
    display: flex;
    align-items: center;
    gap: 14px;
    min-width: 0;
  }

  .od-dock__item {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    color: var(--ink-dim);
    text-decoration: none;
    transition:
      color 140ms ease,
      opacity 140ms ease;
  }

  .od-dock__item:hover,
  .od-dock__item:focus-visible,
  .od-dock__item--active {
    color: var(--ink);
  }

  .od-dock__item:focus-visible {
    outline: 1px solid var(--sand);
    outline-offset: 4px;
  }

  .od-dock__dot {
    width: 5px;
    height: 5px;
    border-radius: 999px;
    background: rgba(240, 232, 214, 0.25);
  }

  .od-dock__glyph {
    margin-right: 2px;
    color: var(--ink-dim);
  }

  .od-dock__item--active .od-dock__dot {
    background: var(--sand);
  }

  .od-dock__item--active .od-dock__glyph,
  .od-dock__hint span {
    color: var(--sand);
  }

  .od-dock__hint {
    margin-left: auto;
    color: var(--ink-sub);
    white-space: nowrap;
  }
</style>
