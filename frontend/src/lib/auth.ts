// Simple password authentication
const PASSWORD_KEY = 'finviz_auth';
const PASSWORD = import.meta.env.VITE_APP_PASSWORD || 'daiweihao1990'; // Default password, change in .env

export function isAuthenticated(): boolean {
	if (typeof window === 'undefined') return false;
	return sessionStorage.getItem(PASSWORD_KEY) === 'true';
}

export function login(password: string): boolean {
	if (password === PASSWORD) {
		sessionStorage.setItem(PASSWORD_KEY, 'true');
		return true;
	}
	return false;
}

export function logout(): void {
	if (typeof window !== 'undefined') {
		sessionStorage.removeItem(PASSWORD_KEY);
	}
}

