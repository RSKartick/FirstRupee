<script lang="ts">
	export interface ChartSeries {
		label: string;
		color: string;
		points: { x: string; y: number }[];
		dashed?: boolean;
	}

	let {
		series,
		height = 260,
		formatY = (v: number) => v.toFixed(0),
		label = 'Line chart'
	}: { series: ChartSeries[]; height?: number; formatY?: (v: number) => string; label?: string } = $props();

	const WIDTH = 800;
	const PAD = { left: 78, right: 16, top: 14, bottom: 28 };

	const values = $derived(series.flatMap((s) => s.points.map((p) => p.y)).filter((v) => Number.isFinite(v)));
	const span = $derived.by(() => {
		if (values.length === 0) return { min: 0, max: 1 };
		const min = Math.min(...values);
		const max = Math.max(...values);
		const pad = (max - min) * 0.06 || Math.abs(max) * 0.05 || 1;
		return { min: min - pad, max: max + pad };
	});
	const count = $derived(Math.max(1, ...series.map((s) => s.points.length)));

	function x(i: number): number {
		return PAD.left + (i / Math.max(1, count - 1)) * (WIDTH - PAD.left - PAD.right);
	}
	function y(v: number): number {
		return PAD.top + (1 - (v - span.min) / (span.max - span.min || 1)) * (height - PAD.top - PAD.bottom);
	}
	const ticks = $derived(Array.from({ length: 5 }, (_, i) => span.min + ((span.max - span.min) * i) / 4));
	const paths = $derived(
		series.map((s) => ({
			...s,
			d: s.points.map((p, i) => `${i === 0 ? 'M' : 'L'}${x(i).toFixed(1)},${y(p.y).toFixed(1)}`).join(' ')
		}))
	);
	const firstLabel = $derived(series[0]?.points[0]?.x ?? '');
	const lastLabel = $derived(series[0]?.points[series[0].points.length - 1]?.x ?? '');
</script>

{#if values.length === 0}
	<div class="flex h-40 items-center justify-center rounded-xl border border-dashed border-line text-[13px] text-muted">
		No data to chart for this selection.
	</div>
{:else}
	<figure class="w-full">
		<svg viewBox="0 0 {WIDTH} {height}" class="w-full" role="img" aria-label={label}>
			{#each ticks as tick (tick)}
				<line x1={PAD.left} x2={WIDTH - PAD.right} y1={y(tick)} y2={y(tick)} stroke="#22324d" stroke-width="1" />
				<text x={PAD.left - 8} y={y(tick) + 4} text-anchor="end" fill="#8b9bb4" font-size="11">{formatY(tick)}</text>
			{/each}
			{#each paths as p (p.label)}
				<path d={p.d} fill="none" stroke={p.color} stroke-width="2" stroke-linejoin="round" stroke-dasharray={p.dashed ? '6 4' : undefined} />
			{/each}
			<text x={PAD.left} y={height - 8} fill="#8b9bb4" font-size="11">{firstLabel}</text>
			<text x={WIDTH - PAD.right} y={height - 8} text-anchor="end" fill="#8b9bb4" font-size="11">{lastLabel}</text>
		</svg>
		<figcaption class="mt-2 flex flex-wrap gap-x-5 gap-y-1">
			{#each series as s (s.label)}
				<span class="flex items-center gap-2 text-[11px] text-muted">
					<span class="inline-block h-0.5 w-3.5" style="background:{s.color}"></span>{s.label}
				</span>
			{/each}
		</figcaption>
	</figure>
{/if}
