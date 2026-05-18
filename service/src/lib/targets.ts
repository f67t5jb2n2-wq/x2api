export type TargetKind = "user" | "keyword";

export type ParsedTarget = {
  kind: TargetKind;
  value: string;
  normalizedValue: string;
};

export function parseTarget(raw: string): ParsedTarget {
  const value = raw.trim();
  if (!value) {
    throw new Error("Target cannot be empty.");
  }

  if (value.startsWith("search:")) {
    const keyword = value.slice("search:".length).trim();
    if (!keyword) {
      throw new Error("Keyword target cannot be empty.");
    }
    return {
      kind: "keyword",
      value: keyword,
      normalizedValue: keyword.toLowerCase(),
    };
  }

  return {
    kind: "user",
    value,
    normalizedValue: value.toLowerCase(),
  };
}

export function formatTarget(target: ParsedTarget | { kind: TargetKind; value: string }): string {
  return target.kind === "keyword" ? `search:${target.value}` : target.value;
}

export function parseTargets(rawTargets: unknown): ParsedTarget[] {
  if (!Array.isArray(rawTargets)) {
    throw new Error("Expected an array of targets.");
  }

  const seen = new Set<string>();
  const parsed: ParsedTarget[] = [];

  for (const rawTarget of rawTargets) {
    if (typeof rawTarget !== "string") {
      throw new Error("Each target must be a string.");
    }
    const target = parseTarget(rawTarget);
    const key = `${target.kind}:${target.normalizedValue}`;
    if (seen.has(key)) {
      continue;
    }
    seen.add(key);
    parsed.push(target);
  }

  return parsed;
}
