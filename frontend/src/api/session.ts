export interface SessionHandlers {
  onSessionExpired: () => void;
  onPasswordChangeRequired: () => void;
}

const noopHandlers: SessionHandlers = {
  onSessionExpired: () => undefined,
  onPasswordChangeRequired: () => undefined,
};

let accessToken: string | null = null;
let handlers: SessionHandlers = noopHandlers;

export function getAccessToken(): string | null {
  return accessToken;
}

export function setAccessToken(token: string | null): void {
  accessToken = token;
}

export function setSessionHandlers(next: SessionHandlers): () => void {
  handlers = next;
  return () => {
    if (handlers === next) handlers = noopHandlers;
  };
}

export function sessionHandlers(): SessionHandlers {
  return handlers;
}

export function resetSession(): void {
  accessToken = null;
  handlers = noopHandlers;
}
