import type { HandleClientError } from '@sveltejs/kit';

export const handleError: HandleClientError = ({ error, event }) => {
	const msg = error instanceof Error ? error.message : String(error ?? '');
	if (
		typeof window !== 'undefined' &&
		(msg.includes('Failed to fetch dynamically imported module') ||
			msg.includes('Importing a module script failed') ||
			msg.includes('error loading dynamically imported module'))
	) {
		const target = event?.url?.pathname
			? `${event.url.pathname}${event.url.search}${event.url.hash}`
			: window.location.href;
		window.location.assign(target);
		return { message: 'Reloading updated application bundle...' };
	}
	return {
		message: 'An unexpected error occurred. Refresh the page and try again.'
	};
};
