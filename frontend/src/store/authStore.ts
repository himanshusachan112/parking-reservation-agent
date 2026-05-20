import { create } from "zustand";

const DEMO_USERNAME = "admin";
// SHA-256 hash of "admin123" — never store plaintext credentials
const DEMO_PASSWORD_HASH =
  "240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9";

async function sha256(message: string): Promise<string> {
  const encoder = new TextEncoder();
  const data = encoder.encode(message);
  const hashBuffer = await crypto.subtle.digest("SHA-256", data);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map((b) => b.toString(16).padStart(2, "0")).join("");
}

interface AuthStore {
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  login: (username: string, password: string) => Promise<boolean>;
  logout: () => void;
  clearError: () => void;
}

export const useAuthStore = create<AuthStore>((set) => ({
  isAuthenticated: false,
  isLoading: false,
  error: null,

  login: async (username: string, password: string) => {
    set({ isLoading: true, error: null });

    // Rate-limit simulation: small delay to deter brute-force
    await new Promise((r) => setTimeout(r, 500));

    const passwordHash = await sha256(password);

    if (
      username.toLowerCase() === DEMO_USERNAME &&
      passwordHash === DEMO_PASSWORD_HASH
    ) {
      set({ isAuthenticated: true, isLoading: false, error: null });
      if (typeof window !== "undefined") {
        sessionStorage.setItem("parksmart_admin_auth", "1");
      }
      return true;
    }

    set({ isLoading: false, error: "Invalid username or password" });
    return false;
  },

  logout: () => {
    set({ isAuthenticated: false, error: null });
    if (typeof window !== "undefined") {
      sessionStorage.removeItem("parksmart_admin_auth");
    }
  },

  clearError: () => set({ error: null }),
}));
