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
  FindCheckTemplate,
  GetAverageDuration,
  GetRelLink,
  LOADING_STRING,
  SpansSummary,
  useFetchState,
} from "@/lib/helpers";
import {
  CheckErrorPopup,
  SetErrorPropsType,
  useError,
} from "@/components/CheckError";
import { TELEMETRY_DURATION } from "@/lib/config";
import DefaultLayout from "@/layouts/DefaultLayout";
import CustomLink from "@/components/CustomLink";
import ButtonWithCheckmark from "@/components/ButtonWithCheckmark";

const log = (type: string) => console.log.bind(console, type);

export default function Home(): JSX.Element {
  const { errorProps, setErrorProps, isErrorOpen, onErrorClose } = useError();
  return (
    <DefaultLayout>
      <CheckErrorPopup
        errorProps={errorProps}
        isOpen={isErrorOpen}
        onClose={onErrorClose}
      />
      <HomeDetails setErrorProps={setErrorProps} />
    </DefaultLayout>
  );
}

function HomeDetails({
  setErrorProps,
}: {
  setErrorProps: SetErrorPropsType;
}): JSX.Element {
  const [checkTemplates] = useFetchState(GetCheckTemplates, setErrorProps, []);
  const [checks, setChecks] = useFetchState(GetChecks, setErrorProps, []);
  if (checkTemplates === null || checks === null) {
    return <Text>{LOADING_STRING}</Text>;
  }
  return (
    <ChecksDiv
      checks={checks}
      telemetryDuration={TELEMETRY_DURATION}
      templates={checkTemplates}
      onCreateCheck={(check) => setChecks([check, ...checks])}
      setErrorProps={setErrorProps}
    />
  );
}

type CheckDivCommonProps = {
  telemetryDuration: Duration;
  setErrorProps: SetErrorPropsType;
};

function ChecksDiv({
  checks,
  templates,
  onCreateCheck,
  ...commonProps
}: {
  checks: Check[];
  templates: CheckTemplate[];
  onCreateCheck: (check: Check) => void;
} & CheckDivCommonProps): JSX.Element {
  // const [spansSummaries, setSpansSummaries] = useState<
  //   Record<string, SpansSummary | null>
  // >(
  //   checks.reduce((accum: Record<string, SpansSummary | null>, val: Check) => {
  //     accum[val.id] = null;
  //     return accum;
  //   }, {})
  // );
  return (
    <div>
      <Heading>Check List</Heading>
      <Text>
        Displaying data from the last{" "}
        {formatDuration(commonProps.telemetryDuration)}
      </Text>
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
              onCreateCheck={onCreateCheck}
              {...commonProps}
            />
            {checks.map((check) => (
              <CheckSummaryDiv
                key={check.id}
                check={check}
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
    </div>
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

function CreateCheckDiv({
  templates,
  onCreateCheck,
  setErrorProps,
}: {
  templates: CheckTemplate[];
  onCreateCheck: (check: Check) => void;
  setErrorProps: SetErrorPropsType;
}): JSX.Element {
  const [templateId, setTemplateId] = useState(templates[0].id);
  // Only used as a hacky way to force clearing of form data
  const [key, setKey] = useState(0);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [schedule, setSchedule] = useState("");
  const template = FindCheckTemplate(templates, templateId);
  const form_id = "create_check";
  return (
    <Tr>
      <Td>
        <details>
          <summary>Create new check</summary>
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
                () =>
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
                  }),
                (check: Check) => {
                  setName("");
                  setSchedule("");
                  setDescription("");
                  // A hacky way to force clearing of form data
                  setKey(1 - key);
                  setTemplateId(templates[0].id);
                  onCreateCheck(check);
                },
                setErrorProps
              )
            }
            onError={log("errors")}
          />
        </details>
      </Td>
    </Tr>
  );
}

function CheckSummaryDiv({
  check,
  setCheckSpansSummary,
  telemetryDuration,
  setErrorProps,
}: {
  check: Check;
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
  const [spansSummary, setSpansSummary] = useFetchState(
    () =>
      ComputeSpansSummary({
        fromTime: subDuration(now, telemetryDuration),
        toTime: now,
        resourceAttributes: check.attributes.outcome_filter.resource_attributes,
        scopeAttributes: check.attributes.outcome_filter.scope_attributes,
        spanAttributes: check.attributes.outcome_filter.span_attributes,
      }),
    setErrorProps,
    [now, telemetryDuration, check]
  );
  const check_label =
    check.attributes.metadata.template_args === undefined
      ? check.id
      : check.attributes.metadata.name ?? check.id;
  return (
    <Tr>
      <Td>
        <CustomLink href={GetRelLink({ checkId: check.id })}>
          {check_label}
        </CustomLink>
      </Td>
      <Td className="flex flex-row gap-4 items-center">
        <IconButton
          aria-label="Reload"
          onClick={() => {
            setNow(new Date());
            setSpansSummary(null);
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
              setErrorProps
            )
          }
        >
          Run Check
        </ButtonWithCheckmark>
      </Td>
      <Td>{spansSummary?.durationCount ?? LOADING_STRING}</Td>
      <Td>{spansSummary?.failedTraceIds.size ?? LOADING_STRING}</Td>
      <Td>
        {spansSummary !== null
          ? GetAverageDuration(
              spansSummary.totalDurationSecs,
              spansSummary.durationCount
            )
          : LOADING_STRING}
      </Td>
      <Td>{spansSummary?.totalTestCount ?? LOADING_STRING}</Td>
    </Tr>
  );
}
