<script lang="ts">
  import { onMount, type Snippet } from 'svelte';
  import { fetchInitialState } from '$lib/api';
  import { connectWebSocket } from '$lib/ws';
  import '../app.css';

  let { children }: { children?: Snippet } = $props();

  onMount(async () => {
    try {
      await fetchInitialState();
    } catch (error) {
      console.warn('initial state unavailable', error);
    }

    connectWebSocket();
  });
</script>

{@render children?.()}
