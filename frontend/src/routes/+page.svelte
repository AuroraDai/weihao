<script lang="ts">
	import { onMount } from 'svelte';
	import { isAuthenticated, logout } from '$lib/auth';
	import { goto } from '$app/navigation';

	type NewsItem = { date?: string; title?: string; link?: string; source?: string };
	type ScreenerRow = Record<string, string>;

	const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://localhost:8000';

	// Check authentication
	let authenticated = $state(false);

	onMount(() => {
		authenticated = isAuthenticated();
		if (!authenticated) {
			goto('/login');
		}
	});

	const handleLogout = () => {
		logout();
		goto('/login');
	};

	let ticker = $state('AAPL');
	let loading = $state(false);
	let error = $state('');
	let quote = $state<Record<string, string> | null>(null);
	let news = $state<NewsItem[]>([]);
	let expandedNews = $state<Record<string, boolean>>({});
	let newsSummaries = $state<Record<string, { en: string; zh: string }>>({});
	let newsSummaryLang = $state<Record<string, 'en' | 'zh'>>({});
	let newsSummaryLoading = $state<Record<string, boolean>>({});
	let newsSummaryError = $state<Record<string, string>>({});
	let chartUrl = $state('');
	let screener = $state<ScreenerRow[]>([]);
	let screenerError = $state('');
	let screenerLoading = $state(false);
	let screenerLimit = $state(25);

	const screenerColumns = $derived(screener.length ? Object.keys(screener[0]) : []);

	const fetchQuote = async () => {
		const symbol = ticker.trim().toUpperCase();

		if (!symbol) {
			error = 'Please enter a ticker symbol.';
			return;
		}

		loading = true;
		error = '';
		quote = null;
		news = [];

		try {
			const response = await fetch(`${API_BASE}/quote/${symbol}`);
			const payload = await response.json();

			if (!response.ok) {
				throw new Error(payload.detail ?? response.statusText);
			}

			quote = payload.quote ?? null;
			news = payload.news ?? [];
			chartUrl = payload.chart_url ?? '';
		} catch (err) {
			error = err instanceof Error ? err.message : 'Unexpected error';
		} finally {
			loading = false;
		}
	};

	const fetchScreener = async () => {
		screenerLoading = true;
		screenerError = '';
		screener = [];

		try {
			const params = new URLSearchParams({
				limit: String(screenerLimit)
			});
			const response = await fetch(`${API_BASE}/screener?${params.toString()}`);
			const payload = await response.json();

			if (!response.ok) {
				throw new Error(payload.detail ?? response.statusText);
			}

			screener = payload.rows ?? [];
		} catch (err) {
			screenerError = err instanceof Error ? err.message : 'Unexpected error';
		} finally {
			screenerLoading = false;
		}
	};

	onMount(() => {
		fetchQuote();
		fetchScreener();
	});

	const newsKey = (item: NewsItem, index: number) => item.link ?? `news-${index}`;

	const loadNewsSummary = async (item: NewsItem, index: number) => {
		const key = newsKey(item, index);
		if (newsSummaries[key] || newsSummaryLoading[key]) return;

		if (!item.link) {
			newsSummaryError = {
				...newsSummaryError,
				[key]: 'No URL available for this article'
			};
			return;
		}

		newsSummaryLoading = { ...newsSummaryLoading, [key]: true };
		newsSummaryError = { ...newsSummaryError, [key]: '' };

		try {
			const response = await fetch(`${API_BASE}/news/summary?url=${encodeURIComponent(item.link)}`);
			const payload = await response.json();

			if (!response.ok) {
				throw new Error(payload.detail ?? response.statusText);
			}

			newsSummaries = {
				...newsSummaries,
				[key]: {
					en: payload.summary_en || 'No summary available.',
					zh: payload.summary_zh || payload.summary_en || 'No summary available.'
				}
			};
			// Default to English
			if (!newsSummaryLang[key]) {
				newsSummaryLang = { ...newsSummaryLang, [key]: 'en' };
			}
		} catch (err) {
			newsSummaryError = {
				...newsSummaryError,
				[key]: err instanceof Error ? err.message : 'Failed to load summary'
			};
		} finally {
			newsSummaryLoading = { ...newsSummaryLoading, [key]: false };
		}
	};

	const toggleNews = (item: NewsItem, index: number) => {
		const key = newsKey(item, index);
		const next = !expandedNews[key];
		expandedNews = { ...expandedNews, [key]: next };
		if (next) {
			loadNewsSummary(item, index);
		}
	};
</script>

{#if !authenticated}
	<div class="loading">验证中...</div>
{:else}
<main class="page">
	<section class="card">
		<div class="card-header">
			<div>
				<h1>Finviz data viewer</h1>
				<p class="muted">Python backend scrapes Finviz; Svelte renders it.</p>
			</div>
			<button class="logout-btn" onclick={handleLogout} type="button">
				退出登录
			</button>
		</div>

		<form
			class="form"
			onsubmit={(event) => {
				event.preventDefault();
				fetchQuote();
			}}
		>
			<label class="input-label" for="ticker">Ticker</label>
			<div class="input-row">
				<input
					id="ticker"
					name="ticker"
					placeholder="e.g. AAPL"
					bind:value={ticker}
					autocomplete="off"
				/>
				<button type="submit" aria-busy={loading}>
					{#if loading}
						Loading...
					{:else}
						Get quote
					{/if}
				</button>
			</div>
		</form>

		{#if error}
			<p class="error">{error}</p>
		{/if}

		{#if loading}
			<p class="muted">Fetching data from backend...</p>
		{/if}

		{#if quote}
			<div class="quote-grid">
				{#each Object.entries(quote) as [key, value] (key)}
					<div class="quote-item">
						<span class="label">{key}</span>
						<span class="value">{value}</span>
					</div>
				{/each}
			</div>
			{#if chartUrl}
				<div class="chart-wrapper">
					<img
						src={chartUrl}
						alt={`Daily chart for ${quote.Company ?? ticker}`}
						loading="lazy"
						referrerpolicy="no-referrer"
					/>
					<p class="muted small">Daily chart from Finviz.</p>
				</div>
			{/if}
		{:else if !loading}
			<p class="muted">Enter a ticker and press "Get quote".</p>
		{/if}
	</section>

	{#if news.length}
		<section class="card">
			<h2>Latest news</h2>
			<ul class="news-list">
				{#each news as item, index (item.link ?? index)}
					<li>
						<div class="news-row">
							<div class="news-meta">
								<a href={item.link} target="_blank" rel="noreferrer">
									{item.title ?? item.link}
								</a>
								<div class="muted">
									{item.source ?? ''}{item.source && item.date ? ' • ' : ''}{item.date ?? ''}
								</div>
							</div>
							<button
								class="ghost-btn"
								type="button"
								aria-expanded={expandedNews[item.link ?? `news-${index}`] ?? false}
								onclick={() => toggleNews(item, index)}
							>
								{expandedNews[item.link ?? `news-${index}`] ? 'Hide summary' : 'Show summary'}
							</button>
						</div>

						{#if expandedNews[item.link ?? `news-${index}`]}
							<div class="summary-box">
								{#if newsSummaryLoading[item.link ?? `news-${index}`]}
									<p class="muted small">Loading summary...</p>
								{:else if newsSummaryError[item.link ?? `news-${index}`]}
									<p class="error small">{newsSummaryError[item.link ?? `news-${index}`]}</p>
								{:else if newsSummaries[item.link ?? `news-${index}`]}
									<div class="summary-content">
										<div class="lang-toggle">
											<button
												class="lang-btn"
												class:active={newsSummaryLang[item.link ?? `news-${index}`] === 'en'}
												type="button"
												onclick={() => {
													const key = item.link ?? `news-${index}`;
													newsSummaryLang = { ...newsSummaryLang, [key]: 'en' };
												}}
											>
												English
											</button>
											<button
												class="lang-btn"
												class:active={newsSummaryLang[item.link ?? `news-${index}`] === 'zh'}
												type="button"
												onclick={() => {
													const key = item.link ?? `news-${index}`;
													newsSummaryLang = { ...newsSummaryLang, [key]: 'zh' };
												}}
											>
												中文
											</button>
										</div>
										<p class="summary-text">
											{newsSummaryLang[item.link ?? `news-${index}`] === 'zh'
												? newsSummaries[item.link ?? `news-${index}`].zh
												: newsSummaries[item.link ?? `news-${index}`].en}
										</p>
									</div>
								{/if}
							</div>
						{/if}
					</li>
				{/each}
			</ul>
		</section>
	{/if}

	<section class="card">
		<div class="card-header">
			<div>
				<h2>Screener export</h2>
				<p class="muted">
					Data pulled from your Finviz export URL on the Python backend.
				</p>
			</div>
			<form
				class="controls"
				onsubmit={(event) => {
					event.preventDefault();
					fetchScreener();
				}}
			>
				<label class="input-label" for="limit">Rows</label>
				<input
					id="limit"
					name="limit"
					type="number"
					min="1"
					max="500"
					bind:value={screenerLimit}
				/>
				<button type="submit" aria-busy={screenerLoading}>
					{#if screenerLoading}
						Refreshing...
					{:else}
						Refresh
					{/if}
				</button>
			</form>
		</div>

		{#if screenerError}
			<p class="error">{screenerError}</p>
		{:else if screenerLoading}
			<p class="muted">Fetching screener export...</p>
		{:else if screener.length === 0}
			<p class="muted">No rows returned from export.</p>
		{:else}
			<div class="table-wrapper">
				<table>
					<thead>
						<tr>
							{#each screenerColumns as col}
								<th>{col}</th>
							{/each}
						</tr>
					</thead>
					<tbody>
						{#each screener as row, idx}
							<tr>
								{#each screenerColumns as col}
									<td>{row[col]}</td>
								{/each}
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
			<p class="muted">{screener.length} rows shown.</p>
		{/if}
	</section>
</main>
{/if}

<style>
	:global(body) {
		margin: 0;
		font-family: system-ui, -apple-system, 'Segoe UI', sans-serif;
		background: #0f172a;
		color: #e2e8f0;
	}

	.page {
		max-width: 960px;
		margin: 0 auto;
		padding: 2rem 1.5rem 3rem;
		display: flex;
		flex-direction: column;
		gap: 1.5rem;
	}

	.card {
		background: #111827;
		border: 1px solid #1f2937;
		border-radius: 12px;
		padding: 1.25rem;
		box-shadow: 0 10px 40px rgba(0, 0, 0, 0.35);
	}

	h1,
	h2 {
		margin: 0 0 0.35rem;
	}

	.muted {
		color: #94a3b8;
		margin: 0.35rem 0 0;
	}

	.form {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
		margin-top: 1rem;
		margin-bottom: 0.75rem;
	}

	.input-label {
		font-weight: 600;
		color: #cbd5e1;
	}

	.input-row {
		display: flex;
		gap: 0.5rem;
	}

	input {
		flex: 1;
		padding: 0.65rem 0.8rem;
		border-radius: 10px;
		border: 1px solid #1f2937;
		background: #0b1220;
		color: #e2e8f0;
	}

	button {
		padding: 0.65rem 1rem;
		border: none;
		border-radius: 10px;
		background: linear-gradient(135deg, #2563eb, #7c3aed);
		color: #f8fafc;
		font-weight: 700;
		cursor: pointer;
		transition: opacity 0.2s ease;
		min-width: 120px;
	}

	button[aria-busy='true'] {
		opacity: 0.7;
		cursor: wait;
	}

	.error {
		color: #f87171;
		font-weight: 600;
	}

	.quote-grid {
		margin-top: 1rem;
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
		gap: 0.75rem;
	}

	.quote-item {
		background: #0b1220;
		border: 1px solid #1f2937;
		border-radius: 10px;
		padding: 0.75rem;
		display: flex;
		flex-direction: column;
		gap: 0.2rem;
	}

	.label {
		color: #94a3b8;
		font-size: 0.9rem;
	}

	.value {
		font-size: 1.1rem;
		font-weight: 700;
		color: #f1f5f9;
		word-break: break-word;
	}

	.news-list {
		list-style: none;
		padding: 0;
		margin: 0.5rem 0 0;
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
	}

	.news-list a {
		color: #60a5fa;
		font-weight: 600;
		text-decoration: none;
	}

	.news-list a:hover {
		text-decoration: underline;
	}

	.news-list li {
		display: flex;
		flex-direction: column;
		gap: 0.2rem;
	}

	.news-row {
		display: flex;
		justify-content: space-between;
		gap: 0.75rem;
		align-items: flex-start;
		flex-wrap: wrap;
	}

	.news-meta a {
		color: #60a5fa;
		font-weight: 600;
		text-decoration: none;
	}

	.news-meta a:hover {
		text-decoration: underline;
	}

	.ghost-btn {
		background: transparent;
		border: 1px solid #334155;
		color: #e2e8f0;
		border-radius: 8px;
		padding: 0.35rem 0.6rem;
		cursor: pointer;
	}

	.summary-box {
		margin-top: 0.35rem;
		border: 1px solid #1f2937;
		background: #0b1220;
		border-radius: 8px;
		padding: 0.5rem 0.75rem;
	}

	.summary-content {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.lang-toggle {
		display: flex;
		gap: 0.5rem;
		margin-bottom: 0.25rem;
	}

	.lang-btn {
		background: transparent;
		border: 1px solid #334155;
		color: #94a3b8;
		border-radius: 6px;
		padding: 0.3rem 0.6rem;
		cursor: pointer;
		font-size: 0.85rem;
		transition: all 0.2s ease;
	}

	.lang-btn:hover {
		border-color: #475569;
		color: #e2e8f0;
	}

	.lang-btn.active {
		background: linear-gradient(135deg, #2563eb, #7c3aed);
		border-color: #2563eb;
		color: #f8fafc;
		font-weight: 600;
	}

	.summary-text {
		line-height: 1.6;
		white-space: pre-wrap;
		word-wrap: break-word;
	}

	.chart-wrapper {
		margin-top: 1rem;
		background: #0b1220;
		border: 1px solid #1f2937;
		border-radius: 10px;
		padding: 0.75rem;
	}

	.chart-wrapper img {
		width: 100%;
		height: auto;
		display: block;
		border-radius: 8px;
	}

	.small {
		font-size: 0.9rem;
	}

	.card-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		gap: 1rem;
		flex-wrap: wrap;
		margin-bottom: 1rem;
	}

	.logout-btn {
		background: transparent;
		border: 1px solid #334155;
		color: #94a3b8;
		border-radius: 8px;
		padding: 0.5rem 1rem;
		cursor: pointer;
		font-size: 0.9rem;
		transition: all 0.2s ease;
	}

	.logout-btn:hover {
		border-color: #f87171;
		color: #f87171;
		background: rgba(248, 113, 113, 0.1);
	}

	.loading {
		min-height: 100vh;
		display: flex;
		align-items: center;
		justify-content: center;
		color: #94a3b8;
		font-size: 1.1rem;
	}

	.controls {
		display: flex;
		gap: 0.5rem;
		align-items: flex-end;
	}

	.controls input {
		max-width: 120px;
	}

	.table-wrapper {
		overflow-x: auto;
		margin-top: 1rem;
	}

	table {
		width: 100%;
		border-collapse: collapse;
		font-size: 0.95rem;
	}

	th,
	td {
		text-align: left;
		padding: 0.5rem;
		border-bottom: 1px solid #1f2937;
		white-space: nowrap;
	}

	th {
		color: #cbd5e1;
		font-weight: 700;
		position: sticky;
		top: 0;
		background: #111827;
	}
</style>
