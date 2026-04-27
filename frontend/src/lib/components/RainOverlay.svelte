<script lang="ts">
  type Drop = {
    x: number;
    y: number;
    vy: number;
    len: number;
  };

  let {
    intensity = 0.5,
    color = '#aac0d6',
  }: {
    intensity?: number;
    color?: string;
  } = $props();

  let canvas: HTMLCanvasElement | undefined;

  $effect(() => {
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let width = 1;
    let height = 1;
    let raf = 0;

    const resize = () => {
      const rect = canvas.getBoundingClientRect();
      const dpr = Math.min(window.devicePixelRatio || 1, 1.5);
      width = Math.max(1, rect.width);
      height = Math.max(1, rect.height);
      canvas.width = Math.max(1, Math.floor(width * dpr));
      canvas.height = Math.max(1, Math.floor(height * dpr));
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };

    resize();

    const dropCount = Math.max(0, Math.floor(60 * intensity));
    const drops: Drop[] = Array.from({ length: dropCount }, () => ({
      x: Math.random() * width,
      y: Math.random() * height,
      vy: 1.2 + Math.random() * 1.4,
      len: 8 + Math.random() * 14,
    }));

    const observer = new ResizeObserver(resize);
    observer.observe(canvas);

    const step = () => {
      ctx.clearRect(0, 0, width, height);
      ctx.strokeStyle = color;
      ctx.lineWidth = 0.7;
      ctx.globalAlpha = 0.35;

      for (const drop of drops) {
        drop.y += drop.vy;
        drop.x -= 0.3;

        if (drop.y > height) {
          drop.y = -10;
          drop.x = Math.random() * width;
        }

        if (drop.x < 0) drop.x = width;

        ctx.beginPath();
        ctx.moveTo(drop.x, drop.y);
        ctx.lineTo(drop.x + 1.5, drop.y + drop.len);
        ctx.stroke();
      }

      ctx.globalAlpha = 1;
      raf = requestAnimationFrame(step);
    };

    raf = requestAnimationFrame(step);

    return () => {
      cancelAnimationFrame(raf);
      observer.disconnect();
    };
  });
</script>

<canvas bind:this={canvas} class="rain-overlay" aria-hidden="true"></canvas>

<style>
  .rain-overlay {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    pointer-events: none;
  }
</style>
