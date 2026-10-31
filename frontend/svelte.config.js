import adapterNode from '@sveltejs/adapter-node';
import adapterVercel from '@sveltejs/adapter-vercel';

const adapter = process.env.VERCEL ? adapterVercel : adapterNode;

/** @type {import('@sveltejs/kit').Config} */
const config = {
	kit: {
		adapter: process.env.VERCEL
			? adapter({ runtime: 'nodejs24.x' })
			: adapter({ out: 'build' })
	}
};

export default config;
