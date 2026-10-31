<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { api, ApiError } from '$lib/api/client';
	import { applySignIn, loadProfiles } from '$lib/stores/session.svelte';

	let name = $state('');
	let email = $state('');
	let password = $state('');
	let busy = $state(false);
	let error = $state('');
	const passwordOk = $derived(password.length >= 10);

	async function submit(event: SubmitEvent) {
		event.preventDefault();
		if (!passwordOk) {
			error = 'Use at least 10 characters for your password.';
			return;
		}
		busy = true;
		error = '';
		try {
			const res = await api.register({ email, password, display_name: name });
			applySignIn(res.user, res.csrf_token);
			await loadProfiles();
			const next = page.url.searchParams.get('next') ?? '/onboarding';
			await goto(next.startsWith('/') && !next.startsWith('//') ? next : '/onboarding');
		} catch (err) {
			error = err instanceof ApiError ? err.message : 'Registration failed. Please try again.';
		} finally {
			busy = false;
		}
	}
</script>

<svelte:head><title>Create account — FirstRupee</title></svelte:head>

<div class="mx-auto max-w-md space-y-6 pt-8">
	<div>
		<h1 class="text-2xl font-semibold tracking-tight">Create your account</h1>
		<p class="muted mt-2">Passwords are hashed with Argon2id. We never store bank passwords or brokerage credentials.</p>
	</div>
	<form class="card space-y-4" onsubmit={submit} novalidate>
		<div>
			<label class="field-label" for="name">Name or nickname</label>
			<input id="name" class="field-input" autocomplete="nickname" required minlength="2" bind:value={name} />
		</div>
		<div>
			<label class="field-label" for="email">Email</label>
			<input id="email" class="field-input" type="email" autocomplete="email" required bind:value={email} />
		</div>
		<div>
			<label class="field-label" for="password">Password (10+ characters)</label>
			<input id="password" class="field-input" type="password" autocomplete="new-password" required minlength="10" bind:value={password} />
		</div>
		{#if error}<p class="field-error" role="alert">{error}</p>{/if}
		<button class="btn btn-primary w-full" type="submit" disabled={busy || !name || !email || !password}>{busy ? 'Creating account…' : 'Create account'}</button>
	</form>
	<p class="muted text-center">Already registered? <a class="text-brand-soft underline" href="/login">Sign in</a></p>
</div>
