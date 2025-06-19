import { Duration } from "date-fns";
import { env } from "next-runtime-env";

export const telemetryDurationOptions: Duration[] = [
  { days: 1 },
  { weeks: 1 },
  { months: 1 },
  { years: 1 },
];

export const DEFAULT_TELEMETRY_DURATION: Duration = telemetryDurationOptions[1];

export function GetSpansQueryPageSize(): number {
  const page_size = env("NEXT_PUBLIC_QUERY_PAGE_SIZE");
  return page_size ? Number(page_size) : 200;
}

export function GetCheckManagerURL(): string {
  // MUST include /v1 (or some other version) at the end
  return GetEnvVarOrThrow("NEXT_PUBLIC_CHECK_MANAGER_ENDPOINT");
}

export function GetTelemetryURL(): string {
  // MUST include /v1 (or some other version) at the end
  return GetEnvVarOrThrow("NEXT_PUBLIC_TELEMETRY_ENDPOINT");
}

export function GetReLoginURL(): string {
  return GetEnvVarOrThrow("NEXT_PUBLIC_RELOGIN_URL");
}

function GetEnvVarOrThrow(envVar: string): string {
  const url = env(envVar);
  if (!url) {
    throw new Error(`environment variable ${envVar} must be set`);
  }
  return url;
}
