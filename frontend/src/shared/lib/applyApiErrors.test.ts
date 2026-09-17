import { act, renderHook } from "@testing-library/react";
import { useForm } from "react-hook-form";

import { ApiError } from "../../api/errors";
import { applyApiErrors, fieldByCode, INVALID_FIELD_MESSAGE } from "./applyApiErrors";

interface Values {
  name: string;
  email: string;
}

function setup() {
  return renderHook(() => useForm<Values>({ defaultValues: { name: "", email: "" } })).result;
}

test("422 validation_failed раскладывается по полям из loc", () => {
  const form = setup();
  const error = new ApiError({
    status: 422,
    code: "validation_failed",
    message: "Некорректные данные запроса",
    details: [{ loc: ["body", "email"], msg: "value is not a valid email", type: "value_error" }],
  });

  let formMessage: string | null = "";
  act(() => {
    formMessage = applyApiErrors(error, form.current.setError, { fields: ["name", "email"] });
  });

  expect(formMessage).toBeNull();
  expect(form.current.getFieldState("email").error?.message).toBe(INVALID_FIELD_MESSAGE);
});

test("ошибка, которую нельзя отнести к полю, возвращается сообщением формы", () => {
  const form = setup();
  const error = new ApiError({
    status: 422,
    code: "validation_failed",
    message: "Некорректные данные запроса",
    details: [{ loc: ["query", "limit"], msg: "bad", type: "x" }],
  });

  expect(applyApiErrors(error, form.current.setError, { fields: ["name"] })).toBe(
    "Некорректные данные запроса",
  );
});

test("доменный код ошибки ставится на поле по словарю", () => {
  const form = setup();
  const error = new ApiError({
    status: 409,
    code: "email_taken",
    message: "Пользователь с таким email уже существует",
  });

  act(() => {
    applyApiErrors(error, form.current.setError, {
      fields: ["name", "email"],
      fieldForError: fieldByCode<Values>({ email_taken: "email" }),
    });
  });

  expect(form.current.getFieldState("email").error?.message).toBe(
    "Пользователь с таким email уже существует",
  );
});

test("прочие ошибки возвращают message backend, не-ApiError — общий текст", () => {
  const form = setup();
  const conflict = new ApiError({ status: 409, code: "last_admin", message: "Нужен админ" });

  expect(applyApiErrors(conflict, form.current.setError, { fields: [] })).toBe("Нужен админ");
  expect(applyApiErrors(new Error("x"), form.current.setError, { fields: [] })).toBe(
    "Не удалось выполнить запрос",
  );
});
