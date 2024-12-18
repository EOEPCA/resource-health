// This is important to make sure that ListCheckTemplates aren't called only when building the website
'use client'

import { StrictRJSFSchema } from '@rjsf/utils'
import axios from 'axios'
import { env } from 'next-runtime-env';

export type CheckTemplateId = string
export type CheckId = string
export type CronExpression = string

export type CheckTemplateMetadata = object & {
  label?: string
  description?: string
}

export type CheckMetadata = object & {
  template_id?: CheckTemplateId
  template_args?: object & {
    label?: string
    description?: string
  }
}

export type CheckTemplate = {
  id: CheckTemplateId
  metadata: CheckTemplateMetadata
  arguments: StrictRJSFSchema
}

type Attributes = Record<string, string | number | boolean>

export type Check = {
  id: CheckId
  metadata: CheckMetadata
  schedule: CronExpression
  outcome_filter: {
    resource_attributes?: Attributes
    scope_attributes?: Attributes
    span_attributes?: Attributes
  }
}

function GetCheckManagerURL(): string {
  const url = env('NEXT_PUBLIC_CHECK_MANAGER_ENDPOINT')
  if (!url) {
    throw new Error(`environment variable NEXT_PUBLIC_CHECK_MANAGER_ENDPOINT must be set`)
  }
  return url
}

function GetTelemetryURL(): string {
  // MUST include /v1 (or some other version) at the end
  const url = env('NEXT_PUBLIC_TELEMETRY_ENDPOINT')
  if (!url) {
    throw new Error(`environment variable NEXT_PUBLIC_TELEMETRY_ENDPOINT must be set`)
  }
  return url
}

export async function ListCheckTemplates(ids?: CheckTemplateId[]): Promise<CheckTemplate[]> {
  const response = await axios.get(GetCheckManagerURL() + "/check_templates/", {params: ids})
  return response.data
}

export async function NewCheck(templateId: CheckTemplateId, templateArgs: object, schedule: CronExpression): Promise<Check> {
  const response = await axios.post(GetCheckManagerURL() + "/checks/", {template_id: templateId, template_args: templateArgs, schedule: schedule})
  return response.data
}

export async function UpdateCheck(oldCheck: Check, templateId?: CheckTemplateId, templateArgs?: object, schedule?: CronExpression): Promise<Check> {
  if (templateId === oldCheck.metadata.template_id) {
    templateId = undefined
  }

  if (templateArgs === oldCheck.metadata.template_args) {
    templateArgs = undefined
  }
  
  if (schedule === oldCheck.schedule) {
    schedule = undefined
  }
  const response = await axios.patch(GetCheckManagerURL() + `/checks/${oldCheck.id}`, {template_id: templateId, template_args: templateArgs, schedule: schedule})
  return response.data
}

export async function RemoveCheck(checkId: CheckId): Promise<void> {
  await axios.delete(GetCheckManagerURL() + `/checks/${checkId}`)
}

export async function ListChecks(ids?: CheckId[]): Promise<Check[]> {
  const response = await axios.get(GetCheckManagerURL() + "/checks/", {params: ids})
  return response.data
}

type Span = {
  traceId: string
  spanId: string
  parentSpanId: string
  startTimeUnixNano: number
  endTimeUnixNano: number
  status: {
    // UNSET = 0
    // OK = 1
    // ERROR = 2
    // According to https://opentelemetry-python.readthedocs.io/en/latest/api/trace.status.html
    code?: 0 | 1 | 2
    message?: string
  }
  attributes: {
    key: string
    value: {
      stringValue: string
    } | {
      intValue: string
    } | unknown
  }[]
}

type SpanResult = {
  resourceSpans: {
    resource: {
      attributes: object[]
    },
    scopeSpans: {
      scope: object
      spans: Span[]
    }[]
  }[]
}

export type SpansResponse = {
  results: SpanResult[]
  next_page_token?: string
}

export type GetSpansQueryParams = {
  traceId?: string
  spanId?: string
  fromTime?: Date
  toTime?: Date
  resourceAttributes?: Attributes
  scopeAttributes?: Attributes
  spanAttributes?: Attributes
}

function AttributesDictToList(attributes?: Attributes): string[] {
  if (attributes === undefined) {
    return []
  }
  return Object.entries(attributes).map(([key, value]) => `${key}=${value}`)
}

export async function GetSpans({traceId, spanId, fromTime, toTime, resourceAttributes, scopeAttributes, spanAttributes, pageToken}: GetSpansQueryParams & { pageToken?: string}): Promise<SpansResponse> {
  if (traceId === undefined && spanId !== undefined) {
    throw new Error("spanId must only be set if traceId is also set")
  }
  const response = await axios.get(
    GetTelemetryURL() + `/spans` + (traceId === undefined ? "" : `/${traceId}`) + (spanId === undefined ? "" : `/${spanId}`),
    {
      params: {
        from_time: fromTime?.toISOString(),
        to_time: toTime?.toISOString(),
        resource_attributes: AttributesDictToList(resourceAttributes),
        scope_attributes: AttributesDictToList(scopeAttributes),
        span_attributes: AttributesDictToList(spanAttributes),
        page_token: pageToken
      },
      paramsSerializer: {
        // Omit brackets when serialize array into the URL.
        // Based on https://stackoverflow.com/a/76517213
        indexes: null,
      }
    }
  )
  return response.data
}

export async function ReduceSpans<T>(getSpansQueryParams: GetSpansQueryParams, callbackFn: (accumulator: T, currentValue: SpanResult) => T, initialValue: T): Promise<T> {
  let pageToken: string | undefined = undefined
  let accumulator: T = initialValue
  do {
    const {results, next_page_token} = await GetSpans({pageToken: pageToken, ...getSpansQueryParams})
    pageToken = next_page_token
    for (const spanResult of results) {
      accumulator = callbackFn(accumulator, spanResult)
    }
  } while (pageToken)
  return accumulator
}