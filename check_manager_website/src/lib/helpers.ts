import {
  Check,
  CheckTemplate,
  CheckTemplateId,
  GetEmptySpanResult,
  GetSpansQueryParams,
  ReduceSpans,
  Span,
  SpanResult,
  SpanStatus,
  TelemetryAttributes,
} from "./backend-wrapper";
import {
  DependencyList,
  Dispatch,
  SetStateAction,
  useEffect,
  useState,
} from "react";
import { Duration, formatDuration, sub as subDuration } from "date-fns";
import { DEFAULT_TELEMETRY_DURATION, telemetryDurationOptions } from "./config";
import {
  DefaultErrorHandler,
  SetErrorsPropsType,
} from "@/components/CheckError";
import { useSearchParams } from "next/navigation";

export const durationStringToDuration: Map<string, Duration> = new Map(
  telemetryDurationOptions.map((duration) => [
    formatDuration(duration),
    duration,
  ])
);

export type FetchState = "Loading" | "Completed";

export type SetResultType<T> = (result: T, fetchState: FetchState) => void;

export type IncrementalFetchType<T> = (
  setResult: SetResultType<T>
) => Promise<void>;

// The difference from func().then(...).catch(...) is that it handles errors and retries with setErrorProps
export function CallBackend<T>(
  func: IncrementalFetchType<T>,
  setResult: SetResultType<T>,
  setErrorsProps: SetErrorsPropsType
): void {
  func(setResult).catch(
    DefaultErrorHandler(setErrorsProps, () =>
      CallBackend<T>(func, setResult, setErrorsProps)
    )
  );
}

// // The difference from func().then(...).catch(...) is that it handles errors and retries with setErrorProps
// export function CallBackend<T>(
//   func: () => Promise<void>,
//   setErrorsProps: SetErrorsPropsType
// ): void {
//   func().catch(
//     DefaultErrorHandler(setErrorsProps, () =>
//       CallBackend<T>(func, setErrorsProps)
//     )
//   );
// }

export function FetchToIncremental<T>(
  fetch: () => Promise<T>
): IncrementalFetchType<T> {
  return async (setResult) => {
    const result = await fetch();
    setResult(result, "Completed");
  };
}

export type UseFetchStateProps<T> = {
  initialValue: T;
  fetch: IncrementalFetchType<T>;
  setErrorsProps: SetErrorsPropsType;
  deps: DependencyList;
};

export function useFetchState<T>({
  initialValue,
  fetch,
  setErrorsProps,
  deps,
}: UseFetchStateProps<T>): [T, (value: T) => void, FetchState] {
  const [value, setValue] = useState<T>(initialValue);
  const [fetchState, setFetchState] = useState<FetchState>("Loading");
  useEffect(
    () => {
      setValue(initialValue);
      setFetchState("Loading");
      CallBackend(
        fetch,
        (result, fetchState) => {
          setValue(result);
          setFetchState(fetchState);
        },
        setErrorsProps
      );
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    deps
  );
  return [value, setValue, fetchState] as const;
}

const DURATION_QUERY_KEY = "duration";

// Gets from query parameter, and if doesn't exist, uses a default
export function useTelemetryDuration(): string {
  const searchParams = useSearchParams();
  return (
    searchParams.get(DURATION_QUERY_KEY) ??
    formatDuration(DEFAULT_TELEMETRY_DURATION)
  );
}

export function GetRelLink({
  checkId,
  traceId,
}: {
  checkId?: string;
  traceId?: string;
}) {
  if (checkId === undefined) {
    return "/";
  }
  if (traceId === undefined) {
    return `/check/${checkId}`;
  }
  return `/check/${checkId}/trace/${traceId}`;
}

// export function GetRelLink({
//   checkId,
//   traceId,
//   telemetryDuration,
// }: {
//   checkId?: string;
//   traceId?: string;
//   telemetryDuration?: Duration;
// }) {
//   let path: string;
//   if (checkId === undefined) {
//     path = "/";
//   } else {
//     if (traceId === undefined) {
//       path = `/check/${checkId}`;
//     } else {
//       path = `/check/${checkId}/trace/${traceId}`;
//     }
//   }
//   const query = telemetryDuration
//     ? `?${DURATION_QUERY_KEY}=${formatDuration(telemetryDuration)}`
//     : "";
//   return path + query;
// }

export function StringifyPretty(json: object): string {
  return JSON.stringify(json, null, 2);
}

export function GetSpanFilterParams(
  check: Check,
  delemetryDuration: Duration,
  now: Date
): GetSpansQueryParams {
  return {
    fromTime: subDuration(now, delemetryDuration),
    toTime: now,
    resourceAttributes: check.attributes.outcome_filter.resource_attributes,
    scopeAttributes: check.attributes.outcome_filter.scope_attributes,
    spanAttributes: check.attributes.outcome_filter.span_attributes,
  };
}

// Escape special DQL characters
function EscChars(str: string): string {
  const specialChars = '\\():<>"*';
  let result: string = "";
  for (let i = 0; i < str.length; i++) {
    result += specialChars.includes(str[i]) ? "\\" : "";
    result += str[i];
  }
  return result;
}

function AttributesToFilters(
  attributes: TelemetryAttributes,
  keyPrefix: string
): string {
  const resultParts: string[] = [];
  for (const [key, values] of Object.entries(attributes)) {
    const finalKey = EscChars(keyPrefix + key);
    if (values === null) {
      resultParts.push(`${finalKey}:*`);
    } else {
      const parts = values.map((value) => {
        const finalKeySuffix = typeof value == "string" ? ".keyword" : "";
        return `${finalKey + finalKeySuffix}: ${EscChars(value.toString())}`;
      });
      const innerString = parts.join(" or ");
      resultParts.push(
        parts.length > 1 ? "(" + innerString + ")" : innerString
      );
    }

    // resultParts.push(
    //   `${EscChars(keyPrefix + key)}: ${EscChars(value.toString())}`
    // );
  }
  return resultParts.join(" and ");
}

export function SpanFilterParamsToDql({
  traceId,
  spanId,
  // Ignored for now as DQL search has its own separate time selection
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  fromTime,
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  toTime,
  resourceAttributes,
  scopeAttributes,
  spanAttributes,
}: GetSpansQueryParams): string {
  // function DateToUnixNano(date: Date): number {
  //   return Math.floor(date.getTime() * 1_000_000);
  // }
  const queryParts: string[] = [];
  if (traceId !== undefined) {
    queryParts.push(`traceId: ${EscChars(traceId)}`);
  }
  if (spanId !== undefined) {
    queryParts.push(`spanId: ${EscChars(spanId)}`);
  }
  // if (fromTime !== undefined) {
  //   queryParts.push(`startTime >= ${EscChars(fromTime.toISOString())}`);
  // }
  // if (toTime !== undefined) {
  //   queryParts.push(`endTime <= ${EscChars(toTime.toISOString())}`);
  // }
  if (resourceAttributes !== undefined) {
    queryParts.push(AttributesToFilters(resourceAttributes, "resource."));
  }
  if (scopeAttributes !== undefined) {
    queryParts.push(
      AttributesToFilters(scopeAttributes, "instrumentationScope.")
    );
  }
  if (spanAttributes !== undefined) {
    queryParts.push(AttributesToFilters(spanAttributes, "attributes."));
  }
  return queryParts.join(" and ");
}

export function GetTraceIdToSpans(
  spans: SpanResult
): Record<string, SpanResult> {
  const traceIdToSpans: Record<string, SpanResult> = {};
  for (const resourceSpans of spans.resourceSpans) {
    for (const scopeSpans of resourceSpans.scopeSpans) {
      for (const span of scopeSpans.spans) {
        const traceId = span.traceId;
        if (!(traceId in traceIdToSpans)) {
          traceIdToSpans[traceId] = GetEmptySpanResult();
        }
        const traceResourceSpans = traceIdToSpans[traceId].resourceSpans;
        // This also correctly deals with empty arrays, as at(-1) will return undefined in that case
        if (traceResourceSpans.at(-1)?.resource != resourceSpans.resource) {
          traceResourceSpans.push({
            resource: resourceSpans.resource,
            scopeSpans: [],
          });
        }
        const traceScopeSpans =
          traceResourceSpans[traceResourceSpans.length - 1].scopeSpans;
        if (traceScopeSpans.at(-1)?.scope != scopeSpans.scope) {
          traceScopeSpans.push({
            scope: scopeSpans.scope,
            spans: [],
          });
        }
        const traceSpans = traceScopeSpans[traceScopeSpans.length - 1].spans;
        traceSpans.push(span);
      }
    }
  }
  return traceIdToSpans;
}

// The same as in https://upmostly.com/next-js/using-localstorage-in-next-js, but use sessionStorage instead of localStorage
// so that the data is deleted when the browser is closed.
export function useSessionStorage<T>(
  key: string,
  defaultValue: T
): [T, Dispatch<SetStateAction<T>>] {
  const [value, setValue] = useState(defaultValue);
  // Get value from storage
  useEffect(() => {
    const stored = sessionStorage.getItem(key);
    if (stored !== null) {
      setValue(JSON.parse(stored));
    }
  }, [key]);
  // When value changes, store it
  useEffect(() => {
    sessionStorage.setItem(key, JSON.stringify(value));
  }, [key, value]);

  return [value, setValue] as const;
}

export function FindCheckTemplate(
  templates: CheckTemplate[],
  templateId: CheckTemplateId
): CheckTemplate {
  const template = templates.find((template) => template.id === templateId);
  if (template === undefined) {
    throw Error(`template with id ${templateId} not found`);
  }
  return template;
}

export type SpansSummary = {
  traceIdsCount: number;
  failedTraceIdsCount: number;
  totalDurationSecs: number;
  durationCount: number;
  totalTestCount: number;
};

export const EmptySpansSummary: SpansSummary = {
  traceIdsCount: 0,
  failedTraceIdsCount: 0,
  totalDurationSecs: 0,
  durationCount: 0,
  totalTestCount: 0,
};

type DetailedSpansSummary = {
  traceIds: Set<string>;
  failedTraceIds: Set<string>;
  totalDurationSecs: number;
  durationCount: number;
  totalTestCount: number;
};

function SimplifySummary(detailedSummary: DetailedSpansSummary): SpansSummary {
  return {
    traceIdsCount: detailedSummary.traceIds.size,
    failedTraceIdsCount: detailedSummary.failedTraceIds.size,
    totalDurationSecs: detailedSummary.totalDurationSecs,
    durationCount: detailedSummary.durationCount,
    totalTestCount: detailedSummary.totalTestCount,
  };
}

export function GetAverageDuration(
  totalDurationSecs: number,
  durationCount: number
): string {
  return durationCount === 0
    ? "N/A"
    : (totalDurationSecs / durationCount).toLocaleString() + " s";
}

export type ComputeSpansSummaryProps = {
  getSpansQueryParams: GetSpansQueryParams;
  setResult: SetResultType<SpansSummary>;
};

export async function ComputeSpansSummary({
  getSpansQueryParams,
  setResult,
}: ComputeSpansSummaryProps): Promise<void> {
  // const [spansSummary, setSpansSummary] = useState<SpansSummary>(null);
  const detailedSummary = await ReduceSpans<DetailedSpansSummary>(
    getSpansQueryParams,
    (detailedSummary, spanResult) => {
      for (const resourceSpans of spanResult.resourceSpans) {
        for (const scopeSpans of resourceSpans.scopeSpans) {
          for (const span of scopeSpans.spans) {
            detailedSummary.traceIds.add(span.traceId);
            if (IsSpanError(span)) {
              detailedSummary.failedTraceIds.add(span.traceId);
            }
            if (span.parentSpanId === "") {
              detailedSummary.totalDurationSecs +=
                (span.endTimeUnixNano - span.startTimeUnixNano) / 1_000_000_000;
              detailedSummary.durationCount++;
            }
            for (const attribute of span.attributes) {
              if (attribute.key === "test.case.result.status") {
                detailedSummary.totalTestCount++;
                break;
              }
            }
          }
        }
      }
      setResult(SimplifySummary(detailedSummary), "Loading");
      return detailedSummary;
    },
    {
      traceIds: new Set<string>(),
      failedTraceIds: new Set<string>(),
      totalDurationSecs: 0,
      durationCount: 0,
      totalTestCount: 0,
    }
  );

  setResult(SimplifySummary(detailedSummary), "Completed");
}

export type GetAllSpansProps = {
  getSpansQueryParams: GetSpansQueryParams;
  setResult: SetResultType<SpanResult>;
};

export async function GetAllSpans({
  getSpansQueryParams,
  setResult,
}: GetAllSpansProps): Promise<void> {
  setResult(GetEmptySpanResult(), "Loading");
  const allSpans = await ReduceSpans<SpanResult>(
    getSpansQueryParams,
    ({ resourceSpans }: SpanResult, currentValue: SpanResult) => {
      resourceSpans.push(...currentValue.resourceSpans);
      // Important that the first argument to setResult is always a different object
      // so that React picks up when it changes
      setResult({ resourceSpans }, "Loading");
      return { resourceSpans };
    },
    GetEmptySpanResult()
  );
  setResult(allSpans, "Completed");
}

export function IsStatusError(status: SpanStatus): boolean {
  return status?.code === SpanStatus.ERROR;
}

export function IsSpanError(span: Span): boolean {
  return IsStatusError(span.status);
}
