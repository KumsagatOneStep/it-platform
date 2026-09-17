/** Возвращает безопасный путь для перехода после входа: только относительный путь приложения. */
export function safeNext(next: string | null | undefined, fallback = "/"): string {
  if (!next || !next.startsWith("/") || next.startsWith("//") || next.startsWith("/\\")) {
    return fallback;
  }
  return next;
}

export function loginPathFor(pathname: string, search: string): string {
  const target = `${pathname}${search}`;
  return target === "/" ? "/login" : `/login?next=${encodeURIComponent(target)}`;
}
