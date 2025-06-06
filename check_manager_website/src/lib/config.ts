import { Duration } from "date-fns";

export const telemetryDurationOptions: Duration[] = [
  { days: 1 },
  { weeks: 1 },
  { months: 1 },
  //   { years: 1 },
];

export const DEFAULT_TELEMETRY_DURATION: Duration = telemetryDurationOptions[1];
