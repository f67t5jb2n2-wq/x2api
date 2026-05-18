type FullQueryLike<T> = {
  rows?: T[];
};

export function asRows<T>(result: unknown): T[] {
  if (Array.isArray(result)) {
    return result as T[];
  }

  if (result && typeof result === "object" && "rows" in result) {
    const rows = (result as FullQueryLike<T>).rows;
    if (Array.isArray(rows)) {
      return rows;
    }
  }

  return [];
}
