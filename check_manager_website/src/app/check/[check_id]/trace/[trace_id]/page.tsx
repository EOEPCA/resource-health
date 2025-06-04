"use client";

import JsonView from "@uiw/react-json-view";
import DefaultLayout from "@/layouts/DefaultLayout";
import { Text } from "@chakra-ui/react";
import { GetAllSpans, SpanStatus } from "@/lib/backend-wrapper";
import {
  CheckErrorPopup,
  SetErrorsPropsType,
  useError,
} from "@/components/CheckError";
import {
  GetRelLink,
  IsStatusError,
  LOADING_STRING,
  SpanFilterParamsToDql,
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
  // It is defined here so that the error popup appears no matter what
  const { errorsProps, setErrorsProps, isErrorOpen } = useError();
  return (
    <DefaultLayout>
      <CheckErrorPopup
        errorsProps={errorsProps}
        setErrorsProps={setErrorsProps}
        isOpen={isErrorOpen}
      />
      <CustomLink href={GetRelLink({})}>Home</CustomLink>
      <CustomLink href={GetRelLink({ checkId: check_id })}>
        Health Check
      </CustomLink>
      <HealthCheckRunPageDetails
        traceId={trace_id}
        setErrorsProps={setErrorsProps}
      />
    </DefaultLayout>
  );
}

function HealthCheckRunPageDetails({
  traceId,
  setErrorsProps,
}: {
  traceId: string;
  setErrorsProps: SetErrorsPropsType;
}): JSX.Element {
  const spanFilterParams = { traceId: traceId };
  const [allSpans] = useFetchState(
    () => GetAllSpans(spanFilterParams),
    setErrorsProps,
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
      <JsonView
        value={allSpans}
        displayObjectSize={false}
        shortenTextAfterLength={0}
        displayDataTypes={false}
        // Could implement shouldExpandNodeInitially to expand only the error parts, for example
        // shouldExpandNodeInitially?: (
        //   isExpanded: boolean,
        //   props: { value?: T; keys: (number | string)[]; level: number },
        // ) => boolean;
        // shouldExpandNodeInitially={(isExpanded, { value, keys, level }) => {
        //   if (
        //     keys.length == PATH_TO_SPANS.length + 1 &&
        //     typeof keys.at(-1) == "number" &&
        //     keys.slice(0, -1) == PATH_TO_SPANS
        //   ) {
        //     return false;
        //   }
        // }}
      >
        {/* Do not display index. Based on https://github.com/uiwjs/react-json-view/tree/b1c5b0d53dfd1bc1107e5ec67387fcf9ad23b586?tab=readme-ov-file#do-not-display-array-index */}
        <JsonView.Colon
          render={(props, { parentValue }) => {
            if (Array.isArray(parentValue) && props.children == ":") {
              return <span />;
            }
            return <span {...props} />;
          }}
        />
        <JsonView.KeyName
          render={(props, { parentValue }) => {
            if (Array.isArray(parentValue) && Number.isFinite(props.children)) {
              return <span />;
            }
            // @ts-expect-error Some part of the props is still needed to display the key
            return <span {...props} />;
          }}
        />
        <JsonView.Row
          as="div"
          render={(props, { parentValue }) => {
            // This check might have false positives, but that's OK for now
            if (
              parentValue !== undefined &&
              "code" in parentValue &&
              IsStatusError(parentValue as SpanStatus)
            ) {
              const prevClassName = props.className;
              delete props.className;
              return (
                <div className={"bg-red-100 " + prevClassName} {...props} />
              );
            }
            return <div {...props} />;
          }}
        />
      </JsonView>
    </>
  );
}
