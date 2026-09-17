import { render, screen } from "@testing-library/react";

import { App } from "./App";

test("приложение рендерится", () => {
  render(<App />);

  expect(screen.getByRole("heading", { name: "IT-платформа" })).toBeInTheDocument();
});
