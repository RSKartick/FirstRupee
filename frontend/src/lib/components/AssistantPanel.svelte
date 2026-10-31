<script lang="ts">
	import { api, ApiError } from '$lib/api/client';
	import { session } from '$lib/stores/session.svelte';
	import type { ChatResponse } from '$lib/api/types';
	import { X, Send } from 'lucide-svelte';

	let { onclose }: { onclose: () => void } = $props();

	type Entry = { role: 'user' | 'assistant'; content: string; meta?: ChatResponse };
	let entries = $state<Entry[]>([]);
	let draft = $state('');
	let busy = $state(false);
	let error = $state('');

	const suggestions = [
		'Show my recommended portfolio and monthly rupee split',
		'Am I ready to invest right now?',
		'What is an expense ratio?',
		'What does maximum drawdown mean?'
	];

	async function send(text: string) {
		const question = text.trim();
		if (!question || busy) return;
		entries = [...entries, { role: 'user', content: question }];
		draft = '';
		busy = true;
		error = '';
		try {
			const history = entries.slice(-8).map((e) => ({ role: e.role, content: e.content }));
			const reply = await api.assistant({ profile_id: session.activeProfileId, messages: history });
			entries = [...entries, { role: 'assistant', content: reply.answer, meta: reply }];
		} catch (err) {
			error = err instanceof ApiError ? err.message : 'The assistant could not answer right now.';
		} finally {
			busy = false;
		}
	}
</script>

<div class="fixed inset-0 z-50 flex justify-end bg-black/60 no-print" role="dialog" aria-modal="true" aria-label="FirstRupee assistant">
	<div class="flex h-full w-full max-w-xl flex-col border-l border-line bg-canvas">
		<div class="flex items-start justify-between gap-3 border-b border-line px-5 py-4">
			<div>
				<p class="text-sm font-semibold">FirstRupee assistant</p>
				<p class="muted mt-0.5">Explains terms and your own stored results. It cannot recommend investments or change your readiness result.</p>
			</div>
			<button class="btn btn-ghost" onclick={onclose} aria-label="Close assistant"><X size={16} /></button>
		</div>

		<div class="flex-1 space-y-4 overflow-y-auto px-5 py-5">
			{#if entries.length === 0}
				<div class="flex flex-wrap gap-2">
					{#each suggestions as suggestion (suggestion)}
						<button class="btn text-[12px]" onclick={() => send(suggestion)}>{suggestion}</button>
					{/each}
				</div>
			{/if}
			{#each entries as entry, i (i)}
				<div class="flex {entry.role === 'user' ? 'justify-end' : 'justify-start'}">
					<div class="max-w-[85%] whitespace-pre-wrap rounded-xl px-4 py-3 text-[13px] leading-relaxed {entry.role === 'user' ? 'bg-brand/15' : 'border border-line bg-raised/60'}">
						{entry.content}
						{#if entry.meta}
							<p class="mt-2 text-[11px] text-muted">{entry.meta.mode === 'LLM' ? `Language model (${entry.meta.provider})` : 'Deterministic answer - no language model used'}</p>
						{/if}
					</div>
				</div>
			{/each}
			{#if busy}<p class="muted">Thinking…</p>{/if}
			{#if error}<p class="field-error" role="alert">{error}</p>{/if}
		</div>

		<form
			class="flex items-center gap-2 border-t border-line px-5 py-4"
			onsubmit={(event) => {
				event.preventDefault();
				void send(draft);
			}}
		>
			<label class="sr-only" for="assistant-input">Ask the assistant</label>
			<input id="assistant-input" class="field-input" bind:value={draft} placeholder="Ask about a term or your stored results…" maxlength="2000" />
			<button class="btn btn-primary" type="submit" disabled={busy || draft.trim() === ''}><Send size={16} />Send</button>
		</form>
	</div>
</div>
