import { useCallback, useMemo } from "react";
import { useSearchParams } from "react-router";

export const PAGE_SIZES = [25, 50, 100] as const;
const DEFAULT_LIMIT = PAGE_SIZES[0];

// Методы (а не свойства-функции), чтобы UrlParam<string> был совместим с UrlParam<unknown>.
export interface UrlParam<V> {
  parse(raw: string | null): V;
  serialize(value: V): string | null;
}

export const textParam: UrlParam<string> = {
  parse: (raw) => raw ?? "",
  serialize: (value) => (value.trim() ? value : null),
};

export function enumParam<T extends string>(values: readonly T[]): UrlParam<T | null> {
  return {
    parse: (raw) => values.find((value) => value === raw) ?? null,
    serialize: (value) => value,
  };
}

export const idParam: UrlParam<number | null> = {
  parse: (raw) => {
    const value = Number(raw);
    return raw && Number.isInteger(value) && value > 0 ? value : null;
  },
  serialize: (value) => (value === null ? null : String(value)),
};

export const booleanParam: UrlParam<boolean | null> = {
  parse: (raw) => (raw === "true" ? true : raw === "false" ? false : null),
  serialize: (value) => (value === null ? null : String(value)),
};

type ParamValues<S extends Record<string, UrlParam<unknown>>> = {
  [K in keyof S]: S[K] extends UrlParam<infer V> ? V : never;
};

function parseLimit(raw: string | null): number {
  const value = Number(raw);
  return PAGE_SIZES.find((size) => size === value) ?? DEFAULT_LIMIT;
}

function parseOffset(raw: string | null): number {
  const value = Number(raw);
  return raw && Number.isInteger(value) && value >= 0 ? value : 0;
}

/** Фильтры и пагинация списка в search params: ссылкой можно поделиться, перезагрузка их не теряет. */
export function useUrlFilters<S extends Record<string, UrlParam<unknown>>>(schema: S) {
  const [searchParams, setSearchParams] = useSearchParams();

  const filters = useMemo(() => {
    const values: Record<string, unknown> = {};
    for (const [key, param] of Object.entries(schema)) {
      values[key] = param.parse(searchParams.get(key));
    }
    return values as ParamValues<S>;
  }, [schema, searchParams]);

  const limit = parseLimit(searchParams.get("limit"));
  const offset = parseOffset(searchParams.get("offset"));

  const setFilter = useCallback(
    <K extends keyof S & string>(key: K, value: ParamValues<S>[K]) => {
      setSearchParams(
        (current) => {
          const next = new URLSearchParams(current);
          const serialized = schema[key]!.serialize(value);
          if (serialized === null) next.delete(key);
          else next.set(key, serialized);
          next.delete("offset");
          return next;
        },
        { replace: true },
      );
    },
    [schema, setSearchParams],
  );

  const setPage = useCallback(
    (nextOffset: number, nextLimit: number) => {
      setSearchParams(
        (current) => {
          const next = new URLSearchParams(current);
          if (nextOffset > 0) next.set("offset", String(nextOffset));
          else next.delete("offset");
          if (nextLimit !== DEFAULT_LIMIT) next.set("limit", String(nextLimit));
          else next.delete("limit");
          return next;
        },
        { replace: true },
      );
    },
    [setSearchParams],
  );

  return { filters, limit, offset, setFilter, setPage };
}
