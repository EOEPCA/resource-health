// This is important to make sure that ListCheckTemplates aren't called only when building the website
"use client";

import { StrictRJSFSchema } from "@rjsf/utils";
import axios, { AxiosResponse } from "axios";
import { env } from "next-runtime-env";

export type CheckTemplateId = string;
export type CheckId = string;
export type CronExpression = string;

export type Json = Record<string, unknown>;

type Link =
  | string
  | {
      href: string;
      title?: string;
    };

type Links = {
  self?: Link;
  describedby?: Link;
  first?: Link;
  next?: Link;
  root?: Link;
} & Record<string, unknown>;

type Resource<T> = {
  id: string;
  type: string;
  attributes: T;
  links?: Record<string, Link>;
};

// A JSON Pointer [RFC6901] to the value in the request document that caused the error
// [e.g. "/data" for a primary data object, or "/data/attributes/title" for a specific attribute].
// This MUST point to a value in the request document that exists; if it doesn’t, the client SHOULD simply ignore the pointer.
type ErrorSourcePointer = {
  pointer: string;
};

// A string indicating which URI query parameter caused the error.
type ErrorSourceParameter = {
  parameter: string;
};

// a string indicating the name of a single request header which caused the error.
type ErrorSourceHeader = {
  header: string;
};

// See https://jsonapi.org/examples/#error-objects
type ErrorSource =
  | ErrorSourcePointer
  | ErrorSourceParameter
  | ErrorSourceHeader;

type Error = {
  status: string;
  code: string;
  title: string;
  detail?: string;
  source?: ErrorSource;
  meta?: Json;
};

type APIOKResponse<T> = {
  data: Resource<T>;
  links?: Links;
};

type APIOKResponseList<T, U> = {
  data: Resource<T>[];
  meta: U;
  links?: Links;
};

// eslint-disable-next-line @typescript-eslint/no-unused-vars
type APIErrorResponse = {
  errors: Error[];
};

export type CheckTemplateMetadata = object & {
  label?: string;
  description?: string;
};

export type CheckTemplateAttributes = {
  metadata: CheckTemplateMetadata;
  arguments: StrictRJSFSchema;
};

export type CheckTemplate = Resource<CheckTemplateAttributes>;

type InCheckMetadata = {
  // SHOULD have name and description
  name: string;
  description: string;
  // MAY have template_id and template_args
  template_id: CheckTemplateId;
  template_args: Json;
};

type OutCheckMetadata = {
  // SHOULD have name and description
  name?: string;
  description?: string;
  // MAY have template_id and template_args
  template_id?: CheckTemplateId;
  template_args?: Json;
} & Record<string, unknown>;

type InCheckAttributes = {
  metadata: InCheckMetadata;
  schedule: CronExpression;
};

export type TelemetryAttributes = Record<
  string,
  (string | number | boolean)[] | null
>;

type OutcomeFilter = {
  resource_attributes?: TelemetryAttributes;
  scope_attributes?: TelemetryAttributes;
  span_attributes?: TelemetryAttributes;
};

type OutCheckAttributes = {
  metadata: OutCheckMetadata;
  schedule: CronExpression;
  // Conditions to determine which spans belong to this check outcome
  outcome_filter: OutcomeFilter;
  // NOTE: For now the above can just be a set of equality conditions on Span/Resource attributes
};

export type Check = Resource<OutCheckAttributes>;

type InCheckData = {
  // Should always be "check"
  type: string;
  attributes: InCheckAttributes;
};

type InCheck = {
  data: InCheckData;
};

function GetCheckManagerURL(): string {
  const url = env("NEXT_PUBLIC_CHECK_MANAGER_ENDPOINT");
  if (!url) {
    throw new Error(
      `environment variable NEXT_PUBLIC_CHECK_MANAGER_ENDPOINT must be set`
    );
  }
  return url;
}

function GetTelemetryURL(): string {
  // MUST include /v1 (or some other version) at the end
  const url = env("NEXT_PUBLIC_TELEMETRY_ENDPOINT");
  if (!url) {
    throw new Error(
      `environment variable NEXT_PUBLIC_TELEMETRY_ENDPOINT must be set`
    );
  }
  return url;
}

type MakeRequestParams = {
  method: "GET" | "POST" | "DELETE";
  baseURL: string;
  path: string;
  pathParameters: (string | undefined)[];
  queryParameters: Record<string, string | string[] | undefined>;
  body?: Record<string, unknown> | undefined;
};

async function MakeRequest<T>({
  method,
  baseURL,
  path,
  pathParameters,
  queryParameters,
  body,
}: MakeRequestParams): Promise<AxiosResponse<T, unknown>> {
  if (method !== "POST" && body !== undefined)
    throw new Error(`${method} request can't have a body`);
  let pathParamsConcat = pathParameters
    .filter((param) => param)
    .map((param) => encodeURIComponent(param!))
    .join("/");
  if (!path.endsWith("/") && pathParamsConcat) {
    pathParamsConcat = "/" + pathParamsConcat;
  }
  return await axios.request<unknown, AxiosResponse<T, unknown>, unknown>({
    url: path + pathParamsConcat,
    method: method,
    baseURL: baseURL,
    params: queryParameters,
    data: body,
    headers: { "content-type": "application/vnd.api+json" },
    withCredentials: true,
    paramsSerializer: {
      // Omit brackets when serialize array into the URL.
      // Based on https://stackoverflow.com/a/76517213
      indexes: null,
    },
  });
}

export async function GetCheckTemplates(
  ids?: CheckTemplateId[]
): Promise<CheckTemplate[]> {
  const response = await MakeRequest<
    APIOKResponseList<CheckTemplateAttributes, null>
  >({
    method: "GET",
    baseURL: GetCheckManagerURL(),
    path: "/check_templates/",
    pathParameters: [],
    queryParameters: { ids: ids },
  });
  return response.data.data;
}

export async function GetCheckTemplate(
  id: CheckTemplateId
): Promise<CheckTemplate> {
  const response = await MakeRequest<APIOKResponse<CheckTemplateAttributes>>({
    method: "GET",
    baseURL: GetCheckManagerURL(),
    path: "/check_templates/",
    pathParameters: [id],
    queryParameters: {},
  });
  return response.data.data;
}

export async function GetChecks(ids?: CheckId[]): Promise<Check[]> {
  const response = await MakeRequest<
    APIOKResponseList<OutCheckAttributes, null>
  >({
    method: "GET",
    baseURL: GetCheckManagerURL(),
    path: "/checks/",
    pathParameters: [],
    queryParameters: { ids: ids },
  });
  return response.data.data;
}

export async function CreateCheck(inCheck: InCheck): Promise<Check> {
  const response = await MakeRequest<APIOKResponse<OutCheckAttributes>>({
    method: "POST",
    baseURL: GetCheckManagerURL(),
    path: "/checks/",
    pathParameters: [],
    queryParameters: {},
    body: inCheck,
  });
  return response.data.data;
}

export async function GetCheck(checkId: CheckId): Promise<Check> {
  const response = await MakeRequest<APIOKResponse<OutCheckAttributes>>({
    method: "GET",
    baseURL: GetCheckManagerURL(),
    path: "/checks/",
    pathParameters: [checkId],
    queryParameters: {},
  });
  return response.data.data;
}

// export async function UpdateCheck(oldCheck: Check, templateId?: CheckTemplateId, templateArgs?: object, schedule?: CronExpression): Promise<Check> {
//   if (templateId === oldCheck.metadata.template_id) {
//     templateId = undefined
//   }

//   if (templateArgs === oldCheck.metadata.template_args) {
//     templateArgs = undefined
//   }

//   if (schedule === oldCheck.schedule) {
//     schedule = undefined
//   }
//   const response = await axios.patch(GetCheckManagerURL() + `/checks/${oldCheck.id}`, {template_id: templateId, template_args: templateArgs, schedule: schedule, withCredentials: true, headers: {"content-type": "application/vnd.api+json"}})
//   return response.data
// }

export async function RemoveCheck(checkId: CheckId): Promise<void> {
  await MakeRequest({
    method: "DELETE",
    baseURL: GetCheckManagerURL(),
    path: "/checks/",
    pathParameters: [checkId],
    queryParameters: {},
  });
}

export async function RunCheck(checkId: CheckId): Promise<void> {
  await MakeRequest({
    method: "POST",
    baseURL: GetCheckManagerURL(),
    path: "/checks/",
    // Including "run" here is a slight hack, but need it to appear at the end of the path and this is one way achieve that
    pathParameters: [checkId, "run/"],
    queryParameters: {},
  });
}

export const SpanStatus = {
  UNSET: 0,
  OK: 1,
  ERROR: 2,
};

export type Span = {
  traceId: string;
  spanId: string;
  parentSpanId: string;
  startTimeUnixNano: number;
  endTimeUnixNano: number;
  status: {
    // UNSET = 0
    // OK = 1
    // ERROR = 2
    // According to https://opentelemetry-python.readthedocs.io/en/latest/api/trace.status.html
    code?: 0 | 1 | 2;
    message?: string;
  };
  attributes: {
    key: string;
    value:
      | {
          stringValue: string;
        }
      | {
          intValue: string;
        }
      | unknown;
  }[];
};

export type SpanResult = {
  resourceSpans: {
    resource: {
      attributes: object[];
    };
    scopeSpans: {
      scope: object;
      spans: Span[];
    }[];
  }[];
};

type SpansResponseNextPageToken = {
  next_page_token?: string;
};

type SpansResponseMeta = {
  page: SpansResponseNextPageToken;
};

export type SpansResponse = APIOKResponseList<SpanResult, SpansResponseMeta>;

export type GetSpansQueryParams = {
  traceId?: string;
  spanId?: string;
  fromTime?: Date;
  toTime?: Date;
  resourceAttributes?: TelemetryAttributes;
  scopeAttributes?: TelemetryAttributes;
  spanAttributes?: TelemetryAttributes;
};

// function AttributesDictToList(attributes?: TelemetryAttributes): string[] {
//   if (attributes === undefined) {
//     return [];
//   }
//   function AttributeToString(
//     key: string,
//     value: string | number | boolean
//   ): string {
//     if (typeof value == "string") {
//       value = `"${value}"`;
//     }
//     return `${key}=${value}`;
//   }
//   return Object.entries(attributes).map(([key, value]) =>
//     AttributeToString(key, value)
//   );
// }

function AttributesDictToList(attributes?: TelemetryAttributes): string[] {
  if (attributes === undefined) {
    return [];
  }
  function AttributeToString(
    key: string,
    values: (string | number | boolean)[] | null
  ): string[] {
    if (values === null) {
      return [key];
    }
    return values.map((value) => {
      if (typeof value == "string") {
        value = `"${value}"`;
      }
      return `${key}=${value}`;
    });
  }
  return Object.entries(attributes).flatMap(([key, values]) =>
    AttributeToString(key, values)
  );
}

export async function GetSpans({
  traceId,
  spanId,
  fromTime,
  toTime,
  resourceAttributes,
  scopeAttributes,
  spanAttributes,
  pageToken,
}: GetSpansQueryParams & { pageToken?: string }): Promise<SpansResponse> {
  if (traceId === undefined && spanId !== undefined) {
    throw new Error("spanId must only be set if traceId is also set");
  }
  const response = await MakeRequest<SpansResponse>({
    method: "GET",
    baseURL: GetTelemetryURL(),
    path: `/spans`,
    pathParameters: [traceId, spanId],
    queryParameters: {
      from_time: fromTime?.toISOString(),
      to_time: toTime?.toISOString(),
      resource_attributes: AttributesDictToList(resourceAttributes),
      scope_attributes: AttributesDictToList(scopeAttributes),
      span_attributes: AttributesDictToList(spanAttributes),
      page_token: pageToken,
    },
  });
  return response.data;
}

export async function GetAllSpans(
  getSpansQueryParams: GetSpansQueryParams
): Promise<SpanResult> {
  return ReduceSpans<SpanResult>(
    getSpansQueryParams,
    (accumulator: SpanResult, currentValue: SpanResult) => {
      accumulator.resourceSpans.push(...currentValue.resourceSpans);
      return accumulator;
    },
    { resourceSpans: [] }
  );
}

export async function ReduceSpans<T>(
  getSpansQueryParams: GetSpansQueryParams,
  callbackFn: (accumulator: T, currentValue: SpanResult) => T,
  initialValue: T
): Promise<T> {
  let pageToken: string | undefined = undefined;
  let accumulator: T = initialValue;
  do {
    const spansResponse = await GetSpans({
      pageToken: pageToken,
      ...getSpansQueryParams,
    });
    pageToken = spansResponse.meta.page.next_page_token;
    for (const spanResult of spansResponse.data) {
      accumulator = callbackFn(accumulator, spanResult.attributes);
    }
  } while (pageToken);
  return accumulator;
}
