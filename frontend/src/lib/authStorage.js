const TOKEN_KEY = 'fieldos_token';
const USER_KEY = 'fieldos_user';

// Default to sessionStorage for reduced persistence/XSS blast radius.
// Set VITE_AUTH_PERSIST=local to opt-in to localStorage persistence.
const persistMode = (import.meta.env.VITE_AUTH_PERSIST || 'session').toLowerCase();

const storage = persistMode === 'local' ? localStorage : sessionStorage;

export const authStorage = {
  getToken: () => storage.getItem(TOKEN_KEY),
  setToken: (token) => storage.setItem(TOKEN_KEY, token),
  clearToken: () => {
    localStorage.removeItem(TOKEN_KEY);
    sessionStorage.removeItem(TOKEN_KEY);
  },

  getUser: () => storage.getItem(USER_KEY),
  setUser: (user) => storage.setItem(USER_KEY, user),
  clearUser: () => {
    localStorage.removeItem(USER_KEY);
    sessionStorage.removeItem(USER_KEY);
  },

  clearAll: () => {
    authStorage.clearToken();
    authStorage.clearUser();
  },
};
