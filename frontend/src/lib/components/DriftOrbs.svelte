<script lang="ts">
  type Mode = 'calm' | 'music' | 'rain' | 'thunder';

  type Orb = {
    bx: number;
    by: number;
    r: number;
    vx: number;
    vy: number;
    color: string;
    phase: number;
    ampX: number;
    ampY: number;
  };

  let {
    palette = ['#e6c89b', '#a8c19a', '#7a5f4a', '#5a6a78'],
    mode = 'calm',
    count = 6,
  }: {
    palette?: string[];
    mode?: Mode;
    count?: number;
  } = $props();

  let canvas: HTMLCanvasElement | undefined;

  const alphaHex = (alpha: number) =>
    Math.round(Math.max(0, Math.min(1, alpha)) * 255)
      .toString(16)
      .padStart(2, '0');

  const withAlpha = (color: string, alpha: number) => {
    if (/^#[0-9a-f]{6}$/i.test(color)) return `${color}${alphaHex(alpha)}`;
    if (/^#[0-9a-f]{3}$/i.test(color)) {
      const [, r, g, b] = color;
      return `#${r}${r}${g}${g}${b}${b}${alphaHex(alpha)}`;
    }
    return color;
  };

  $effect(() => {
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const colors = palette.length > 0 ? palette : ['#e6c89b'];
    let width = 1;
    let height = 1;
    let raf = 0;
    let t = 0;
    let flash = 0;
    let last = performance.now();

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

    const orbs: Orb[] = Array.from({ length: Math.max(0, count) }, (_, index) => ({
      bx: Math.random() * width,
      by: Math.random() * height,
      r: 90 + Math.random() * 140,
      vx: (Math.random() - 0.5) * 0.18,
      vy: (Math.random() - 0.5) * 0.14,
      color: colors[index % colors.length],
      phase: Math.random() * Math.PI * 2,
      ampX: 30 + Math.random() * 50,
      ampY: 20 + Math.random() * 40,
    }));

    const observer = new ResizeObserver(resize);
    observer.observe(canvas);

    const step = (now: number) => {
      const dt = Math.min(50, now - last);
      last = now;
      t += dt * 0.001;

      ctx.globalCompositeOperation = 'source-over';
      ctx.globalAlpha = 1;
      ctx.clearRect(0, 0, width, height);

      const speedMul = mode === 'thunder' ? 2.4 : mode === 'rain' ? 1.3 : mode === 'music' ? 1.5 : 1;
      const alphaMul = mode === 'rain' ? 0.6 : mode === 'thunder' ? 1.1 : 1;

      if (mode === 'thunder') {
        if (Math.random() < 0.005) flash = 1;
        if (flash > 0.01) {
          ctx.fillStyle = `rgba(220, 200, 220, ${flash * 0.18})`;
          ctx.fillRect(0, 0, width, height);
          flash *= 0.78;
        }
      }

      ctx.globalCompositeOperation = 'screen';

      for (const orb of orbs) {
        orb.bx += orb.vx * speedMul;
        orb.by += orb.vy * speedMul;

        if (orb.bx < -orb.r) orb.bx = width + orb.r;
        if (orb.bx > width + orb.r) orb.bx = -orb.r;
        if (orb.by < -orb.r) orb.by = height + orb.r;
        if (orb.by > height + orb.r) orb.by = -orb.r;

        const x = orb.bx + Math.sin(t * 0.3 + orb.phase) * orb.ampX;
        const y = orb.by + Math.cos(t * 0.27 + orb.phase) * orb.ampY;
        const breath = mode === 'music' ? 1 + Math.max(0, Math.sin(t * 4.2 + orb.phase)) * 0.18 : 1;
        const radius = orb.r * breath;
        const gradient = ctx.createRadialGradient(x, y, 0, x, y, radius);

        gradient.addColorStop(0, withAlpha(orb.color, 0.34));
        gradient.addColorStop(0.4, withAlpha(orb.color, 0.12));
        gradient.addColorStop(1, withAlpha(orb.color, 0));

        ctx.globalAlpha = 0.55 * alphaMul;
        ctx.fillStyle = gradient;
        ctx.beginPath();
        ctx.arc(x, y, radius, 0, Math.PI * 2);
        ctx.fill();
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

<canvas bind:this={canvas} class="drift-orbs" aria-hidden="true"></canvas>

<style>
  .drift-orbs {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    pointer-events: none;
    filter: blur(36px);
    opacity: 0.85;
  }
</style>
