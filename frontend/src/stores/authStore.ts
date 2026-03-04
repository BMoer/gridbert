import { create } from "zustand";
import type { UserProfile } from "../api/client";

interface AuthState {
  token: string | null;
  user: UserProfile | null;
  setAuth: (token: string, user: { user_id: number; name: string; email?: string }) => void;
  setUser: (user: UserProfile) => void;
  logout: () => void;
  isAuthenticated: () => boolean;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  token: localStorage.getItem("gridbert_token"),
  user: null,

  setAuth: (token, user) => {
    localStorage.setItem("gridbert_token", token);
    set({
      token,
      user: {
        id: user.user_id,
        email: user.email ?? "",
        name: user.name,
        plz: "",
      },
    });
  },

  setUser: (user) => set({ user }),

  logout: () => {
    localStorage.removeItem("gridbert_token");
    set({ token: null, user: null });
  },

  isAuthenticated: () => get().token !== null,
}));
