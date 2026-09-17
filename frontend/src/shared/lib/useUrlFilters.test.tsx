import { screen } from "@testing-library/react";

import { renderWithProviders } from "../../test/render";
import { booleanParam, enumParam, textParam, useUrlFilters } from "./useUrlFilters";

const schema = {
  q: textParam,
  role: enumParam(["employee", "manager", "admin"] as const),
  active: booleanParam,
};

function Probe() {
  const { filters, limit, offset, setFilter, setPage } = useUrlFilters(schema);
  return (
    <>
      <output>{JSON.stringify({ ...filters, limit, offset })}</output>
      <button onClick={() => setFilter("role", "manager")}>роль</button>
      <button onClick={() => setPage(50, 50)}>страница</button>
    </>
  );
}

test("читает фильтры из URL и отбрасывает невалидные значения", () => {
  renderWithProviders(<Probe />, {
    initialEntries: ["/?q=ив&role=boss&active=false&limit=33&offset=-1"],
  });

  expect(JSON.parse(screen.getByRole("status").textContent ?? "")).toEqual({
    q: "ив",
    role: null,
    active: false,
    limit: 25,
    offset: 0,
  });
});

test("смена фильтра пишет его в URL и сбрасывает страницу", async () => {
  const { user, router } = renderWithProviders(<Probe />, { initialEntries: ["/?q=ив"] });

  await user.click(screen.getByRole("button", { name: "страница" }));
  expect(router.state.location.search).toBe("?q=%D0%B8%D0%B2&offset=50&limit=50");

  await user.click(screen.getByRole("button", { name: "роль" }));
  expect(router.state.location.search).toBe("?q=%D0%B8%D0%B2&limit=50&role=manager");
});
