import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";

// ==========================================
// 1. Type Definitions
// ==========================================
export interface User {
  id: number | string;
  email: string;
  full_name: string;
  phone?: string | null;
  role?: string;
  is_verified?: boolean;
  avatar_url?: string;
}

interface AuthState {
  // State
  user: User | null;
  accessToken: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  
  // Hydration state for Next.js SSR safe rendering
  _hasHydrated: boolean;

  // Actions
  setAuth: (user: User, accessToken: string, refreshToken: string) => void;
  updateUser: (user: Partial<User>) => void;
  logout: () => void;
  setHasHydrated: (state: boolean) => void;
}

// ==========================================
// 2. Zustand Store Setup
// ==========================================
export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      // Initial State
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
      _hasHydrated: false,

      // --- Actions ---

      // 3. Set Auth (Login / Refresh)
      setAuth: (user, accessToken, refreshToken) => {
        // Sync with standard localStorage for Axios interceptors (from lib/api.ts)
        // Zustand persist will also save it, but this acts as a double-safety net for raw API calls
        if (typeof window !== "undefined") {
          localStorage.setItem("access_token", accessToken);
          localStorage.setItem("refresh_token", refreshToken);
        }

        set({
          user,
          accessToken,
          refreshToken,
          isAuthenticated: true,
        });
      },

      // 4. Update partial user profile (e.g., after editing profile)
      updateUser: (updatedUser) =>
        set((state) => ({
          user: state.user ? { ...state.user, ...updatedUser } : null,
        })),

      // 5. Secure Logout
      logout: () => {
        // Clear standard localStorage used by Axios
        if (typeof window !== "undefined") {
          localStorage.removeItem("access_token");
          localStorage.removeItem("refresh_token");
        }

        // Clear Zustand state
        set({
          user: null,
          accessToken: null,
          refreshToken: null,
          isAuthenticated: false,
        });

        // Hard redirect to login to clear all React Query cache & states from memory
        if (typeof window !== "undefined") {
          window.location.href = "/login";
        }
      },

      // 6. Hydration setter
      setHasHydrated: (state) => {
        set({ _hasHydrated: state });
      },
    }),
    {
      name: "auth-storage", // Key used in localStorage
      storage: createJSONStorage(() => localStorage),
      
      // 7. Hydration Callback for Next.js SSR
      onRehydrateStorage: () => (state) => {
        // This runs after Zustand has loaded state from localStorage
        state?.setHasHydrated(true);
      },
      
      // Optional: Don't persist _hasHydrated state itself
      partialize: (state) => ({
        user: state.user,
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);