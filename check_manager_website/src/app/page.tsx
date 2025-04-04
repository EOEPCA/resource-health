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
  Button,
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
  ComputeSpansSummary,
  FindCheckTemplate,
  GetAverageDuration,
  LOADING_STRING,
  SpansSummary,
} from "@/lib/helpers";
import { CheckError } from "@/components/CheckError";
import { TELEMETRY_DURATION } from "@/lib/config";
import { IoCheckmarkCircle as Checkmark } from "react-icons/io5";
import DefaultLayout from "@/layouts/DefaultLayout";
import CustomLink from "@/components/CustomLink";

const log = (type: string) => console.log.bind(console, type);

export default function Home(): JSX.Element {
  return (
    <DefaultLayout>
      <HomeDetails />
    </DefaultLayout>
  );
  // return (
  //   <ThemeProvider theme={theme}>
  //     <CSSReset />
  //     <main className="flex min-h-screen flex-col items-start p-24">
  //       <HomeDetails />
  //     </main>
  //   </ThemeProvider>
  // )
}

function HomeDetails(): JSX.Element {
  const [error, setError] = useState<Error | null>(null);
  const [checkTemplates, setCheckTemplates] = useState<CheckTemplate[] | null>(
    null
  );
  const [checks, setChecks] = useState<Check[] | null>(null);
  if (error !== null) {
    return <CheckError {...error} />;
  }
  if (checkTemplates === null) {
    GetCheckTemplates().then(setCheckTemplates).catch(setError);
  }
  if (checks === null) {
    GetChecks().then(setChecks).catch(setError);
  }
  if (checkTemplates === null || checks === null) {
    return <Text>{LOADING_STRING}</Text>;
  }
  return (
    <ChecksDiv
      checks={checks}
      telemetryDuration={TELEMETRY_DURATION}
      templates={checkTemplates}
      onCreateCheck={(check) => setChecks([check, ...checks])}
      setError={setError}
    />
  );
}

type CheckDivCommonProps = {
  telemetryDuration: Duration;
  setError: (error: Error) => void;
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
            {SummaryRowDiv(commonProps)}
            {CreateCheckDiv({
              templates,
              onCreateCheck: onCreateCheck,
              ...commonProps,
            })}
            {checks.map((check) => (
              <CheckSummaryDiv key={check.id} check={check} {...commonProps} />
            ))}
          </Tbody>
        </Table>
      </TableContainer>
    </div>
  );
}

function SummaryRowDiv({
  telemetryDuration,
  setError,
}: {
  telemetryDuration: Duration;
  setError: (error: Error) => void;
}): JSX.Element {
  const [now, setNow] = useState(new Date());
  const [spansSummary, setSpansSummary] = useState<SpansSummary | null>(null);
  if (spansSummary === null) {
    ComputeSpansSummary({
      fromTime: subDuration(now, telemetryDuration),
      toTime: now,
    })
      .then(setSpansSummary)
      .catch(setError);
  }
  return (
    <Tr>
      <Td>From all checks (not only those in the table)</Td>
      <Td>
        <IconButton
          aria-label="Reload"
          onClick={() => {
            setNow(new Date());
            setSpansSummary(null);
          }}
        >
          <Reload />
        </IconButton>
      </Td>
      <Td>{spansSummary?.durationCount ?? LOADING_STRING}</Td>
      <Td>{spansSummary?.failedTraceIds.size ?? LOADING_STRING}</Td>
      <Td>
        {spansSummary !== null
          ? GetAverageDuration(spansSummary)
          : LOADING_STRING}
      </Td>
      <Td>{spansSummary?.totalTestCount ?? LOADING_STRING}</Td>
    </Tr>
  );
}

function CreateCheckDiv({
  templates,
  onCreateCheck,
  setError,
}: {
  templates: CheckTemplate[];
  onCreateCheck: (check: Check) => void;
  setError: (error: Error) => void;
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
            onSubmit={(data) => {
              setName("");
              setSchedule("");
              setDescription("");
              // A hacky way to force clearing of form data
              setKey(1 - key);
              setTemplateId(templates[0].id);
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
                .then(onCreateCheck)
                .catch(setError);
            }}
            onError={log("errors")}
          />
        </details>
      </Td>
    </Tr>
  );
}

function CheckSummaryDiv({
  check,
  telemetryDuration,
  setError,
}: { check: Check } & CheckDivCommonProps): JSX.Element {
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const [description, setDescription] = useState(
    check.attributes.metadata.description
  );
  const [now, setNow] = useState(new Date());
  const [spansSummary, setSpansSummary] = useState<SpansSummary | null>(null);
  if (spansSummary === null) {
    ComputeSpansSummary({
      fromTime: subDuration(now, telemetryDuration),
      toTime: now,
      resourceAttributes: check.attributes.outcome_filter.resource_attributes,
      scopeAttributes: check.attributes.outcome_filter.scope_attributes,
      spanAttributes: check.attributes.outcome_filter.span_attributes,
    })
      .then(setSpansSummary)
      .catch(setError);
  }
  const check_label =
    check.attributes.metadata.template_args === undefined
      ? check.id
      : check.attributes.metadata.name ?? check.id;
  const [checkRunSubmitted, setCheckRunSubmitted] = useState(false);
  return (
    <Tr>
      <Td>
        <CustomLink href={"/" + check.id}>{check_label}</CustomLink>
      </Td>
      <Td className="flex flex-row gap-4 items-center">
        <IconButton
          aria-label="Reload"
          onClick={() => {
            setNow(new Date());
            setSpansSummary(null);
          }}
        >
          <Reload />
        </IconButton>
        <div className="flex flex-row gap-1 items-center">
          <Button
            onClick={() =>
              RunCheck(check.id)
                .then(() => setCheckRunSubmitted(true))
                .catch(setError)
            }
          >
            Run Check
          </Button>
          {checkRunSubmitted && <Checkmark />}
        </div>
      </Td>
      <Td>{spansSummary?.durationCount ?? LOADING_STRING}</Td>
      <Td>{spansSummary?.failedTraceIds.size ?? LOADING_STRING}</Td>
      <Td>
        {spansSummary !== null
          ? GetAverageDuration(spansSummary)
          : LOADING_STRING}
      </Td>
      <Td>{spansSummary?.totalTestCount ?? LOADING_STRING}</Td>
    </Tr>
  );
}
