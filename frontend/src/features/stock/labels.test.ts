import { makeStockMovement } from "../../test/fixtures";
import { formatDelta, movementDetails, movementTitle } from "./labels";

test("изменение количества со знаком и единицей", () => {
  expect(formatDelta(10, "шт")).toBe("+10 шт");
  expect(formatDelta(-3, "уп")).toBe("−3 уп");
});

test("заголовок движения по типу", () => {
  expect(movementTitle("receipt")).toBe("Приход");
  expect(movementTitle("transfer_out")).toBe("Перемещение: отправлено");
});

test("подробности движения: получатель, склад, дата документа, причина", () => {
  expect(
    movementDetails(
      makeStockMovement({
        movement_type: "issue",
        recipient_name: "Петров Пётр",
        reason_name: "Новый сотрудник",
      }),
    ),
  ).toEqual(["Кому: Петров Пётр", "Причина: Новый сотрудник"]);
  expect(
    movementDetails(
      makeStockMovement({ movement_type: "transfer_out", counterpart_location_name: "Офис" }),
    ),
  ).toEqual(["Куда: Офис"]);
  expect(
    movementDetails(
      makeStockMovement({ movement_type: "transfer_in", counterpart_location_name: "Склад" }),
    ),
  ).toEqual(["Откуда: Склад"]);
  expect(
    movementDetails(makeStockMovement({ movement_type: "receipt", document_date: "2026-09-01" })),
  ).toEqual(["Дата документа: 01.09.2026"]);
});
