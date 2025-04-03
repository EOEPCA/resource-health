import { CheckTemplate, CheckTemplateId, GetSpansQueryParams, ReduceSpans } from "./backend-wrapper"
import { Dispatch, SetStateAction, useEffect, useState } from "react"

export const LOADING_STRING = "Loading ..."

// The same as in https://upmostly.com/next-js/using-localstorage-in-next-js, but use sessionStorage instead of localStorage
// so that the data is deleted when the browser is closed.
export function useSessionStorage<T>(key: string, defaultValue: T): [T, Dispatch<SetStateAction<T>>] {
  const [value, setValue] = useState(defaultValue);
  // Get value from storage
  useEffect(() => {
    const stored = sessionStorage.getItem(key)
    if (stored !== null) {
      setValue(JSON.parse(stored))
    }
  }, [key])
  // When value changes, store it
  useEffect(() => {
    sessionStorage.setItem(key, JSON.stringify(value))
  }, [key, value])

  return [value, setValue] as const
}

export function FindCheckTemplate(templates: CheckTemplate[], templateId: CheckTemplateId): CheckTemplate {
  const template = templates.find((template) => template.id === templateId)
  if (template === undefined) {
    throw Error(`template with id ${templateId} not found`)
  }
  return template
}

export type SpansSummary = {
  traceIds: Set<string>
  failedTraceIds: Set<string>
  totalDurationSecs: number
  durationCount: number
  totalTestCount: number
}

export function GetAverageDuration(spansSummary: SpansSummary): string {
  return spansSummary.durationCount === 0 ? "N/A" : (spansSummary.totalDurationSecs / spansSummary.durationCount).toLocaleString() + " s"
}

export async function ComputeSpansSummary(getSpansQueryParams: GetSpansQueryParams): Promise<SpansSummary> {
  return ReduceSpans<SpansSummary>(
    getSpansQueryParams,
    ({ traceIds, failedTraceIds, totalDurationSecs, durationCount, totalTestCount }, spanResult) => {
      for (const resourceSpans of spanResult.resourceSpans) {
        for (const scopeSpans of resourceSpans.scopeSpans) {
          for (const span of scopeSpans.spans) {
            traceIds.add(span.traceId)
            if (span.status?.code === 2) {
              failedTraceIds.add(span.traceId)
            }
            if (span.parentSpanId === "") {
              totalDurationSecs += (span.endTimeUnixNano - span.startTimeUnixNano) / 1_000_000_000
              durationCount++
            }
            for (const attribute of span.attributes) {
              if (attribute.key === 'test.case.result.status') {
                totalTestCount++
                break
              }
            }
          }
        }
      }
      return { traceIds, failedTraceIds, totalDurationSecs, durationCount, totalTestCount }
    },
    { traceIds: new Set<string>(), failedTraceIds: new Set<string>(), totalDurationSecs: 0, durationCount: 0, totalTestCount: 0 }
  )
}