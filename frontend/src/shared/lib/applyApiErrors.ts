import type { FieldPath, FieldValues, UseFormSetError } from "react-hook-form";

import { ApiError, UNKNOWN_ERROR_MESSAGE, validationIssuesOf } from "../../api/errors";

export const INVALID_FIELD_MESSAGE = "Некорректное значение";

interface ApplyApiErrorsOptions<T extends FieldValues> {
  /** Поля формы, совпадающие по имени с полями тела запроса. */
  fields: readonly FieldPath<T>[];
  /** Поле, к которому относится доменная ошибка backend (по коду или деталям). */
  fieldForError?: (error: ApiError) => FieldPath<T> | undefined;
}

/**
 * Раскладывает ошибку API по полям формы. Возвращает сообщение для показа над формой
 * или null, если всё разложено по полям.
 */
export function applyApiErrors<T extends FieldValues>(
  error: unknown,
  setError: UseFormSetError<T>,
  { fields, fieldForError }: ApplyApiErrorsOptions<T>,
): string | null {
  if (!(error instanceof ApiError)) return UNKNOWN_ERROR_MESSAGE;

  const field = fieldForError?.(error);
  if (field) {
    setError(field, { type: "server", message: error.message });
    return null;
  }

  const issues = validationIssuesOf(error);
  if (issues.length === 0) return error.message;

  let unmapped = false;
  for (const issue of issues) {
    const [location, name] = issue.loc;
    const target = fields.find((candidate) => candidate === name);
    if (location === "body" && target) {
      setError(target, { type: "server", message: INVALID_FIELD_MESSAGE });
    } else {
      unmapped = true;
    }
  }
  return unmapped ? error.message : null;
}

/** Строит `fieldForError` по словарю «код ошибки → поле». */
export function fieldByCode<T extends FieldValues>(
  map: Partial<Record<string, FieldPath<T>>>,
): (error: ApiError) => FieldPath<T> | undefined {
  return (error) => map[error.code];
}
