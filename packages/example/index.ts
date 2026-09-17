import { normalizeGreetingTarget } from "./lib/impl";

/** Returns a consistently formatted greeting without exposing its formatting implementation. */
export function greet(target: string): string {
  return `Hello, ${normalizeGreetingTarget(target)}!`;
}
