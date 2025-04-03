"use client";

import { JSX, useState } from "react";
import Form from "@rjsf/chakra-ui";
import {
  RemoveCheck,
  Check,
  RunCheck,
  GetCheck,
  GetCheckTemplates,
  CheckTemplate,
  CheckId,
  SpanResult,
  GetAllSpans,
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
  Link,
  Select,
  Table,
  Tbody,
  Td,
  Text,
  Textarea,
  Th,
  Thead,
  Tr,
} from "@chakra-ui/react";
import { IoCheckmarkCircle as Checkmark } from "react-icons/io5";
import { IoReload as Reload } from "react-icons/io5";
import { Duration } from "date-fns";
import {
  FindCheckTemplate,
  GetSpanFilterParams,
  GetTraceIdToSpans,
  IsSpanError,
  LOADING_STRING,
} from "@/lib/helpers";
import { CheckError } from "@/components/CheckError";
import { TELEMETRY_DURATION } from "@/lib/config";
import { useRouter } from "next/navigation";
import DefaultLayout from "@/layouts/DefaultLayout";

type HealthCheckPageProps = {
  params: { check_id: string };
};

export default function HealthCheckPage({
  params: { check_id },
}: HealthCheckPageProps): JSX.Element {
  return (
    <DefaultLayout>
      <Link href="/">Home</Link>
      <HealthCheckDetails checkId={check_id} />
    </DefaultLayout>
  );
}

function HealthCheckDetails({ checkId }: { checkId: string }): JSX.Element {
  const router = useRouter();
  const [error, setError] = useState<Error | null>(null);
  const [checkTemplates, setCheckTemplates] = useState<CheckTemplate[] | null>(
    null
  );
  const [check, setCheck] = useState<Check | null>(null);
  const [now, setNow] = useState(new Date());
  const [allSpans, setAllSpans] = useState<SpanResult | null>(null);
  if (error !== null) {
    return <CheckError {...error} />;
  }
  if (checkTemplates === null) {
    GetCheckTemplates().then(setCheckTemplates).catch(setError);
  }
  if (check === null) {
    GetCheck(checkId).then(setCheck).catch(setError);
  }
  if (checkTemplates === null || check === null) {
    return <Text>{LOADING_STRING}</Text>;
  }
  if (allSpans === null) {
    GetAllSpans(GetSpanFilterParams(check, now))
      .then(setAllSpans)
      .catch(setError);
  }

  return (
    <CheckDiv
      check={check}
      telemetryDuration={TELEMETRY_DURATION}
      templates={checkTemplates}
      setNow={setNow}
      allSpans={allSpans}
      setAllSpans={setAllSpans}
      // eslint-disable-next-line @typescript-eslint/no-unused-vars
      onCheckUpdate={(_check) => {
        throw new Error("Update is not yet implemented");
      }}
      // eslint-disable-next-line @typescript-eslint/no-unused-vars
      onCheckRemove={(_checkId) => router.push("/")}
      setError={setError}
    />
  );
}

function StringifyPretty(json: object): string {
  return JSON.stringify(json, null, 2);
}

export type CheckDivProps = {
  check: Check;
  telemetryDuration: Duration;
  templates: CheckTemplate[];
  setNow: (now: Date) => void;
  allSpans: SpanResult | null;
  setAllSpans: (allSpans: SpanResult | null) => void;
  onCheckUpdate: (check: Check) => void;
  onCheckRemove: (checkId: CheckId) => void;
  setError: (error: Error) => void;
};

function CheckDiv({
  check,
  templates,
  setNow,
  allSpans,
  setAllSpans,
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  onCheckUpdate,
  onCheckRemove,
  setError,
}: CheckDivProps): JSX.Element {
  const [templateId, setTemplateId] = useState(
    check.attributes.metadata.template_id
  );
  const [name, setName] = useState(check.attributes.metadata.name);
  const [description, setDescription] = useState(
    check.attributes.metadata.description
  );
  const [schedule, setSchedule] = useState(check.attributes.schedule);
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const [isDisabled, setIsDisabled] = useState(true);

  const check_label =
    check.attributes.metadata.template_args === undefined
      ? check.id
      : check.attributes.metadata.name ?? check.id;
  let checkDiv;
  if (templateId) {
    const template = FindCheckTemplate(templates, templateId);
    const form_id = "existing_check_" + check.id;
    checkDiv = (
      <>
        <FormControl isDisabled={isDisabled}>
          <Grid gap={6} marginBottom={6}>
            <GridItem>
              <FormLabel>Check Template Id</FormLabel>
              <Select
                form={form_id}
                value={template.id}
                onChange={(e) => setTemplateId(e.target.value)}
              >
                {templates.map((template) => (
                  <option key={template.id} value={template.id}>
                    {template.id}
                  </option>
                ))}
              </Select>
            </GridItem>
            <GridItem>
              <FormControl isRequired isDisabled={isDisabled}>
                <FormLabel>Name</FormLabel>
                <Input
                  form={form_id}
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                />
              </FormControl>
            </GridItem>
            <GridItem>
              <FormControl isRequired isDisabled={isDisabled}>
                <FormLabel>Description</FormLabel>
                <Input
                  form={form_id}
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                />
              </FormControl>
            </GridItem>
            <GridItem>
              <FormControl isRequired isDisabled={isDisabled}>
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
            idPrefix={form_id + "_"}
            schema={template.attributes.arguments}
            formData={check.attributes.metadata.template_args}
            uiSchema={{
              "ui:readonly": isDisabled,
              "ui:options": {
                submitButtonOptions: {
                  norender: true,
                  props: {
                    disabled: isDisabled,
                  },
                },
              },
            }}
            validator={validator}
            // onSubmit={(data) => {setIsDisabled(!isDisabled); UpdateCheck(check, templateId, data.formData, schedule).then((updatedCheck) => { onCheckUpdate(updatedCheck)}).catch(setError)}}
          />
        </FormControl>
        {/* <Button
        type="button"
        onClick={() => {
          if (!isDisabled) {
            setTemplateId(check.metadata.template_id!)
            setSchedule(check.schedule)
          }
          setIsDisabled(!isDisabled)
        }}
      >
        {isDisabled ? "Enable Editing" : "Disable Editing (and delete unsaved changes)"}
      </Button> */}
        <Button
          type="button"
          onClick={() => {
            RemoveCheck(check.id)
              .then(() => onCheckRemove(check.id))
              .catch(setError);
          }}
        >
          Remove Check
        </Button>
      </>
    );
  } else {
    const template_args = check.attributes.metadata.template_args!;
    checkDiv = (
      <>
        <FormControl isDisabled={isDisabled}>
          <Grid gap={6} marginBottom={6}>
            <GridItem>
              <FormLabel>Name</FormLabel>
              <Input value={name} onChange={(e) => setName(e.target.value)} />
            </GridItem>
            <GridItem>
              <FormLabel>Description</FormLabel>
              <Input
                value={description}
                onChange={(e) => setDescription(e.target.value)}
              />
            </GridItem>
            <GridItem>
              <FormLabel>Schedule</FormLabel>
              <Input
                value={schedule}
                onChange={(e) => setSchedule(e.target.value)}
              />
            </GridItem>
            {Object.entries(template_args).map(([key, value]) => (
              <GridItem key={key}>
                <FormLabel>{key}</FormLabel>
                {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
                <Textarea value={value as any} />
              </GridItem>
            ))}
          </Grid>
        </FormControl>
      </>
    );
  }

  const [checkRunSubmitted, setCheckRunSubmitted] = useState(false);
  return (
    <>
      <Heading>{check_label}</Heading>
      <div className="flex flex-col gap-4">
        <div>
          <Grid gap={6} marginBottom={6}>
            <div>
              <FormLabel>Check id</FormLabel>
              <Text>{check.id}</Text>
            </div>
            <div>
              <FormLabel>Outcome Filter</FormLabel>
              <Text className="whitespace-pre">
                {StringifyPretty(check.attributes.outcome_filter)}
              </Text>
            </div>
          </Grid>
          {checkDiv}
        </div>
        <IconButton
          aria-label="Reload"
          onClick={() => {
            setNow(new Date());
            setAllSpans(null);
          }}
        >
          <Reload />
        </IconButton>
        <div className="flex flex-row gap-1">
          {" "}
          {/* items-center */}
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
        <CheckRunsTable allSpans={allSpans} />
      </div>
    </>
  );
}

type CheckRunsTableProps = {
  allSpans: SpanResult | null;
};

function CheckRunsTable({ allSpans }: CheckRunsTableProps): JSX.Element {
  if (allSpans === null) {
    return <Text>{LOADING_STRING}</Text>;
  }
  const traceIdToSpans = GetTraceIdToSpans(allSpans);
  return (
    // <TableContainer>
    <Table variant="simple">
      <Thead>
        <Tr>
          <Th>Check Result</Th>
          <Th>Trace Id</Th>
          <Th>Error Details</Th>
        </Tr>
      </Thead>
      <Tbody>
        {Object.entries(traceIdToSpans).map(([traceId, traceSpans]) => (
          <CheckRunTableRow
            key={traceId}
            traceId={traceId}
            traceSpans={traceSpans}
          />
        ))}
      </Tbody>
    </Table>
    // </TableContainer>
  );
}

function CheckRunTableRow({
  traceId,
  traceSpans,
}: {
  traceId: string;
  traceSpans: SpanResult;
}): JSX.Element {
  let checkPass = true;
  const errorMessages: string[] = [];
  for (const resourceSpans of traceSpans.resourceSpans) {
    for (const scopeSpans of resourceSpans.scopeSpans) {
      for (const span of scopeSpans.spans) {
        if (IsSpanError(span)) {
          checkPass = false;
          if (span.status.message) {
            errorMessages.push(span.status.message);
          }
        }
      }
    }
  }
  return (
    <Tr>
      <Td className={checkPass ? "bg-green-300" : "bg-red-300"}>
        <Text>{checkPass ? "PASS" : "FAIL"}</Text>
      </Td>
      <Td>{traceId}</Td>
      <Td>
        <div className="flex flex-col gap-6">
          {errorMessages.map((message) => (
            <div key={message} className="whitespace-pre-line">
              {message}
            </div>
          ))}
        </div>
      </Td>
    </Tr>
  );
}
