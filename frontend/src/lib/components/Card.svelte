<script lang="ts">
	import type { Snippet } from 'svelte';

	let {
		title = '',
		subtitle = '',
		right,
		children,
		class: extra = ''
	}: { title?: string; subtitle?: string; right?: Snippet; children: Snippet; class?: string } = $props();
</script>

<section class="card {extra}">
	{#if title || right}
		<header class="card-head">
			<div>
				{#if title}<h2>{title}</h2>{/if}
				{#if subtitle}<p class="muted mt-1">{subtitle}</p>{/if}
			</div>
			{#if right}<div class="shrink-0">{@render right()}</div>{/if}
		</header>
	{/if}
	{@render children()}
</section>
