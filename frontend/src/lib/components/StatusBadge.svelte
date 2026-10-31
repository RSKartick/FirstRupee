<script lang="ts">
	import { labelize, readinessTone, type Tone } from '$lib/format';

	let { status, text = '' }: { status: string; text?: string } = $props();

	const classes: Record<Tone, string> = {
		success: 'border-brand/40 bg-brand/10 text-brand-soft',
		warn: 'border-amber/40 bg-amber/10 text-amber',
		danger: 'border-danger/40 bg-danger/10 text-danger',
		info: 'border-azure/40 bg-azure/10 text-azure',
		neutral: 'border-line bg-raised text-muted'
	};
	const tone = $derived(readinessTone(status));
</script>

<span class="inline-flex items-center rounded-full border px-2.5 py-0.5 text-[11px] font-medium tracking-wide uppercase {classes[tone]}">
	{text || labelize(status)}
</span>
