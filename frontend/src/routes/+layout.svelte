<script lang="ts">
  import { onMount, type Snippet } from 'svelte';
  import { fetchInitialState, fetchStatus } from '$lib/api';
  import { connectWebSocket } from '$lib/ws';
  import '../app.css';

  let { children }: { children?: Snippet } = $props();

  onMount(() => {
    void fetchInitialState();
    void fetchStatus();
    connectWebSocket();
    const id = setInterval(() => void fetchStatus(), 30_000);
    return () => clearInterval(id);
  });
</script>

{@render children?.()}
