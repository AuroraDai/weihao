<script lang="ts">
	import { onMount } from 'svelte';
	import { login, isAuthenticated } from '$lib/auth';
	import { goto } from '$app/navigation';

	let password = $state('');
	let error = $state('');
	let loading = $state(false);

	// If already authenticated, redirect to home
	onMount(() => {
		if (isAuthenticated()) {
			goto('/');
		}
	});

	const handleLogin = async () => {
		if (!password.trim()) {
			error = '请输入密码';
			return;
		}

		loading = true;
		error = '';

		// Small delay to prevent brute force
		await new Promise((resolve) => setTimeout(resolve, 300));

		if (login(password)) {
			password = '';
			goto('/');
		} else {
			error = '密码错误，请重试';
			password = '';
		}

		loading = false;
	};

	const handleKeyPress = (e: KeyboardEvent) => {
		if (e.key === 'Enter') {
			handleLogin();
		}
	};
</script>

<div class="login-container">
	<div class="login-box">
		<h1>🔒 访问受限</h1>
		<p class="subtitle">请输入密码以访问 Finviz 交易仪表板</p>

		<form
			onsubmit={(e) => {
				e.preventDefault();
				handleLogin();
			}}
			class="login-form"
		>
			<div class="input-group">
				<label for="password">密码</label>
				<input
					id="password"
					type="password"
					placeholder="输入密码"
					bind:value={password}
					onkeypress={handleKeyPress}
					autocomplete="off"
					autofocus
					disabled={loading}
				/>
			</div>

			{#if error}
				<p class="error">{error}</p>
			{/if}

			<button type="submit" disabled={loading} aria-busy={loading}>
				{loading ? '验证中...' : '登录'}
			</button>
		</form>
	</div>
</div>

<style>
	.login-container {
		min-height: 100vh;
		display: flex;
		align-items: center;
		justify-content: center;
		background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
		padding: 2rem;
	}

	.login-box {
		background: #111827;
		border: 1px solid #1f2937;
		border-radius: 16px;
		padding: 2.5rem;
		width: 100%;
		max-width: 400px;
		box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
	}

	h1 {
		margin: 0 0 0.5rem;
		font-size: 1.75rem;
		color: #f1f5f9;
		text-align: center;
	}

	.subtitle {
		color: #94a3b8;
		text-align: center;
		margin: 0 0 2rem;
		font-size: 0.95rem;
	}

	.login-form {
		display: flex;
		flex-direction: column;
		gap: 1.25rem;
	}

	.input-group {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	label {
		color: #cbd5e1;
		font-weight: 600;
		font-size: 0.9rem;
	}

	input {
		padding: 0.75rem 1rem;
		border-radius: 10px;
		border: 1px solid #1f2937;
		background: #0b1220;
		color: #e2e8f0;
		font-size: 1rem;
		transition: border-color 0.2s;
	}

	input:focus {
		outline: none;
		border-color: #2563eb;
	}

	input:disabled {
		opacity: 0.6;
		cursor: not-allowed;
	}

	.error {
		color: #f87171;
		font-size: 0.9rem;
		margin: 0;
		text-align: center;
	}

	button {
		padding: 0.75rem 1.5rem;
		border: none;
		border-radius: 10px;
		background: linear-gradient(135deg, #2563eb, #7c3aed);
		color: #f8fafc;
		font-weight: 700;
		font-size: 1rem;
		cursor: pointer;
		transition: opacity 0.2s;
		margin-top: 0.5rem;
	}

	button:hover:not(:disabled) {
		opacity: 0.9;
	}

	button:disabled {
		opacity: 0.6;
		cursor: wait;
	}
</style>

