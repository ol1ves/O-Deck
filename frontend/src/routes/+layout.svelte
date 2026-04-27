<script lang="ts">
  import { onMount, type Snippet } from 'svelte';
  import { fetchInitialState, fetchStatus } from '$lib/api';
  import { connectWebSocket } from '$lib/ws';
  import '../app.css';

  let { children }: { children?: Snippet } = $props();

  onMount(() => {
    void (async () => {
      try {
        await fetchInitialState();
      } catch (error) {
        console.warn('initial state unavailable', error);
      }
    })();
    void fetchStatus();
    connectWebSocket();
    const id = setInterval(() => void fetchStatus(), 30_000);
    return () => clearInterval(id);
  });
</script>

{@render children?.()}
