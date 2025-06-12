"use client";

import { JSX, useState } from "react";
import Form from "@rjsf/chakra-ui";
import {
  GetChecks,
  GetCheckTemplates,
  CreateCheck,
  CheckTemplate,
  Check,
  RunCheck,
} from "@/lib/backend-wrapper";
import validator from "@rjsf/validator-ajv8";
import {
  FormControl,
  FormLabel,
  Grid,
  GridItem,
  Heading,
  IconButton,
  Input,
  Select,
  Skeleton,
  Table,
  TableContainer,
  Tbody,
  Td,
  Text,
  Th,
  Thead,
  Tr,
} from "@chakra-ui/react";
import { IoReload as Reload } from "react-icons/io5";
import { Duration, formatDuration, sub as subDuration } from "date-fns";
import {
  CallBackend,
  ComputeSpansSummary,
  durationStringToDuration,
  EmptySpansSummary,
  FetchState,
  FetchToIncremental,
  FindCheckTemplate,
  GetAverageDuration,
  GetRelLink,
  SpansSummary,
  useFetchState,
} from "@/lib/helpers";
import {
  CheckErrorPopup,
  SetErrorsPropsType,
  useError,
} from "@/components/CheckError";
import DefaultLayout from "@/layouts/DefaultLayout";
import CustomLink from "@/components/CustomLink";
import ButtonWithCheckmark from "@/components/ButtonWithCheckmark";
import { DEFAULT_TELEMETRY_DURATION } from "@/lib/config";
import { TelemetryDurationTextAndDropdown } from "@/components/TelemetryDurationDropdown";
import { LoadingDiv } from "@/components/LoadingDiv";

const log = (type: string) => console.log.bind(console, type);

export default function Home(): JSX.Element {
  const { errorsProps, setErrorsProps, isErrorOpen } = useError();
  return (
    <DefaultLayout>
      <CheckErrorPopup
        errorsProps={errorsProps}
        setErrorsProps={setErrorsProps}
        isOpen={isErrorOpen}
      />
      <HomeDetails setErrorsProps={setErrorsProps} />
    </DefaultLayout>
  );
}

function HomeDetails({
  setErrorsProps,
}: {
  setErrorsProps: SetErrorsPropsType;
}): JSX.Element {
  const [checkTemplates, , templatesFetchState] = useFetchState({
    initialValue: [],
    fetch: FetchToIncremental(GetCheckTemplates),
    setErrorsProps: setErrorsProps,
    deps: [],
  });
  const [checks, setChecks, checksFetchState] = useFetchState({
    initialValue: [],
    fetch: FetchToIncremental(GetChecks),
    setErrorsProps: setErrorsProps,
    deps: [],
  });
  // if (templatesFetchState === "Loading" || checksFetchState === "Loading") {
  //   return <Spinner />;
  // }

  return (
    <ChecksDiv
      checks={checks}
      templates={checkTemplates}
      fetchState={
        templatesFetchState === "Loading" || checksFetchState === "Loading"
          ? "Loading"
          : "Completed"
      }
      onCreateCheck={(check) => setChecks([check, ...checks])}
      setErrorsProps={setErrorsProps}
    />
  );
}

type CheckDivCommonProps = {
  setErrorsProps: SetErrorsPropsType;
};

function ChecksDiv({
  checks,
  templates,
  fetchState,
  onCreateCheck,
  ...commonProps
}: {
  checks: Check[];
  templates: CheckTemplate[];
  fetchState: FetchState;
  onCreateCheck: (check: Check) => void;
} & CheckDivCommonProps): JSX.Element {
  // const useTelemetryDuration = useTelemetryDuration();
  const [durationString, setDurationString] = useState<string>(
    formatDuration(DEFAULT_TELEMETRY_DURATION)
  );
  const telemetryDuration = durationStringToDuration.get(durationString)!;
  return (
    <>
      <Heading>Check List</Heading>
      <TelemetryDurationTextAndDropdown
        durationString={durationString}
        setDurationString={setDurationString}
      />
      <Skeleton isLoaded={fetchState === "Completed"}>
        <TableContainer>
          <Table variant="simple">
            <Thead>
              <Tr>
                <Th>Check info</Th>
                <Th>Actions</Th>
                <Th>Run count</Th>
                <Th>Problematic run count</Th>
                <Th>Average duration</Th>
                <Th>Total test count</Th>
              </Tr>
            </Thead>

            <Tbody>
              {/* <SummaryRowDiv spansSummaries={spansSummaries} /> */}
              <CreateCheckDiv
                templates={templates}
                fetchState={fetchState}
                onCreateCheck={onCreateCheck}
                {...commonProps}
              />

              {checks.map((check) => (
                <CheckSummaryDiv
                  key={check.id}
                  check={check}
                  telemetryDuration={telemetryDuration}
                  // eslint-disable-next-line @typescript-eslint/no-unused-vars
                  setCheckSpansSummary={(checkId, spansSummary) => {
                    // const newSpansSummaries = {
                    //   ...spansSummaries,
                    //   // This is at the end to override the existing value
                    //   [checkId]: spansSummary,
                    // };
                    // setSpansSummaries(newSpansSummaries);
                  }}
                  {...commonProps}
                />
              ))}
            </Tbody>
          </Table>
        </TableContainer>
      </Skeleton>
    </>
  );
}

// function SummaryRowDiv({
//   spansSummaries,
// }: {
//   spansSummaries: Record<string, SpansSummary | null>;
// }): JSX.Element {
//   let finishedLoading = true;
//   let totalDurationSecs = 0;
//   let durationCount = 0;
//   let failedCheckCount = 0;
//   let totalTestCount = 0;
//   for (const [, spansSummary] of Object.entries(spansSummaries)) {
//     if (spansSummary === null) {
//       finishedLoading = false;
//     } else {
//       totalDurationSecs += spansSummary.totalDurationSecs;
//       durationCount += spansSummary.durationCount;
//       failedCheckCount += spansSummary.failedTraceIds.size;
//       totalTestCount += spansSummary.totalTestCount;
//     }
//   }

//   return (
//     <Tr>
//       <Td>Summary</Td>
//       <Td />
//       <Td>{finishedLoading ? durationCount : LOADING_STRING}</Td>
//       <Td>{finishedLoading ? failedCheckCount : LOADING_STRING}</Td>
//       <Td>
//         {finishedLoading
//           ? GetAverageDuration(totalDurationSecs, durationCount)
//           : LOADING_STRING}
//       </Td>
//       <Td>{finishedLoading ? totalTestCount : LOADING_STRING}</Td>
//     </Tr>
//   );
// }

type CreateCheckDivProps = {
  templates: CheckTemplate[];

  onCreateCheck: (check: Check) => void;
  setErrorsProps: SetErrorsPropsType;
};

function CreateCheckDiv({
  fetchState,
  ...rest
}: CreateCheckDivProps & { fetchState: FetchState }): JSX.Element {
  function CreateCheckDivInternal({
    templates,
    onCreateCheck,
    setErrorsProps,
  }: CreateCheckDivProps): JSX.Element {
    const [templateId, setTemplateId] = useState(templates[0].id);
    // Only used as a hacky way to force clearing of form data
    const [key, setKey] = useState(0);
    const [name, setName] = useState("");
    const [description, setDescription] = useState("");
    const [schedule, setSchedule] = useState("");
    const template = FindCheckTemplate(templates, templateId);
    const form_id = "create_check";

    return (
      <>
        <Grid gap={6} marginBottom={6}>
          <GridItem>
            <FormLabel>Check Template</FormLabel>
            <Select
              form={form_id}
              value={template.id}
              onChange={(e) => setTemplateId(e.target.value)}
            >
              {templates.map((template) => (
                <option key={template.id} value={template.id}>
                  {template.attributes.metadata.label || template.id}
                </option>
              ))}
            </Select>
            <Text>{template.attributes.metadata.description}</Text>
            <FormLabel>Template ID</FormLabel>
            <Text>{template.id}</Text>
          </GridItem>
          <GridItem>
            <FormControl isRequired>
              <FormLabel>Name</FormLabel>
              <Input
                form={form_id}
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </FormControl>
            <FormControl isRequired>
              <FormLabel>Description</FormLabel>
              <Input
                form={form_id}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
              />
            </FormControl>
            <FormControl isRequired>
              <FormLabel>Schedule</FormLabel>
              <Input
                form={form_id}
                value={schedule}
                onChange={(e) => setSchedule(e.target.value)}
              />
            </FormControl>
          </GridItem>
        </Grid>
        <Form
          id={form_id}
          idPrefix={form_id + "_"}
          key={key}
          schema={template.attributes.arguments}
          validator={validator}
          onChange={log("changed")}
          onSubmit={(data) =>
            CallBackend(
              FetchToIncremental(() =>
                CreateCheck({
                  data: {
                    type: "check",
                    attributes: {
                      metadata: {
                        name: name,
                        description: description,
                        template_id: templateId,
                        template_args: data.formData,
                      },
                      schedule: schedule,
                    },
                  },
                })
              ),
              (check: Check) => {
                setName("");
                setSchedule("");
                setDescription("");
                // A hacky way to force clearing of form data
                setKey(1 - key);
                setTemplateId(templates[0].id);
                onCreateCheck(check);
              },
              setErrorsProps
            )
          }
          onError={log("errors")}
        />
      </>
    );
  }

  return (
    <Tr>
      <Td>
        <details>
          <summary>Create new check</summary>
          {fetchState === "Completed" && <CreateCheckDivInternal {...rest} />}
        </details>
      </Td>
    </Tr>
  );
}

function CheckSummaryDiv({
  check,
  telemetryDuration,
  setCheckSpansSummary,
  setErrorsProps,
}: {
  check: Check;
  telemetryDuration: Duration;
  setCheckSpansSummary: (
    checkId: string,
    spansSummary: SpansSummary | null
  ) => void;
} & CheckDivCommonProps): JSX.Element {
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const [description, setDescription] = useState(
    check.attributes.metadata.description
  );
  const [now, setNow] = useState(new Date());
  const [spansSummary, , fetchState] = useFetchState<SpansSummary>({
    initialValue: EmptySpansSummary,
    fetch: (setResult) =>
      ComputeSpansSummary({
        getSpansQueryParams: {
          fromTime: subDuration(now, telemetryDuration),
          toTime: now,
          resourceAttributes:
            check.attributes.outcome_filter.resource_attributes,
          scopeAttributes: check.attributes.outcome_filter.scope_attributes,
          spanAttributes: check.attributes.outcome_filter.span_attributes,
        },
        setResult: setResult,
      }),
    setErrorsProps: setErrorsProps,
    deps: [now, telemetryDuration, check],
  });
  const checkLabel =
    check.attributes.metadata.template_args === undefined
      ? check.id
      : check.attributes.metadata.name ?? check.id;
  return (
    <Tr>
      <Td>
        <CustomLink href={GetRelLink({ checkId: check.id })}>
          {checkLabel}
        </CustomLink>
      </Td>
      <Td className="flex flex-row gap-4 items-center">
        <IconButton
          aria-label="Reload"
          onClick={() => {
            setNow(new Date());
            setCheckSpansSummary(check.id, null);
          }}
        >
          <Reload />
        </IconButton>
        <ButtonWithCheckmark
          onClick={() =>
            CallBackend(
              () => RunCheck(check.id),
              () => {},
              setErrorsProps
            )
          }
        >
          Run Check
        </ButtonWithCheckmark>
      </Td>
      <Td>
        <LoadingDiv fetchState={fetchState}>
          <Text>{spansSummary.durationCount}</Text>
        </LoadingDiv>
      </Td>
      <Td>
        <LoadingDiv fetchState={fetchState}>
          <Text>{spansSummary.failedTraceIdsCount}</Text>
        </LoadingDiv>
      </Td>
      <Td>
        <LoadingDiv fetchState={fetchState}>
          <Text>
            {GetAverageDuration(
              spansSummary.totalDurationSecs,
              spansSummary.durationCount
            )}
          </Text>
        </LoadingDiv>
      </Td>
      <Td>
        <LoadingDiv fetchState={fetchState}>
          <Text>{spansSummary.totalTestCount}</Text>
        </LoadingDiv>
      </Td>
    </Tr>
  );
}
