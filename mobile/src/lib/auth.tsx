import * as SecureStore from 'expo-secure-store';
import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react';

import { api, setAuthToken } from './api';
import type { User } from './types';

const TOKEN_KEY = 'spartango.token';

interface AuthState {
  user: User | null;
  loading: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signUp: (b: { email: string; password: string; name: string; student_id: string; accepted_terms_version: string }) => Promise<void>;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const adopt = useCallback(async (token: string) => {
    // Token lives in the phone's Keychain/Keystore, never in plain AsyncStorage.
    await SecureStore.setItemAsync(TOKEN_KEY, token);
    setAuthToken(token);
    setUser(await api.me());
  }, []);

  useEffect(() => {
    (async () => {
      try {
        const saved = await SecureStore.getItemAsync(TOKEN_KEY);
        if (saved) {
          setAuthToken(saved);
          setUser(await api.me());
        }
      } catch {
        await SecureStore.deleteItemAsync(TOKEN_KEY);
        setAuthToken(null);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const value: AuthState = {
    user,
    loading,
    signIn: async (email, password) => adopt((await api.login({ email, password })).access_token),
    signUp: async (b) => adopt((await api.signup(b)).access_token),
    signOut: async () => {
      await SecureStore.deleteItemAsync(TOKEN_KEY);
      setAuthToken(null);
      setUser(null);
    },
  };
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider');
  return ctx;
}
