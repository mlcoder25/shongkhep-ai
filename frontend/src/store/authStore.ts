import { create } from "zustand";
import Cookies from "js-cookie";
import { authApi } from "@/lib/api";

export interface UserProfile {
  id: string;
  email: string;
  plan: "free" | "basic" | "pro";
  usage_count: number;
  monthly_limit: number;
  remaining_requests: number;
  usage_percentage: number;
  api_key: string;
  created_at: string;
}

interface AuthState {
  user: UserProfile | null;
  token: string | null;
  loading: boolean;
  hydrated: boolean;

  login: (email: string, password: string) => Promise<void>;
  signup: (email: string, password: string) => Promise<void>;
  logout: () => void;
  fetchMe: () => Promise<void>;
  setUser: (user: UserProfile) => void;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  token: null,
  loading: false,
  hydrated: false,

  login: async (email, password) => {
    set({ loading: true });
    try {
      const data = await authApi.login({ email, password });
      Cookies.set("access_token", data.access_token, {
        expires: 7,
        sameSite: "Lax",
      });
      set({ token: data.access_token });
      await get().fetchMe();
    } finally {
      set({ loading: false });
    }
  },

  signup: async (email, password) => {
    set({ loading: true });
    try {
      await authApi.signup({ email, password });
      await get().login(email, password);
    } finally {
      set({ loading: false });
    }
  },

  logout: () => {
    Cookies.remove("access_token");
    set({ user: null, token: null });
  },

  fetchMe: async () => {
    try {
      const user = await authApi.me();
      set({ user, hydrated: true });
    } catch {
      Cookies.remove("access_token");
      set({ user: null, token: null, hydrated: true });
    }
  },

  setUser: (user) => set({ user }),
}));
