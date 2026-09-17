import { createContext, useContext } from "react";

import type { Me } from "../../api/types";

export type AuthState =
  { status: "loading" } | { status: "guest" } | { status: "authenticated"; user: Me };

export interface AuthContextValue {
  state: AuthState;
  user: Me | null;
  login: (email: string, password: string) => Promise<Me>;
  logout: () => Promise<void>;
  changePassword: (currentPassword: string, newPassword: string) => Promise<Me>;
}

export const AuthContext = createContext<AuthContextValue | null>(null);

export function useAuth(): AuthContextValue {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth должен использоваться внутри AuthProvider");
  return value;
}
