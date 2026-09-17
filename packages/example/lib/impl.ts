export function normalizeGreetingTarget(target: string): string {
  return target.trim() || "world";
}
