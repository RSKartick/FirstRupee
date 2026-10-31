<script lang="ts">
	import { api, ApiError } from '$lib/api/client';
	import { session } from '$lib/stores/session.svelte';
	import type { ChatResponse } from '$lib/api/types';
	import { X, Send, Trash2 } from 'lucide-svelte';

	let { onclose }: { onclose: () => void } = $props();

	type Entry = { role: 'user' | 'assistant'; content: string; meta?: Partial<ChatResponse> | null };
	let entries = $state<Entry[]>([]);
	let draft = $state('');
	let busy = $state(false);
	let loadingHistory = $state(false);
	let error = $state('');
	let scrollContainer: HTMLDivElement | undefined = $state();

	const suggestions = [
		'How do index funds compare to picking individual stocks?',
		'Explain LTCG and STCG tax rules on stocks and mutual funds in India',
		'What should I check before analysing a company on NSE?',
		'Am I ready to invest right now and how should I split my monthly SIP?'
	];

	$effect(() => {
		const userId = session.user?.id;
		void loadHistory(userId);
	});

	$effect(() => {
		if (entries.length > 0 && scrollContainer) {
			scrollContainer.scrollTop = scrollContainer.scrollHeight;
		}
	});

	async function loadHistory(userId: number | undefined) {
		error = '';
		if (!userId) {
			entries = [];
			return;
		}
		loadingHistory = true;
		try {
			const res = await api.assistantHistory();
			entries = res.messages.map((m) => ({
				role: m.role,
				content: m.content,
				meta: m.meta
			}));
		} catch {
			// Ignore if history cannot be loaded yet
		} finally {
			loadingHistory = false;
		}
	}

	async function clearHistory() {
		if (busy) return;
		error = '';
		const previous = entries;
		entries = [];
		try {
			await api.clearAssistantHistory();
		} catch (err) {
			entries = previous;
			error = err instanceof ApiError ? err.message : 'Could not clear chat history.';
		}
	}

	async function send(text: string) {
		const question = text.trim();
		if (!question || busy) return;
		entries = [...entries, { role: 'user', content: question }];
		draft = '';
		busy = true;
		error = '';
		try {
			const reply = await api.assistant({
				profile_id: session.activeProfileId,
				messages: [{ role: 'user', content: question }]
			});
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
				<p class="text-sm font-semibold">FirstRupee AI Chatbot</p>
				<p class="muted mt-0.5">Ask about finance, stocks, mutual funds, taxes, market concepts, basic questions, or your personal portfolio.</p>
			</div>
			<div class="flex shrink-0 items-center gap-1.5">
				{#if entries.length > 0}
					<button class="btn btn-ghost !px-2.5 !py-1.5 text-[12px]" onclick={clearHistory} title="Clear conversation history" aria-label="Clear conversation history">
						<Trash2 size={14} />Clear
					</button>
				{/if}
				<button class="btn btn-ghost" onclick={onclose} aria-label="Close assistant"><X size={16} /></button>
			</div>
		</div>

		<div bind:this={scrollContainer} class="flex-1 space-y-4 overflow-y-auto px-5 py-5">
			{#if loadingHistory && entries.length === 0}
				<p class="muted text-[12px]">Restoring your conversation history...</p>
			{:else if entries.length === 0}
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
						{#if entry.meta && entry.meta.mode}
							<p class="mt-2 text-[11px] text-muted">{entry.meta.mode === 'LLM' ? `Language model (${entry.meta.provider})` : entry.meta.provider === 'domain-guardrail' ? 'Financial domain guardrail' : 'Deterministic engine'}</p>
						{/if}
					</div>
				</div>
			{/each}
			{#if busy}<p class="muted">Thinking...</p>{/if}
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
			<input id="assistant-input" class="field-input" bind:value={draft} placeholder="Ask anything about finance, markets, or a general question..." maxlength="2000" />
			<button class="btn btn-primary" type="submit" disabled={busy || draft.trim() === ''}><Send size={16} />Send</button>
		</form>
	</div>
</div>
