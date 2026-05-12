export function logPerformance(event: string, details: Record<string, unknown>) {
  console.info(`[performance] ${event}`, details);
}

export async function withTiming<T>(name: string, fn: () => Promise<T>): Promise<T> {
  const start = Date.now();
  try {
    return await fn();
  } finally {
    const durationMs = Date.now() - start;
    logPerformance(name, { durationMs });
  }
}
