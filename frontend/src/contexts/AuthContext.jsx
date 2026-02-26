import { createContext, useContext, useState, useEffect } from 'react';
import { authAPI } from '../lib/api';
import { authStorage } from '../lib/authStorage';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Check for existing session
    const storedUser = authStorage.getUser();
    const token = authStorage.getToken();
    
    if (storedUser && token) {
      setUser(JSON.parse(storedUser));
      // Verify token is still valid
      authAPI.me()
        .then(res => setUser(res.data))
        .catch(() => {
          authStorage.clearAll();
          setUser(null);
        })
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, []);

  const login = async (email, password) => {
    const response = await authAPI.login(email, password);
    const { access_token, user: userData } = response.data;
    
    authStorage.setToken(access_token);
    authStorage.setUser(JSON.stringify(userData));
    setUser(userData);
    
    return userData;
  };

  const logout = () => {
    authStorage.clearAll();
    setUser(null);
  };

  const refreshUser = async () => {
    try {
      const res = await authAPI.me();
      setUser(res.data);
      authStorage.setUser(JSON.stringify(res.data));
      return res.data;
    } catch {
      return null;
    }
  };

  const isSuperAdmin = user?.role === 'SUPERADMIN';

  return (
    <AuthContext.Provider value={{ user, login, logout, refreshUser, loading, isSuperAdmin }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};
