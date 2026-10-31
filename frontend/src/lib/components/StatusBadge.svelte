<script lang="ts">
	import { labelize, readinessTone, type Tone } from '$lib/format';

	let { status, text = '' }: { status: string; text?: string } = $props();

	const classes: Record<Tone, string> = {
		success: 'border-line bg-raised text-brand-soft',
		warn: 'border-line bg-raised text-amber',
		danger: 'border-line bg-raised text-danger',
		info: 'border-line bg-raised text-ink',
		neutral: 'border-line bg-canvas text-muted'
	};
	const tone = $derived(readinessTone(status));
</script>

<span class="inline-flex shrink-0 items-center whitespace-nowrap rounded border px-2 py-0.5 text-[11px] font-mono font-medium {classes[tone]}">
	{text || labelize(status)}
</span>
