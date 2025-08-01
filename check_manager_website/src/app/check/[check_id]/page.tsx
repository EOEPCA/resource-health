"use client";

import { JSX, useEffect, useState } from "react";
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
  GetEmptySpanResult,
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
  Skeleton,
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
import { formatDuration } from "date-fns";
import {
  CallBackendIncremental,
  durationStringToDuration,
  FetchState,
  FindCheckTemplate,
  GetAllSpans,
  GetRelLink,
  GetSpanFilterParams,
  GetTraceIdToSpans,
  IsSpanError,
  SetResultType,
  SpanFilterParamsToDql,
  StringifyPretty,
  CallBackend,
  useFetchState,
} from "@/lib/helpers";
import {
  CheckErrorPopup,
  SetErrorsPropsType,
  useError,
} from "@/components/CheckError";
import { useRouter } from "next/navigation";
import DefaultLayout from "@/layouts/DefaultLayout";
import CustomLink from "@/components/CustomLink";
import ButtonWithCheckmark from "@/components/ButtonWithCheckmark";
import { DEFAULT_TELEMETRY_DURATION } from "@/lib/config";
import { TelemetryDurationTextAndDropdown } from "@/components/TelemetryDurationDropdown";
import { LoadingDiv } from "@/components/LoadingDiv";

type HealthCheckPageProps = {
  params: { check_id: string };
};

export default function HealthCheckPage({
  params: { check_id },
}: HealthCheckPageProps): JSX.Element {
  const { errorsProps, setErrorsProps, isErrorOpen } = useError();
  return (
    <DefaultLayout>
      <CheckErrorPopup
        errorsProps={errorsProps}
        setErrorsProps={setErrorsProps}
        isOpen={isErrorOpen}
      />
      <CustomLink href={GetRelLink({})}>Home</CustomLink>
      <HealthCheckDetails checkId={check_id} setErrorsProps={setErrorsProps} />
    </DefaultLayout>
  );
}

function HealthCheckDetails({
  checkId,
  setErrorsProps,
}: {
  checkId: string;
  setErrorsProps: SetErrorsPropsType;
}): JSX.Element {
  const router = useRouter();
  const [checkTemplates, , templatesFetchState] = useFetchState<
    CheckTemplate[]
  >({
    initialValue: [],
    fetch: GetCheckTemplates,
    setErrorsProps: setErrorsProps,
    deps: [],
  });
  const [check] = useFetchState<Check | null>({
    initialValue: null,
    fetch: () => GetCheck(checkId),
    setErrorsProps: setErrorsProps,
    deps: [checkId],
  });
  const [now, setNow] = useState(new Date());
  const [allSpans, setAllSpans] = useState<SpanResult>(GetEmptySpanResult());
  const [spansFetchState, setSpansFetchState] = useState<FetchState>("Loading");
  const [durationString, setDurationString] = useState<string>(
    formatDuration(DEFAULT_TELEMETRY_DURATION)
  );
  const telemetryDuration = durationStringToDuration.get(durationString)!;
  useEffect(() => {
    if (check !== null) {
      CallBackendIncremental<SpanResult>(
        (setResult) =>
          GetAllSpans({
            getSpansQueryParams: GetSpanFilterParams(
              check,
              telemetryDuration,
              now
            ),
            setResult: setResult,
          }),
        (spans, fetchState) => {
          setAllSpans(spans);
          setSpansFetchState(fetchState);
        },
        setErrorsProps
      );
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [check, now, telemetryDuration]);
  if (templatesFetchState === "Loading" || check === null) {
    return (
      <div className="flex flex-col gap-4">
        <Skeleton height="md" width="md" />
        <Skeleton height="md" />
      </div>
    );
  }

  return (
    <CheckDiv
      check={check}
      durationString={durationString}
      setDurationString={setDurationString}
      templates={checkTemplates}
      setNow={setNow}
      filterParamsDql={SpanFilterParamsToDql(
        GetSpanFilterParams(check, telemetryDuration, now)
      )}
      allSpans={allSpans}
      setAllSpans={(spans, fetchState) => {
        setAllSpans(spans);
        setSpansFetchState(fetchState);
      }}
      spansFetchState={spansFetchState}
      // eslint-disable-next-line @typescript-eslint/no-unused-vars
      onCheckUpdate={(_check) => {
        throw new Error("Update is not yet implemented");
      }}
      // eslint-disable-next-line @typescript-eslint/no-unused-vars
      onCheckRemove={(_checkId) => router.push("/")}
      setErrorsProps={setErrorsProps}
    />
  );
}

export type CheckDivProps = {
  check: Check;
  durationString: string;
  setDurationString: (duration: string) => void;
  templates: CheckTemplate[];
  setNow: (now: Date) => void;
  filterParamsDql: string;
  allSpans: SpanResult;
  setAllSpans: SetResultType<SpanResult>;
  spansFetchState: FetchState;
  onCheckUpdate: (check: Check) => void;
  onCheckRemove: (checkId: CheckId) => void;
  setErrorsProps: SetErrorsPropsType;
};

function CheckTemplateDiv({
  check,
  templates,
}: {
  check: Check;
  templates: CheckTemplate[];
}): JSX.Element {
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

  if (templateId) {
    const template = FindCheckTemplate(templates, templateId);
    const form_id = "existing_check_" + check.id;
    return (
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
    return (
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
}

function CheckDiv({
  check,
  durationString,
  setDurationString,
  templates,
  setNow,
  filterParamsDql,
  allSpans,
  setAllSpans,
  spansFetchState,
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  onCheckUpdate,
  onCheckRemove,
  setErrorsProps,
}: CheckDivProps): JSX.Element {
  const check_label =
    check.attributes.metadata.template_args === undefined
      ? check.id
      : check.attributes.metadata.name ?? check.id;
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
          <CheckTemplateDiv check={check} templates={templates} />
        </div>
        <div className="flex flex-row gap-6">
          <IconButton
            aria-label="Reload"
            onClick={() => {
              setNow(new Date());
              setAllSpans(GetEmptySpanResult(), "Loading");
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
          <RemoveCheckButton
            onClick={() =>
              CallBackend(
                () => RemoveCheck(check.id),
                () => onCheckRemove(check.id),
                setErrorsProps
              )
            }
          />
        </div>
        <TelemetryDurationTextAndDropdown
          durationString={durationString}
          setDurationString={setDurationString}
        />
        <CheckRunsTable
          checkId={check.id}
          allSpans={allSpans}
          spansFetchState={spansFetchState}
        />
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
  allSpans: SpanResult;
  spansFetchState: FetchState;
};

function CheckRunsTable({
  checkId,
  allSpans,
  spansFetchState,
}: CheckRunsTableProps): JSX.Element {
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
        <CheckRunsSummaryRow
          traceIdToSpans={traceIdToSpans}
          spansFetchState={spansFetchState}
        />
        {Object.entries(traceIdToSpans).map(([traceId, traceSpans]) => (
          <CheckRunTableRow
            key={traceId}
            checkId={checkId}
            traceId={traceId}
            traceSpans={traceSpans}
          />
        ))}
        {spansFetchState === "Loading" && (
          <Tr>
            <Skeleton as={Td}>
              <Text>FAIL</Text>
            </Skeleton>
            <Skeleton as={Td} />
            <Skeleton as={Td} />
          </Tr>
        )}
      </Tbody>
    </Table>
    // </TableContainer>
  );
}

function CheckRunsSummaryRow({
  traceIdToSpans,
  spansFetchState,
}: {
  traceIdToSpans: Record<string, SpanResult>;
  spansFetchState: FetchState;
}): JSX.Element {
  let passedCount = 0;
  let failedCount = 0;
  for (const [, traceSpans] of Object.entries(traceIdToSpans)) {
    let checkPass = true;
    for (const resourceSpans of traceSpans.resourceSpans) {
      for (const scopeSpans of resourceSpans.scopeSpans) {
        for (const span of scopeSpans.spans) {
          if (IsSpanError(span)) {
            checkPass = false;
          }
        }
      }
    }
    if (checkPass) {
      passedCount++;
    } else {
      failedCount++;
    }
  }
  return (
    <Tr>
      <Td className={failedCount === 0 ? "bg-green-300" : "bg-red-300"}>
        <LoadingDiv fetchState={spansFetchState}>
          <Text className="whitespace-pre">
            PASS {passedCount}
            <br />
            FAIL {failedCount}
          </Text>
        </LoadingDiv>
      </Td>
      <Td />
      <Td />
    </Tr>
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
