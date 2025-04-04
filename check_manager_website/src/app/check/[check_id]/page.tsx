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
  Modal,
  ModalBody,
  ModalCloseButton,
  ModalContent,
  ModalFooter,
  ModalHeader,
  ModalOverlay,
  Select,
  Table,
  Tbody,
  Td,
  Text,
  Textarea,
  Th,
  Thead,
  Tr,
  useDisclosure,
} from "@chakra-ui/react";
import { IoReload as Reload } from "react-icons/io5";
import { Duration } from "date-fns";
import {
  FindCheckTemplate,
  GetRelLink,
  GetSpanFilterParams,
  GetTraceIdToSpans,
  IsSpanError,
  LOADING_STRING,
  SpanFilterParamsToDql,
  StringifyPretty,
} from "@/lib/helpers";
import { CheckError } from "@/components/CheckError";
import { TELEMETRY_DURATION } from "@/lib/config";
import { useRouter } from "next/navigation";
import DefaultLayout from "@/layouts/DefaultLayout";
import CustomLink from "@/components/CustomLink";
import ButtonWithCheckmark from "@/components/ButtonWithCheckmark";

type HealthCheckPageProps = {
  params: { check_id: string };
};

export default function HealthCheckPage({
  params: { check_id },
}: HealthCheckPageProps): JSX.Element {
  return (
    <DefaultLayout>
      <CustomLink href={GetRelLink({})}>Home</CustomLink>
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
  const spanFilterParams = GetSpanFilterParams(check, now);
  if (allSpans === null) {
    GetAllSpans(spanFilterParams).then(setAllSpans).catch(setError);
  }

  return (
    <CheckDiv
      check={check}
      telemetryDuration={TELEMETRY_DURATION}
      templates={checkTemplates}
      setNow={setNow}
      filterParamsDql={SpanFilterParamsToDql(spanFilterParams)}
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

export type CheckDivProps = {
  check: Check;
  telemetryDuration: Duration;
  templates: CheckTemplate[];
  setNow: (now: Date) => void;
  filterParamsDql: string;
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
  filterParamsDql,
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
        {/* Use isDisabled here instead of isReadonly, as the latter does nothing for the select, option, and button HTML tags,
            as discussed in this answer https://stackoverflow.com/a/7730719
        */}
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
  return (
    <>
      <Heading>{check_label}</Heading>
      <div className="flex flex-col gap-4">
        <div>
          <FormControl isReadOnly>
            <Grid gap={6} marginBottom={6}>
              <div>
                <FormLabel>Check id</FormLabel>
                <Input value={check.id} />
              </div>
              <div>
                <FormLabel>Outcome Filter</FormLabel>
                <Textarea
                  resize="none"
                  className="whitespace-pre !h-32"
                  value={StringifyPretty(check.attributes.outcome_filter)}
                />
              </div>
            </Grid>
          </FormControl>
          {checkDiv}
        </div>
        <div className="flex flex-row gap-6">
          <IconButton
            aria-label="Reload"
            onClick={() => {
              setNow(new Date());
              setAllSpans(null);
            }}
          >
            <Reload />
          </IconButton>
          <ButtonWithCheckmark
            onClick={() => navigator.clipboard.writeText(filterParamsDql)}
          >
            Copy filter parameters in DQL
          </ButtonWithCheckmark>
          <ButtonWithCheckmark
            onClick={() => RunCheck(check.id).catch(setError)}
          >
            Run Check
          </ButtonWithCheckmark>
          <RemoveCheckButton
            onClick={() => {
              RemoveCheck(check.id)
                .then(() => onCheckRemove(check.id))
                .catch(setError);
            }}
          />
        </div>
        <CheckRunsTable checkId={check.id} allSpans={allSpans} />
      </div>
    </>
  );
}

function RemoveCheckButton({ onClick }: { onClick: () => void }): JSX.Element {
  const { isOpen, onOpen, onClose } = useDisclosure();

  return (
    <>
      <Button onClick={onOpen}>Remove Check</Button>
      <Modal onClose={onClose} isOpen={isOpen} isCentered>
        <ModalOverlay />
        <ModalContent>
          <ModalHeader>Remove Check</ModalHeader>
          <ModalCloseButton />
          <ModalBody>Are you sure you want to remove the check?</ModalBody>
          <ModalFooter>
            <Button mr={3} onClick={onClick}>
              Remove Check
            </Button>
            <Button onClick={onClose}>Cancel</Button>
          </ModalFooter>
        </ModalContent>
      </Modal>
    </>
  );
}

type CheckRunsTableProps = {
  checkId: string;
  allSpans: SpanResult | null;
};

function CheckRunsTable({
  checkId,
  allSpans,
}: CheckRunsTableProps): JSX.Element {
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
          <Th>Health Check Run Id (same as Trace id)</Th>
          <Th>Error Details</Th>
        </Tr>
      </Thead>
      <Tbody>
        {Object.entries(traceIdToSpans).map(([traceId, traceSpans]) => (
          <CheckRunTableRow
            key={traceId}
            checkId={checkId}
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
  checkId,
  traceId,
  traceSpans,
}: {
  checkId: string;
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
      <Td>
        <CustomLink href={GetRelLink({ checkId: checkId, traceId: traceId })}>
          {traceId}
        </CustomLink>
      </Td>
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
