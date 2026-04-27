import type { Config } from 'tailwindcss';

export default {
  theme: {
    extend: {
      colors: {
        bg: '#15130f',
        'bg-raised': 'rgba(31,28,24,0.78)',
        'bg-solid': '#1f1c18',
        ink: '#f0e8d6',
        'ink-dim': 'rgba(240,232,214,0.55)',
        'ink-sub': 'rgba(240,232,214,0.32)',
        sand: '#e6c89b',
        sage: '#a8c19a',
        rose: '#d49a8e',
        lav: '#a08fb3',
        line: 'rgba(240,232,214,0.08)'
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['IBM Plex Mono', 'monospace']
      }
    }
  }
} satisfies Config;
