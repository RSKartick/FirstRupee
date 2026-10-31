import adapterNode from '@sveltejs/adapter-node';

const adapter = process.env.VERCEL
	? (await import('@sveltejs/adapter-vercel')).default
	: adapterNode;

/** @type {import('@sveltejs/kit').Config} */
const config = {
	kit: {
		adapter: process.env.VERCEL
			? adapter({ runtime: 'nodejs24.x' })
			: adapter({ out: 'build' })
	}
};

export default config;
