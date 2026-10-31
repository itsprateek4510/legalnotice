import { createContext, useContext, useState } from "react";
import { AUTH_TOKEN_KEY, AUTH_USER_KEY } from "../utils/constants";
import { loginUser, registerUser } from "../api/api";

const AuthContext = createContext(null);

function loadUser() {
  try {
    const raw = localStorage.getItem(AUTH_USER_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

function persistAuth(token, user) {
  localStorage.setItem(AUTH_TOKEN_KEY, token);
  localStorage.setItem(AUTH_USER_KEY, JSON.stringify(user));
}

function clearAuth() {
  localStorage.removeItem(AUTH_TOKEN_KEY);
  localStorage.removeItem(AUTH_USER_KEY);
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(loadUser);
  const [token, setToken] = useState(() => localStorage.getItem(AUTH_TOKEN_KEY));

  const login = async (email, password) => {
    const data = await loginUser({ email, password });
    persistAuth(data.access_token, data.user);
    setUser(data.user);
    setToken(data.access_token);
    return data.user;
  };

  const register = async (full_name, email, password) => {
    const data = await registerUser({ full_name, email, password });
    persistAuth(data.access_token, data.user);
    setUser(data.user);
    setToken(data.access_token);
    return data.user;
  };

  const logout = () => {
    clearAuth();
    setUser(null);
    setToken(null);
  };

  const value = { user, token, login, register, logout, isAuthenticated: !!user };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
  return ctx;
}