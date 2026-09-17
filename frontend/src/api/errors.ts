import type { Schemas } from "./types";

export const NETWORK_ERROR_MESSAGE = "Нет связи с сервером";
export const UNKNOWN_ERROR_MESSAGE = "Не удалось выполнить запрос";

export interface Blocker {
  kind: string;
  entity_id: number;
  title: string;
}

export interface ValidationIssue {
  loc: (string | number)[];
  msg: string;
  type: string;
}

interface ApiErrorInit {
  status: number;
  code: string;
  message: string;
  details?: unknown;
  requestId?: string | null;
}

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details: unknown;
  readonly requestId: string | null;

  constructor(init: ApiErrorInit) {
    super(init.message);
    this.name = "ApiError";
    this.status = init.status;
    this.code = init.code;
    this.details = init.details ?? null;
    this.requestId = init.requestId ?? null;
  }
}

type ErrorEnvelope = Schemas["ErrorResponse"];

function isErrorEnvelope(body: unknown): body is ErrorEnvelope {
  if (typeof body !== "object" || body === null || !("error" in body)) return false;
  const error = (body as { error: unknown }).error;
  return (
    typeof error === "object" &&
    error !== null &&
    typeof (error as { code?: unknown }).code === "string" &&
    typeof (error as { message?: unknown }).message === "string"
  );
}

export function apiErrorFromBody(
  status: number,
  body: unknown,
  requestId: string | null,
): ApiError {
  if (isErrorEnvelope(body)) {
    return new ApiError({
      status,
      code: body.error.code,
      message: body.error.message,
      details: body.error.details,
      requestId,
    });
  }
  return new ApiError({ status, code: "unknown_error", message: UNKNOWN_ERROR_MESSAGE, requestId });
}

export function networkError(): ApiError {
  return new ApiError({ status: 0, code: "network_error", message: NETWORK_ERROR_MESSAGE });
}

export function toApiError(error: unknown): ApiError {
  if (error instanceof ApiError) return error;
  return new ApiError({ status: 0, code: "unknown_error", message: UNKNOWN_ERROR_MESSAGE });
}

export function isRetryableError(error: unknown): boolean {
  return error instanceof ApiError && (error.status === 0 || error.status >= 500);
}

export function blockersOf(error: ApiError): Blocker[] {
  if (!Array.isArray(error.details)) return [];
  return error.details.filter(
    (item): item is Blocker =>
      typeof item === "object" &&
      item !== null &&
      typeof (item as Blocker).kind === "string" &&
      typeof (item as Blocker).entity_id === "number" &&
      typeof (item as Blocker).title === "string",
  );
}

export function validationIssuesOf(error: ApiError): ValidationIssue[] {
  if (error.code !== "validation_failed" || !Array.isArray(error.details)) return [];
  return error.details.filter(
    (item): item is ValidationIssue =>
      typeof item === "object" && item !== null && Array.isArray((item as ValidationIssue).loc),
  );
}
