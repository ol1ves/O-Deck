<script lang="ts">
  import { appStore } from '$lib/ws';
  import ODScreen from '$lib/components/ODScreen.svelte';
  import ODStatusBar from '$lib/components/ODStatusBar.svelte';
  import ODDock from '$lib/components/ODDock.svelte';
  import SectionLabel from '$lib/components/SectionLabel.svelte';
  import CommitHeartbeat from '$lib/components/CommitHeartbeat.svelte';

  const state = $derived($appStore);
  const gh = $derived(state.github);
  const mode = $derived(state.motionMode);

  function labelColor(label: string): string {
    if (label === 'bug') return 'var(--rose)';
    if (label === 'feat') return 'var(--lav)';
    return 'var(--sand)';
  }
  function labelBg(label: string): string {
    if (label === 'bug') return 'rgba(212,154,142,0.12)';
    if (label === 'feat') return 'rgba(160,143,179,0.12)';
    return 'rgba(230,200,155,0.12)';
  }
  function prStatusColor(status: string): string {
    return status === 'review' ? 'var(--sand)' : 'var(--sage)';
  }
  function prStatusBg(status: string): string {
    return status === 'review' ? 'rgba(230,200,155,0.12)' : 'rgba(168,193,154,0.12)';
  }
  function relativeTime(isoStr: string): string {
    const ms = Date.now() - new Date(isoStr).getTime();
    const h = Math.floor(ms / 3_600_000);
    const d = Math.floor(h / 24);
    if (d > 0) return `${d}d`;
    if (h > 0) return `${h}h`;
    return '<1h';
  }
</script>

<ODScreen {mode}>
  <ODStatusBar app="GITHUB · commits · PRs · issues" accent="var(--sage)" />

  <main class="gh-grid">
    <div class="commits-col">
      <div>
        <SectionLabel>// HEARTBEAT · 7d</SectionLabel>
        <CommitHeartbeat color="var(--sage)" count={56} maxHeight={34} />
      </div>

      <div style="flex:1;display:flex;flex-direction:column;min-height:0;margin-top:12px">
        <SectionLabel>// RECENT COMMITS</SectionLabel>
        <div class="commit-list">
          {#each gh?.commits ?? [] as commit, i}
            <div class="commit-row" class:last={i === (gh?.commits.length ?? 0) - 1}>
              <span class="sha">{commit.sha}</span>
              <div style="min-width:0">
                <div class="commit-msg">{commit.msg}</div>
                <div class="commit-meta">
                  <span style="color:var(--sage)">+changes</span>
                  <span> · {commit.repo.split('/')[1]} · {relativeTime(commit.time)} ago</span>
                </div>
              </div>
            </div>
          {/each}
          {#if !gh?.commits.length}
            <div style="color:var(--ink-sub);font-size:11px">no commits</div>
          {/if}
        </div>
      </div>
    </div>

    <div class="right-col">
      <div>
        <SectionLabel>// OPEN PRs · {gh?.prs.length ?? 0}</SectionLabel>
        <div class="pr-list">
          {#each gh?.prs ?? [] as pr}
            <div class="pr-row">
              <span
                class="label-tag"
                style:color={prStatusColor(pr.status)}
                style:background={prStatusBg(pr.status)}>{pr.status}</span
              >
              <div>
                <div class="pr-title">{pr.title}</div>
                <div class="item-meta">#{pr.number} · {pr.repo.split('/')[1]} · {relativeTime(pr.age)}</div>
              </div>
            </div>
          {/each}
          {#if !gh?.prs.length}
            <div style="color:var(--ink-sub);font-size:11px">no open PRs</div>
          {/if}
        </div>
      </div>

      <div style="flex:1;display:flex;flex-direction:column;min-height:0;margin-top:14px">
        <SectionLabel>// ASSIGNED ISSUES · {gh?.issues.length ?? 0}</SectionLabel>
        <div class="issue-list">
          {#each gh?.issues ?? [] as issue}
            <div class="pr-row">
              <span
                class="label-tag"
                style:color={labelColor(issue.label)}
                style:background={labelBg(issue.label)}>{issue.label}</span
              >
              <div>
                <div class="pr-title">{issue.title}</div>
                <div class="item-meta">#{issue.number} · {issue.repo.split('/')[1]} · {relativeTime(issue.age)}</div>
              </div>
            </div>
          {/each}
          {#if !gh?.issues.length}
            <div style="color:var(--ink-sub);font-size:11px">no assigned issues</div>
          {/if}
        </div>
      </div>
    </div>
  </main>

  <ODDock active="GH" />
</ODScreen>

<style>
  .gh-grid {
    flex: 1;
    display: grid;
    grid-template-columns: 1.4fr 1fr;
    gap: 24px;
    min-height: 0;
  }
  .commits-col {
    display: flex;
    flex-direction: column;
    min-height: 0;
  }
  .commit-list {
    display: flex;
    flex-direction: column;
    gap: 9px;
    flex: 1;
    min-height: 0;
  }
  .commit-row {
    display: grid;
    grid-template-columns: auto 1fr;
    gap: 12px;
    align-items: flex-start;
    padding-bottom: 9px;
    border-bottom: 1px dashed var(--line);
  }
  .commit-row.last {
    border-bottom: none;
  }
  .sha {
    font-family: var(--font-mono);
    font-size: 10px;
    color: var(--sand);
    letter-spacing: 0.5px;
    margin-top: 2px;
  }
  .commit-msg {
    font-family: var(--font-sans);
    font-size: 13px;
    color: var(--ink);
    line-height: 1.25;
  }
  .commit-meta {
    font-family: var(--font-mono);
    font-size: 9px;
    color: var(--ink-dim);
    letter-spacing: 0.8px;
    margin-top: 2px;
  }
  .right-col {
    display: flex;
    flex-direction: column;
    min-height: 0;
  }
  .pr-list,
  .issue-list {
    display: flex;
    flex-direction: column;
    gap: 9px;
  }
  .pr-row {
    display: flex;
    align-items: flex-start;
    gap: 10px;
  }
  .label-tag {
    font-family: var(--font-mono);
    font-size: 9px;
    letter-spacing: 0.6px;
    padding: 3px 7px;
    border-radius: 5px;
    margin-top: 1px;
    white-space: nowrap;
  }
  .pr-title {
    font-family: var(--font-sans);
    font-size: 12.5px;
    color: var(--ink);
    line-height: 1.3;
  }
  .item-meta {
    font-size: 9px;
    color: var(--ink-sub);
    letter-spacing: 0.7px;
    margin-top: 2px;
  }
</style>
