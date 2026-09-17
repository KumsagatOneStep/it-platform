import { StatusPage } from "../shared/ui/StatusPage";

export function NotFoundPage() {
  return (
    <StatusPage
      code={404}
      title="Страница не найдена"
      text="Возможно, ссылка устарела или в адресе опечатка."
    />
  );
}
