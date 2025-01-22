'use client'

import { JSX, useState } from 'react'
import Form from '@rjsf/chakra-ui';
import { Check, CheckId, CheckTemplate, CheckTemplateId, GetSpansQueryParams, ListChecks, ListCheckTemplates, NewCheck, ReduceSpans, RemoveCheck } from "@/app/check_api_wrapper"
import validator from '@rjsf/validator-ajv8';
import { Button, CSSReset, FormControl, FormLabel, Grid, GridItem, Heading, Input, Select, Table, TableContainer, Tbody, Td, Text, Textarea, Th, Thead, theme, ThemeProvider, Tr } from '@chakra-ui/react';

const log = (type: string) => console.log.bind(console, type);
const LOADING_STRING = "Loading ..."

function StringifyPretty(json: object): string {
  return JSON.stringify(json, null, 2)
}

function FindCheckTemplate(templates: CheckTemplate[], templateId: CheckTemplateId): CheckTemplate {
  const template = templates.find((template) => template.id === templateId)
  if (template === undefined) {
    throw Error(`template with id ${templateId} not found`)
  }
  return template
}


export default function Home(): JSX.Element {
  const [error, setError] = useState<Error | null>(null)
  const [checkTemplates, setCheckTemplates] = useState<CheckTemplate[] | null>(null)
  const [checks, setChecks] = useState<Check[] | null>(null)
  if (error !== null) {
    return (
      <ThemeProvider theme={theme}>
        <CSSReset />
        <main className="flex min-h-screen flex-col items-start p-24">
          <Heading>Error occurred</Heading>
          <Text>{`${error.name}: ${error.message}`}</Text>
        </main>
      </ThemeProvider>
    )
  }
  if (checkTemplates === null) {
    ListCheckTemplates().then(setCheckTemplates).catch(setError)
  }
  if (checks === null) {
    ListChecks().then(setChecks).catch(setError)
  }
  if (checkTemplates === null || checks === null) {
    return (
      <ThemeProvider theme={theme}>
        <CSSReset />
        <main className="flex min-h-screen flex-col items-start p-24">
          <Text>{LOADING_STRING}</Text>
        </main>
      </ThemeProvider>
    )
  }
  const now = new Date()
  const before = new Date()
  // before.setMonth(before.getMonth() - 1);
  before.setDate(before.getDate() - 5);
  return (
    <ThemeProvider theme={theme}>
      <CSSReset />
      <main className="flex min-h-screen flex-col items-start p-24">
        <ChecksDiv
          checks={checks}
          fromTime={before}
          toTime={now}
          templates={checkTemplates}
          onCreateCheck={(check) => setChecks([check, ...checks])}
          onCheckUpdate={(updatedCheck) => setChecks(checks.map((check) => check.id === updatedCheck.id ? updatedCheck : check))}
          onCheckRemove={(checkId) => setChecks(checks.filter((check) => check.id !== checkId))}
          setError={setError}
        />
      </main>
    </ThemeProvider>
  )
}

type SpansSummary = {
  traceIds: Set<string>
  failedTraceIds: Set<string>
  totalDurationSecs: number
  durationCount: number
  totalTestCount: number
}

function GetAverageDuration(spansSummary: SpansSummary): string {
  return spansSummary.durationCount === 0 ? "N/A" : (spansSummary.totalDurationSecs / spansSummary.durationCount).toLocaleString() + " s"
}

async function ComputeSpansSummary(getSpansQueryParams: GetSpansQueryParams): Promise<SpansSummary> {
  return ReduceSpans<SpansSummary>(
    getSpansQueryParams,
    ({traceIds, failedTraceIds, totalDurationSecs, durationCount, totalTestCount}, spanResult) => {
      for (const resourceSpans of spanResult.resourceSpans) {
        for (const scopeSpans of resourceSpans.scopeSpans) {
          for (const span of scopeSpans.spans) {
            traceIds.add(span.traceId)
            if (span.status?.code === 2) {
              failedTraceIds.add(span.traceId)
            }
            if (span.parentSpanId === "") {
              totalDurationSecs += (span.endTimeUnixNano - span.startTimeUnixNano) / 1_000_000_000
              durationCount++
            }
            for (const attribute of span.attributes) {
              if (attribute.key === 'test.case.result.status') {
                totalTestCount++
                break
              }
            }
          }
        }
      }
      return {traceIds, failedTraceIds, totalDurationSecs, durationCount, totalTestCount}
    },
    {traceIds: new Set<string>(), failedTraceIds: new Set<string>(), totalDurationSecs: 0, durationCount: 0, totalTestCount: 0}
  )
}

type CheckDivCommonProps = {
  fromTime?: Date
  toTime?: Date
  templates: CheckTemplate[]
  onCheckUpdate: (check: Check) => void
  onCheckRemove: (checkId: CheckId) => void
  setError: (error: Error) => void
}

function ChecksDiv({checks, onCreateCheck, ...commonProps}: {checks: Check[], onCreateCheck: (check: Check) => void} & CheckDivCommonProps): JSX.Element {
  return (
    <div>
      <Heading>Check List</Heading>
      <Text>From {commonProps.fromTime?.toLocaleString()} to {commonProps.toTime?.toLocaleString()}</Text>
      <TableContainer>
        <Table variant='simple'>
          <Thead>
            <Tr>
              <Th>Check info</Th>
              <Th>Run count</Th>
              <Th>Problematic run count</Th>
              <Th>Average duration</Th>
              <Th>Total test count</Th>
            </Tr>
          </Thead>
          <Tbody>
            {SummaryRowDiv(commonProps)}
            {CreateCheckDiv({onCreateCheck: onCreateCheck, ...commonProps})}
            {checks.map((check) => <CheckDiv key={check.id} check={check} {...commonProps} />)}
          </Tbody>
        </Table>
      </TableContainer>
    </div>
  )
}

function SummaryRowDiv({fromTime, toTime, setError}: {fromTime?: Date, toTime?: Date, setError: (error: Error) => void}): JSX.Element {
  const [spansSummary, setSpansSummary] = useState<SpansSummary | null>(null)
  if (spansSummary === null) {
    ComputeSpansSummary({
      fromTime: fromTime,
      toTime: toTime,
    }).then(setSpansSummary).catch(setError)
  }
  return (
    <Tr>
      <Td>From all checks (not only those in the table)</Td>
      <Td>{spansSummary?.durationCount ?? LOADING_STRING}</Td>
      <Td>{spansSummary?.failedTraceIds.size ?? LOADING_STRING}</Td>
      <Td>{spansSummary !== null ? GetAverageDuration(spansSummary) : LOADING_STRING}</Td>
      <Td>{spansSummary?.totalTestCount ?? LOADING_STRING}</Td>
    </Tr>
  )
}

function CreateCheckDiv({templates, onCreateCheck, setError}: {templates: CheckTemplate[], onCreateCheck: (check: Check) => void, setError: (error: Error) => void}): JSX.Element {
  const [templateId, setTemplateId] = useState(templates[0].id)
  // Only used as a hacky way to force clearing of form data
  const [key, setKey] = useState(0)
  const [schedule, setSchedule] = useState("")
  const template = FindCheckTemplate(templates, templateId)
  const form_id = "create_check"
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
                onChange={e => setTemplateId(e.target.value)}
              >
                {templates.map((template) => (
                  <option
                    key={template.id}
                    value={template.id}
                  >
                    {template.metadata.label || template.id}
                  </option>
                ))}
              </Select>
              <Text>{template.metadata.description}</Text>
              <FormLabel>Template ID</FormLabel>
              <Text>{template.id}</Text>
            </GridItem>
            <GridItem>
              <FormControl isRequired>
                <FormLabel>Schedule</FormLabel>
                <Input
                  form={form_id}
                  value={schedule}
                  onChange={e => setSchedule(e.target.value)}
                />
              </FormControl>
            </GridItem>
          </Grid>
          <Form
            id={form_id}
            idPrefix={form_id + "_"}
            key={key}
            schema={template.arguments}
            validator={validator}
            onChange={log('changed')}
            onSubmit={(data) => {
              setSchedule("")
              // A hacky way to force clearing of form data
              setKey(1 - key)
              setTemplateId(templates[0].id)
              NewCheck(templateId, data.formData, schedule)
                .then(onCreateCheck)
                .catch(setError)
            }}
            onError={log('errors')}
          />
        </details>
      </Td>
    </Tr>
  )
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars
function CheckDiv({check, fromTime, toTime, templates, onCheckUpdate, onCheckRemove, setError}: {check: Check} & CheckDivCommonProps): JSX.Element {
  const [templateId, setTemplateId] = useState(check.metadata.template_id)
  const [schedule, setSchedule] = useState(check.schedule)
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const [isDisabled, setIsDisabled] = useState(true)
  const [spansSummary, setSpansSummary] = useState<SpansSummary | null>(null)
  if (spansSummary === null) {
    ComputeSpansSummary({
      fromTime: fromTime,
      toTime: toTime,
      resourceAttributes: check.outcome_filter.resource_attributes,
      scopeAttributes: check.outcome_filter.scope_attributes,
      spanAttributes: check.outcome_filter.span_attributes
    }).then(setSpansSummary).catch(setError)
  }
  const check_label = check.metadata.template_args === undefined ? check.id : check.metadata.template_args['health_check.name'] ?? check.id
  let checkDiv
  if (templateId) {
    const template = FindCheckTemplate(templates, templateId)
    const form_id = "existing_check_" + check.id
    checkDiv = (
    <>
      <FormControl isDisabled={isDisabled}>
        <Grid gap={6} marginBottom={6}>
          <GridItem>
            <FormLabel>Check Template Id</FormLabel>
            <Select
              form={form_id}
              value={template.id}
              onChange={e => setTemplateId(e.target.value)}
            >
              {templates.map((template) => (<option key={template.id} value={template.id}>{template.id}</option>))}
            </Select>
          </GridItem>
          <GridItem>
            <FormControl isRequired isDisabled={isDisabled}>
              <FormLabel>Schedule</FormLabel>
              <Input
                form={form_id}
                value={schedule}
                onChange={e => setSchedule(e.target.value)}
              />
            </FormControl>
          </GridItem>
        </Grid>
        <Form
          idPrefix={form_id + "_"}
          schema={template.arguments}
          formData={check.metadata.template_args}
          uiSchema={{
            "ui:readonly": isDisabled,
            "ui:options": {
              submitButtonOptions: {
                norender: true,
                props: {
                  disabled: isDisabled
                },
              }
            }
          }}
          validator={validator}
          onChange={log('changed')}
          // onSubmit={(data) => {setIsDisabled(!isDisabled); UpdateCheck(check, templateId, data.formData, schedule).then((updatedCheck) => { onCheckUpdate(updatedCheck)}).catch(setError)}}
          onError={log('errors')}
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
      <Button type="button" onClick={() => {RemoveCheck(check.id); onCheckRemove(check.id)}}>Remove Check</Button>
    </>)
  }
  else {
    const template_args = check.metadata.template_args!
    checkDiv = (
    <>
      <FormControl isDisabled={isDisabled}>
        <Grid gap={6} marginBottom={6}>
          <GridItem>
            <FormLabel>Schedule</FormLabel>
            <Input
              value={schedule}
              onChange={e => setSchedule(e.target.value)}
            />
          </GridItem>
          {Object.entries(template_args).map(([key, value]) => (
            <GridItem key={key}>
              <FormLabel>{key}</FormLabel>
              <Textarea value={value} />
            </GridItem>
          ))}
        </Grid>
      </FormControl>
    </>)
  }
  return (
    <Tr>
      <Td>
        <details>
          <summary>{check_label}</summary>
          <Grid gap={6} marginBottom={6}>
            <div>
              <FormLabel>Check id</FormLabel>
              <Text>{check.id}</Text>
            </div>
            <div>
              <FormLabel>Outcome Filter</FormLabel>
              <Text className="whitespace-pre">{StringifyPretty(check.outcome_filter)}</Text>
            </div>
          </Grid>
          {checkDiv}
        </details>
      </Td>
      <Td>{spansSummary?.durationCount ?? LOADING_STRING}</Td>
      <Td>{spansSummary?.failedTraceIds.size ?? LOADING_STRING}</Td>
      <Td>{spansSummary !== null ? GetAverageDuration(spansSummary) : LOADING_STRING}</Td>
      <Td>{spansSummary?.totalTestCount ?? LOADING_STRING}</Td>
    </Tr>
  )
}
