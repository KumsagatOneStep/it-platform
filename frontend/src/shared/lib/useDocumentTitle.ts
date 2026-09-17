import { useEffect } from "react";

export const APP_TITLE = "IT-платформа";

export function useDocumentTitle(title: string): void {
  useEffect(() => {
    document.title = `${title} — ${APP_TITLE}`;
  }, [title]);
}
