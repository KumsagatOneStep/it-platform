export function errorBody(code: string, message: string, details: unknown = null) {
  return { error: { code, message, details } };
}
