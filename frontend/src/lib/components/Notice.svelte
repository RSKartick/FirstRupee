<script lang="ts">
	import type { Snippet } from 'svelte';
	import { Info, AlertTriangle, CheckCircle2, OctagonAlert } from 'lucide-svelte';

	let {
		tone = 'info',
		title = '',
		children
	}: { tone?: 'info' | 'warn' | 'danger' | 'success'; title?: string; children: Snippet } = $props();

	const palette = {
		info: 'border-azure/40 bg-azure/10 text-azure',
		warn: 'border-amber/40 bg-amber/10 text-amber',
		danger: 'border-danger/40 bg-danger/10 text-danger',
		success: 'border-brand/40 bg-brand/10 text-brand-soft'
	};
</script>

<div class="rounded-xl border px-4 py-3 text-[13px] leading-relaxed {palette[tone]}" role={tone === 'danger' ? 'alert' : 'status'}>
	<div class="flex items-start gap-2.5">
		{#if tone === 'danger'}<OctagonAlert size={16} class="mt-0.5 shrink-0" />
		{:else if tone === 'warn'}<AlertTriangle size={16} class="mt-0.5 shrink-0" />
		{:else if tone === 'success'}<CheckCircle2 size={16} class="mt-0.5 shrink-0" />
		{:else}<Info size={16} class="mt-0.5 shrink-0" />{/if}
		<div class="min-w-0">
			{#if title}<p class="mb-1 font-semibold">{title}</p>{/if}
			<div class="text-ink/90">{@render children()}</div>
		</div>
	</div>
</div>
