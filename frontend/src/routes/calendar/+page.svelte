<script lang="ts">
  import { appStore } from '$lib/ws';
  import ODScreen from '$lib/components/ODScreen.svelte';
  import ODStatusBar from '$lib/components/ODStatusBar.svelte';
  import ODDock from '$lib/components/ODDock.svelte';
  import SectionLabel from '$lib/components/SectionLabel.svelte';

  const state = $derived($appStore);
  const calendar = $derived(state.calendar);
  const mode = $derived(state.motionMode);
  const events = $derived(calendar?.events ?? []);

  const today = new Date();
  const weekDays = ['M', 'T', 'W', 'T', 'F', 'S', 'S'];
  const todayDow = (today.getDay() + 6) % 7;

  const HOURS = Array.from({ length: 13 }, (_, i) => {
    const h = i + 9;
    return h < 12 ? `${h} AM` : h === 12 ? '12 PM' : `${h - 12} PM`;
  });
  const SLOT_PX = 32;
  const START_H = 9;

  function eventTop(timeStr: string): number {
    const [h, m] = timeStr.split(':').map(Number);
    let h24 = h;
    if (h < 9) h24 = h + 12;
    return (h24 - START_H) * SLOT_PX + (m / 60) * SLOT_PX;
  }

  function eventHeight(durStr: string): number {
    const hMatch = durStr.match(/(\d+)h/);
    const mMatch = durStr.match(/(\d+)m/);
    const totalMin = (hMatch ? parseInt(hMatch[1]) * 60 : 0) + (mMatch ? parseInt(mMatch[1]) : 0);
    return (totalMin / 60) * SLOT_PX;
  }

  const nowTop = (() => {
    const n = new Date();
    return (n.getHours() + n.getMinutes() / 60 - START_H) * SLOT_PX;
  })();

  const nowStr = new Date().toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false
  });
</script>

<ODScreen {mode}>
  <ODStatusBar app="CALENDAR · TODAY · {events.length} events" />

  <main class="cal-grid">
    <div class="day-col">
      <SectionLabel
        >// {today
          .toLocaleDateString('en-US', { weekday: 'long', month: 'short', day: 'numeric' })
          .toUpperCase()}</SectionLabel
      >
      <div class="timeline-wrap">
        {#each HOURS as h, i}
          <div class="hour-slot" style="top:{i * SLOT_PX}px">
            <span class="hour-label">{h}</span>
          </div>
        {/each}

        {#if nowTop >= 0 && nowTop < HOURS.length * SLOT_PX}
          <div class="now-line" style="top:{nowTop}px">
            <div class="now-dot"></div>
            <div class="now-label">{nowStr}</div>
          </div>
        {/if}

        {#each events as event}
          <div
            class="event-block"
            style="
              top:{eventTop(event.time)}px;
              height:{Math.max(eventHeight(event.duration) - 2, 20)}px;
              background:{event.color}22;
              border-left:3px solid {event.color};
            "
          >
            <div class="event-title">{event.title}</div>
            <div class="event-meta">
              {event.time} · {event.duration} · {event.location.toLowerCase()}
              {#if event.notion}
                <span style="color:var(--sand)"> · notion/{event.notion.project}</span>
              {/if}
            </div>
          </div>
        {/each}
      </div>
    </div>

    <div class="right-col">
      <div>
        <SectionLabel>// WEEK</SectionLabel>
        <div class="week-grid">
          {#each weekDays as d, i}
            <div class="week-cell" class:today={i === todayDow}>
              <div style="font-size:9px;color:var(--ink-dim);letter-spacing:1px">{d}</div>
              <div class="week-num" class:today={i === todayDow}>{today.getDate() - todayDow + i}</div>
            </div>
          {/each}
        </div>
      </div>

      <div class="agenda">
        <SectionLabel>// UP NEXT{calendar?.next_in ? ' · ' + calendar.next_in : ''}</SectionLabel>
        {#each events as event, i}
          <div class="agenda-row" class:last={i === events.length - 1}>
            <div>
              <div class="agenda-time">{event.time}</div>
              <div
                style="font-size:9px;color:var(--ink-sub);letter-spacing:1px;font-family:var(--font-mono);margin-top:1px"
              >
                {event.duration}
              </div>
            </div>
            <div>
              <div class="agenda-title">{event.title}</div>
              <div style="font-size:10px;color:var(--ink-dim);margin-top:2px;letter-spacing:0.4px">
                {event.location.toLowerCase()}
                {#if event.notion}
                  <span style="color:var(--sand)">
                    · notion/{event.notion.project} · {event.notion.status.toLowerCase()}</span
                  >
                {/if}
              </div>
            </div>
          </div>
        {/each}
      </div>
    </div>
  </main>

  <ODDock active="HOME" />
</ODScreen>

<style>
  .cal-grid {
    flex: 1;
    display: grid;
    grid-template-columns: 1.2fr 1fr;
    gap: 24px;
    min-height: 0;
    overflow: hidden;
  }
  .day-col {
    display: flex;
    flex-direction: column;
    min-height: 0;
  }
  .timeline-wrap {
    position: relative;
    flex: 1;
    overflow: hidden;
  }
  .hour-slot {
    position: absolute;
    left: 0;
    right: 0;
    height: 32px;
    display: flex;
    align-items: flex-start;
    gap: 10px;
    border-top: 1px solid var(--line);
  }
  .hour-label {
    font-size: 9px;
    color: var(--ink-sub);
    letter-spacing: 1px;
    padding-top: 3px;
    width: 42px;
    font-family: var(--font-mono);
  }
  .now-line {
    position: absolute;
    left: 42px;
    right: 0;
    height: 1px;
    background: var(--rose);
    z-index: 3;
  }
  .now-dot {
    position: absolute;
    left: -6px;
    top: -4px;
    width: 8px;
    height: 8px;
    border-radius: 8px;
    background: var(--rose);
  }
  .now-label {
    position: absolute;
    right: 0;
    top: -14px;
    font-size: 9px;
    color: var(--rose);
    letter-spacing: 1px;
    font-family: var(--font-mono);
    background: var(--bg);
    padding: 0 6px;
  }
  .event-block {
    position: absolute;
    left: 54px;
    right: 0;
    border-radius: 6px;
    padding: 5px 9px;
    display: flex;
    flex-direction: column;
    justify-content: flex-start;
    overflow: hidden;
  }
  .event-title {
    font-family: var(--font-sans);
    font-size: 13px;
    font-weight: 500;
    color: var(--ink);
    line-height: 1.2;
  }
  .event-meta {
    font-family: var(--font-mono);
    font-size: 9px;
    color: var(--ink-dim);
    letter-spacing: 0.8px;
    margin-top: 1px;
  }
  .right-col {
    display: flex;
    flex-direction: column;
    gap: 14px;
    min-height: 0;
  }
  .week-grid {
    display: grid;
    grid-template-columns: repeat(7, 1fr);
    gap: 4px;
  }
  .week-cell {
    aspect-ratio: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    background: rgba(240, 232, 214, 0.04);
    border: 1px solid var(--line);
    border-radius: 6px;
  }
  .week-cell.today {
    background: rgba(212, 154, 142, 0.12);
    border-color: rgba(212, 154, 142, 0.33);
  }
  .week-num {
    font-family: var(--font-sans);
    font-size: 18px;
    font-weight: 400;
    color: var(--ink);
    font-variant-numeric: tabular-nums;
    letter-spacing: -0.5px;
  }
  .week-num.today {
    font-weight: 600;
    color: var(--rose);
  }
  .agenda {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-height: 0;
  }
  .agenda-row {
    display: grid;
    grid-template-columns: 58px 1fr;
    gap: 12px;
    padding-bottom: 10px;
    border-bottom: 1px dashed var(--line);
    margin-bottom: 10px;
  }
  .agenda-row.last {
    border-bottom: none;
    margin-bottom: 0;
  }
  .agenda-time {
    font-family: var(--font-sans);
    font-size: 14px;
    font-weight: 500;
    color: var(--ink);
    font-variant-numeric: tabular-nums;
    letter-spacing: -0.3px;
  }
  .agenda-title {
    font-family: var(--font-sans);
    font-size: 13px;
    font-weight: 500;
    color: var(--ink);
    line-height: 1.2;
  }
</style>
