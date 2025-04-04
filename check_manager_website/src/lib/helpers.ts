import {
  Check,
  CheckTemplate,
  CheckTemplateId,
  GetSpansQueryParams,
  ReduceSpans,
  Span,
  SpanResult,
  SpanStatus,
} from "./backend-wrapper";
import { Dispatch, SetStateAction, useEffect, useState } from "react";
import { sub as subDuration } from "date-fns";
import { TELEMETRY_DURATION } from "./config";

export const LOADING_STRING = "Loading ...";

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

export function StringifyPretty(json: object): string {
  return JSON.stringify(json, null, 2);
}

export function GetSpanFilterParams(
  check: Check,
  now: Date
): GetSpansQueryParams {
  return {
    fromTime: subDuration(now, TELEMETRY_DURATION),
    toTime: now,
    resourceAttributes: check.attributes.outcome_filter.resource_attributes,
    scopeAttributes: check.attributes.outcome_filter.scope_attributes,
    spanAttributes: check.attributes.outcome_filter.span_attributes,
  };
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
          traceIdToSpans[traceId] = { resourceSpans: [] };
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
  traceIds: Set<string>;
  failedTraceIds: Set<string>;
  totalDurationSecs: number;
  durationCount: number;
  totalTestCount: number;
};

export function GetAverageDuration(spansSummary: SpansSummary): string {
  return spansSummary.durationCount === 0
    ? "N/A"
    : (
        spansSummary.totalDurationSecs / spansSummary.durationCount
      ).toLocaleString() + " s";
}

export async function ComputeSpansSummary(
  getSpansQueryParams: GetSpansQueryParams
): Promise<SpansSummary> {
  return ReduceSpans<SpansSummary>(
    getSpansQueryParams,
    (
      {
        traceIds,
        failedTraceIds,
        totalDurationSecs,
        durationCount,
        totalTestCount,
      },
      spanResult
    ) => {
      for (const resourceSpans of spanResult.resourceSpans) {
        for (const scopeSpans of resourceSpans.scopeSpans) {
          for (const span of scopeSpans.spans) {
            traceIds.add(span.traceId);
            if (IsSpanError(span)) {
              failedTraceIds.add(span.traceId);
            }
            if (span.parentSpanId === "") {
              totalDurationSecs +=
                (span.endTimeUnixNano - span.startTimeUnixNano) / 1_000_000_000;
              durationCount++;
            }
            for (const attribute of span.attributes) {
              if (attribute.key === "test.case.result.status") {
                totalTestCount++;
                break;
              }
            }
          }
        }
      }
      return {
        traceIds,
        failedTraceIds,
        totalDurationSecs,
        durationCount,
        totalTestCount,
      };
    },
    {
      traceIds: new Set<string>(),
      failedTraceIds: new Set<string>(),
      totalDurationSecs: 0,
      durationCount: 0,
      totalTestCount: 0,
    }
  );
}

export function IsSpanError(span: Span): boolean {
  return span.status?.code === SpanStatus.ERROR;
}
