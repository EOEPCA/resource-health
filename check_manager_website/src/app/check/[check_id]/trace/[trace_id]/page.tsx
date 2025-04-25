"use client";

import DefaultLayout from "@/layouts/DefaultLayout";
import { Text } from "@chakra-ui/react";
import { GetAllSpans } from "@/lib/backend-wrapper";
import { useError } from "@/components/CheckError";
import {
  GetRelLink,
  LOADING_STRING,
  SpanFilterParamsToDql,
  StringifyPretty,
  useFetchState,
} from "@/lib/helpers";
import CustomLink from "@/components/CustomLink";
import ButtonWithCheckmark from "@/components/ButtonWithCheckmark";

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
  const [errorDiv, setErrorProps] = useError();
  const spanFilterParams = { traceId: traceId };
  const [allSpans] = useFetchState(
    () => GetAllSpans(spanFilterParams),
    setErrorProps
  );
  const filterParamsDql = SpanFilterParamsToDql(spanFilterParams);
  if (allSpans === null) {
    return <Text>{LOADING_STRING}</Text>;
  }
  return (
    <>
      {errorDiv}
      <ButtonWithCheckmark
        onClick={() => navigator.clipboard.writeText(filterParamsDql)}
      >
        Copy filter parameters in DQL
      </ButtonWithCheckmark>
      <Text className="whitespace-pre">{StringifyPretty(allSpans)}</Text>;
    </>
  );
}
