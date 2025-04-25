"use client";

import DefaultLayout from "@/layouts/DefaultLayout";
import { Text } from "@chakra-ui/react";
import { GetAllSpans, SpanResult } from "@/lib/backend-wrapper";
import { SetErrorPropsType, useError } from "@/components/CheckError";
import {
  CallBackend,
  GetRelLink,
  LOADING_STRING,
  SpanFilterParamsToDql,
  StringifyPretty,
  useFetchState,
} from "@/lib/helpers";
import CustomLink from "@/components/CustomLink";
import ButtonWithCheckmark from "@/components/ButtonWithCheckmark";
import { useEffect, useState } from "react";

type HealthCheckRunPageProps = {
  params: { check_id: string; trace_id: string };
};

export default function HealthCheckRunPage({
  params: { check_id, trace_id },
}: HealthCheckRunPageProps): JSX.Element {
  // It is defined here so that the error popup appears no matter what
  const [errorDiv, setErrorProps] = useError();
  return (
    <DefaultLayout>
      {errorDiv}
      <CustomLink href={GetRelLink({})}>Home</CustomLink>
      <CustomLink href={GetRelLink({ checkId: check_id })}>
        Health Check
      </CustomLink>
      <HealthCheckRunPageDetails
        traceId={trace_id}
        setErrorProps={setErrorProps}
      />
    </DefaultLayout>
  );
}

function HealthCheckRunPageDetails({
  traceId,
  setErrorProps,
}: {
  traceId: string;
  setErrorProps: SetErrorPropsType;
}): JSX.Element {
  const spanFilterParams = { traceId: traceId };
  const [allSpans] = useFetchState(
    () => GetAllSpans(spanFilterParams),
    setErrorProps,
    [traceId]
  );
  const filterParamsDql = SpanFilterParamsToDql(spanFilterParams);
  if (allSpans === null) {
    return <Text>{LOADING_STRING}</Text>;
  }
  return (
    <>
      <ButtonWithCheckmark
        onClick={() => navigator.clipboard.writeText(filterParamsDql)}
      >
        Copy filter parameters in DQL
      </ButtonWithCheckmark>
      <Text className="whitespace-pre">{StringifyPretty(allSpans)}</Text>;
    </>
  );
}
