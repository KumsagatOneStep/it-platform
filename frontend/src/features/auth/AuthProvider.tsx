import { useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";

import { api, unwrap } from "../../api/client";
import { refreshAccessToken } from "../../api/refresh";
import { setAccessToken, setSessionHandlers } from "../../api/session";
import type { Me } from "../../api/types";
import { AuthContext, type AuthContextValue, type AuthState } from "./AuthContext";

export const AUTH_CHANNEL = "it-platform-auth";
const LOGOUT_MESSAGE = "logout";

function fetchMe(): Promise<Me> {
  return unwrap(api.GET("/api/auth/me"));
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [state, setState] = useState<AuthState>({ status: "loading" });
  const channelRef = useRef<BroadcastChannel | null>(null);

  const endSession = useCallback(
    (reason?: "logout") => {
      setAccessToken(null);
      queryClient.clear();
      setState({ status: "guest", reason });
    },
    [queryClient],
  );

  useEffect(() => {
    return setSessionHandlers({
      onSessionExpired: () => endSession(),
      onPasswordChangeRequired: () =>
        setState((current) =>
          current.status === "authenticated"
            ? { status: "authenticated", user: { ...current.user, must_change_password: true } }
            : current,
        ),
    });
  }, [endSession]);

  useEffect(() => {
    const channel = new BroadcastChannel(AUTH_CHANNEL);
    channel.onmessage = (event: MessageEvent) => {
      if (event.data === LOGOUT_MESSAGE) endSession("logout");
    };
    channelRef.current = channel;
    return () => {
      channel.close();
      channelRef.current = null;
    };
  }, [endSession]);

  useEffect(() => {
    let cancelled = false;
    const restore = async () => {
      try {
        const token = await refreshAccessToken(null);
        const user = token ? await fetchMe() : null;
        if (!cancelled) setState(user ? { status: "authenticated", user } : { status: "guest" });
      } catch {
        setAccessToken(null);
        if (!cancelled) setState({ status: "guest" });
      }
    };
    void restore();
    return () => {
      cancelled = true;
    };
  }, []);

  const startSession = useCallback(async (accessToken: string) => {
    setAccessToken(accessToken);
    const user = await fetchMe();
    setState({ status: "authenticated", user });
    return user;
  }, []);

  const login = useCallback(
    async (email: string, password: string) => {
      const tokens = await unwrap(api.POST("/api/auth/login", { body: { email, password } }));
      return startSession(tokens.access_token);
    },
    [startSession],
  );

  const changePassword = useCallback(
    async (currentPassword: string, newPassword: string) => {
      const tokens = await unwrap(
        api.POST("/api/auth/change-password", {
          body: { current_password: currentPassword, new_password: newPassword },
        }),
      );
      return startSession(tokens.access_token);
    },
    [startSession],
  );

  const logout = useCallback(async () => {
    try {
      await api.POST("/api/auth/logout");
    } catch {
      // Выход на клиенте выполняется даже без ответа сервера.
    }
    endSession("logout");
    channelRef.current?.postMessage(LOGOUT_MESSAGE);
  }, [endSession]);

  const reloadUser = useCallback(async () => {
    const user = await fetchMe();
    setState({ status: "authenticated", user });
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      state,
      user: state.status === "authenticated" ? state.user : null,
      login,
      logout,
      changePassword,
      reloadUser,
    }),
    [state, login, logout, changePassword, reloadUser],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
