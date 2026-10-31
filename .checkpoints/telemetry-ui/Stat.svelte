<script lang="ts">
	import type { Tone } from '$lib/format';

	let {
		label,
		value,
		hint = '',
		tone = 'neutral'
	}: { label: string; value: string; hint?: string; tone?: Tone } = $props();

	const valueClass: Record<Tone, string> = {
		success: 'text-brand-soft',
		warn: 'text-amber',
		danger: 'text-danger',
		info: 'text-azure',
		neutral: 'text-ink'
	};
</script>

<div class="rounded-xl border border-line bg-raised/50 p-4 transition-colors hover:border-line-soft">
	<p class="text-[11px] font-bold uppercase tracking-wider text-muted">{label}</p>
	<p class="mt-1.5 text-xl font-bold font-mono tabular-nums {valueClass[tone]}">{value}</p>
	{#if hint}<p class="mt-1 text-xs leading-relaxed text-muted">{hint}</p>{/if}
</div>
