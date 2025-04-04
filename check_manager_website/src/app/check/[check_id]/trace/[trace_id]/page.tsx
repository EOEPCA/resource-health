"use client";

import DefaultLayout from "@/layouts/DefaultLayout";
import { Text } from "@chakra-ui/react";
import { useState } from "react";
import { GetAllSpans, SpanResult } from "@/lib/backend-wrapper";
import { CheckError } from "@/components/CheckError";
import { GetRelLink, LOADING_STRING, StringifyPretty } from "@/lib/helpers";
import CustomLink from "@/components/CustomLink";

type HealthCheckRunPageProps = {
  params: { check_id: string; trace_id: string };
};

export default function HealthCheckRunPage({
  params: { check_id, trace_id },
}: HealthCheckRunPageProps): JSX.Element {
  return (
    <DefaultLayout>
      <CustomLink href={GetRelLink({})}>Home</CustomLink>
      <CustomLink href={GetRelLink({ checkId: check_id })}>
        Health Check
      </CustomLink>
      <HealthCheckRunPageDetails traceId={trace_id} />
    </DefaultLayout>
  );
}

function HealthCheckRunPageDetails({
  traceId,
}: {
  traceId: string;
}): JSX.Element {
  const [error, setError] = useState<Error | null>(null);
  const [allSpans, setAllSpans] = useState<SpanResult | null>(null);
  if (error !== null) {
    return <CheckError {...error} />;
  }
  if (allSpans === null) {
    GetAllSpans({ traceId: traceId }).then(setAllSpans).catch(setError);
  }
  if (allSpans === null) {
    return <Text>{LOADING_STRING}</Text>;
  }
  return <Text className="whitespace-pre">{StringifyPretty(allSpans)}</Text>;
}
