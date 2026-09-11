import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";

interface User {
  id: string;
  email: string;
  full_name: string;
  role: string;
  health_score: number;
  avatar_url?: string;
}

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;

  // Tracks whether zustand's persist middleware has finished reading from
  // localStorage yet. Next.js renders on the server first (no localStorage),
  // so any redirect/gate logic must wait for `_hasHydrated` before trusting
  // `isAuthenticated` — otherwise a logged-in user briefly flashes as
  // logged-out (or vice versa) on every page load.
  _hasHydrated: boolean;

  setAuth: (user: User, token: string, refreshToken: string) => void;
  updateUser: (user: Partial<User>) => void;
  logout: () => void;
  setHasHydrated: (state: boolean) => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      token: null,
      isAuthenticated: false,
      _hasHydrated: false,

      setAuth: (user, token, refreshToken) => {
        // Kept in plain localStorage too (in addition to zustand's own
        // persisted copy) since lib/api.ts's axios interceptors read the
        // token directly from localStorage on every request/refresh.
        if (typeof window !== "undefined") {
          localStorage.setItem("access_token", token);
          localStorage.setItem("refresh_token", refreshToken);
        }
        set({ user, token, isAuthenticated: true });
      },

      updateUser: (updatedUser) =>
        set((state) => ({
          user: state.user ? { ...state.user, ...updatedUser } : null,
        })),

      logout: () => {
        if (typeof window !== "undefined") {
          localStorage.removeItem("access_token");
          localStorage.removeItem("refresh_token");
        }
        set({ user: null, token: null, isAuthenticated: false });
      },

      setHasHydrated: (state) => {
        set({ _hasHydrated: state });
      },
    }),
    {
      name: "medicare-auth",
      storage: createJSONStorage(() => localStorage),
      partialize: (s) => ({
        user: s.user,
        token: s.token,
        isAuthenticated: s.isAuthenticated,
      }),
      onRehydrateStorage: () => (state) => {
        state?.setHasHydrated(true);
      },
    }
  )
);
