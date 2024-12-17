'use client'

import { JSX, useState } from 'react'
import Form from '@rjsf/chakra-ui';
import { Check, CheckId, CheckTemplate, CheckTemplateId, GetSpans, GetSpansQueryParams, ListChecks, ListCheckTemplates, NewCheck, ReduceSpans, RemoveCheck, SpansResponse, UpdateCheck } from "@/app/check_api_wrapper"
import validator from '@rjsf/validator-ajv8';
import { Button, CSSReset, FormControl, FormLabel, Grid, GridItem, Heading, Input, Select, Text, theme, ThemeProvider } from '@chakra-ui/react';


const log = (type: string) => console.log.bind(console, type);

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
          <Text>Loading</Text>
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
        {/* <CheckTemplatesListDiv templates={checkTemplates} /> */}
        <ResultsSummaryDiv fromTime={before} toTime={now} setError={setError}/>
        <CreateCheckDiv templates={checkTemplates} onCreateCheck={(check) => setChecks([...checks, check])} setError={setError} />
        <ChecksDiv
          checks={checks}
          templates={checkTemplates}
          onCheckUpdate={(updatedCheck) => setChecks(checks.map((check) => check.id === updatedCheck.id ? updatedCheck : check))}
          onCheckRemove={(checkId) => setChecks(checks.filter((check) => check.id !== checkId))}
          setError={setError}
        />
      </main>
    </ThemeProvider>
  )
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars
function CheckTemplatesListDiv({templates}: {templates: CheckTemplate[]}): JSX.Element {
  function CheckTemplateDiv(template: CheckTemplate): JSX.Element {
    return (
      <details>
        <summary>{template.metadata.label}</summary>
        <Text>{template.metadata.description}</Text>
        {/* <button type="button">List Checks</button>
        <button type="button">Create Check</button>
        {StringifyPretty(template)} */}
      </details>
    )
  }
  
  return (
    <div>
      <Heading>Check Template List</Heading>
      {templates.map((template) => <CheckTemplateDiv key={template.id} {...template}/>)}
    </div>
  )
}

function CreateCheckDiv({templates, onCreateCheck, setError}: {templates: CheckTemplate[], onCreateCheck: (check: Check) => void, setError: (error: Error) => void}): JSX.Element {
  const [templateId, setTemplateId] = useState(templates[0].id)
  // const [templateArgs, setTemplateArgs] = useState({})
  const [schedule, setSchedule] = useState("")
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const [check, setCheck] = useState<Check | null>(null)
  const template = FindCheckTemplate(templates, templateId)
  return (
    <div>
      <Heading>Create Check</Heading>
      <Grid gap={6} marginBottom={6}>
        <GridItem>
          <FormLabel>Check Template</FormLabel>
          {/* <Text>{templateId}</Text> */}
          <Select>
            {templates.map((template) => (
              <option
                key={template.id}
                onClick={() => setTemplateId(template.id)}
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
          <FormLabel>Schedule</FormLabel>
          <Input
            value={schedule}
            onChange={e => setSchedule(e.target.value)}
          />
        </GridItem>
      </Grid>
      <Form
        schema={template.arguments}
        validator={validator}
        onChange={log('changed')}
        onSubmit={(data) => {NewCheck(templateId, data.formData, schedule).then((newCheck) => {setCheck(newCheck); onCreateCheck(newCheck)}).catch(setError)}}
        onError={log('errors')}
      />
      {/* <div>
        <FormLabel>Tamplate args</FormLabel>
        {for}
      </div> */}
      {/* <button type="button" className="underline text-blue-500" onClick={() => NewCheck(templateId, templateArgs, schedule).then((newCheck) => {setCheck(newCheck); onCreateCheck(newCheck)}).catch(setError)}>Create Check</button> */}
      {/* {check && <Text className="whitespace-pre">New Check {StringifyPretty(check)}</Text>} */}
    </div>
  )
}

type SpansSummary = {
  traceIds: Set<string>
  failedTraceIds: Set<string>
  totalDurationSecs: number
  durationCount: number
  totalTestCount: number
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

function ResultsSummaryDiv({fromTime, toTime, setError}: {fromTime?: Date, toTime?: Date, setError: (error: Error) => void}): JSX.Element {
  // const [spansResponse, setSpansResponse] = useState<SpansResponse | null>(null)
  // if (spansResponse === null) {
  //   GetSpans({fromTime: fromTime, toTime: toTime}).then(setSpansResponse).catch(setError)
  // }
  // const traceIds = new Set<string>()
  // const failedTraceIds = new Set<string>()
  // if (spansResponse !== null) {
  //   for (const resourceSpansArray of spansResponse.results) {
  //     for (const resourceSpans of resourceSpansArray.resourceSpans) {
  //       for (const scopeSpans of resourceSpans.scopeSpans) {
  //         for (const span of scopeSpans.spans) {
  //           traceIds.add(span.traceId)
  //           if (span.status?.code === 2) {
  //             failedTraceIds.add(span.traceId)
  //           }
  //         }
  //       }
  //     }
  //   }
  // }



  const [spansSummary, setSpansSummary] = useState<SpansSummary | null>(null)
  if (spansSummary === null) {
    ComputeSpansSummary({
      fromTime: fromTime,
      toTime: toTime,
      resourceAttributes: {
        "user.id": "Health BB user",
        "health_check.name": "hourly-simple-openeo-check"
      }
    }).then(setSpansSummary).catch(setError)
  }
  // if (spansSummary?.traceIds.size !== spansSummary?.durationCount) {
  //   throw new Error(`The number of trace ids (${spansSummary?.traceIds.size}) and the number of root spans (${spansSummary?.durationCount}) must be the same`)
  // }
  return (
    <div>
      <Heading>Status summary</Heading>
      <Text>From {fromTime?.toLocaleString()} to {toTime?.toLocaleString()}</Text>
      {spansSummary === null ?
        <Text>Loading ...</Text> : (
          <>
            <Text>Number of runs {spansSummary.durationCount}</Text>
            <Text>Number of runs with a problem {spansSummary.failedTraceIds.size}</Text>
            <Text>Average duration {spansSummary.durationCount === 0 ? "N/A" : (spansSummary.totalDurationSecs / spansSummary.durationCount).toLocaleString()} s</Text>
            <Text>Total test count {spansSummary.totalTestCount}</Text>
          </>
        )
      }
    </div>
  )
}

function ChecksDiv({checks, templates, onCheckUpdate, onCheckRemove, setError}: {checks: Check[], templates: CheckTemplate[], onCheckUpdate: (check: Check) => void, onCheckRemove: (checkId: CheckId) => void, setError: (error: Error) => void}): JSX.Element {
  function CheckDiv({check, templates, onCheckUpdate, onCheckRemove, setError}: {check: Check, templates: CheckTemplate[], onCheckUpdate: (check: Check) => void, onCheckRemove: (checkId: CheckId) => void, setError: (error: Error) => void}): JSX.Element {
    if (check.metadata.template_id === undefined)
      throw Error("Can't deal with checks without template id, at least for now")
    const [templateId, setTemplateId] = useState(check.metadata.template_id)
    const [schedule, setSchedule] = useState(check.schedule)
    const template = FindCheckTemplate(templates, templateId)
    const [isDisabled, setIsDisabled] = useState(true)
    // const [newCheck, setNewCheck] = useState<Check>(check)
    // const [template, setTemplate] = useState<CheckTemplate>(FindCheckTemplate(templates, templateId))
    // setTemplate(FindCheckTemplate(templates, templateId))
    return (
      <details>
        <summary>{check.metadata.template_args?.label || check.id}</summary>
        {/* <Text>{check.metadata.description}</Text> */}
        <Grid gap={6} marginBottom={6}>
          <div>
            <FormLabel>Check id</FormLabel>
            <Text>{check.id}</Text>
          </div>
          <div>
            <FormLabel>Outcome Filter</FormLabel>
            <Text className="whitespace-pre">{StringifyPretty(check.outcome_filter)}</Text>
          </div>
          {/* <Text></Text> */}
        </Grid>
        <FormControl isDisabled={isDisabled}>
          <Grid gap={6} marginBottom={6}>
            <GridItem>
              <FormLabel>Check Template Id</FormLabel>
              {/* <Text>{templateId}</Text> */}
              <Select>
                {templates.map((template) => (<option key={template.id} onClick={() => setTemplateId(template.id)}>{template.id}</option>))}
              </Select>
            </GridItem>
            <GridItem>
              <FormLabel>Schedule</FormLabel>
              <Input
                value={schedule}
                onChange={e => setSchedule(e.target.value)}
              />
            </GridItem>
          </Grid>
          <Form
            schema={template.arguments}
            formData={check.metadata.template_args}
            uiSchema={{
              "ui:readonly": isDisabled,
              "ui:options": {
                submitButtonOptions: {
                  props: {
                    disabled: isDisabled
                  },
                }
              }
            }}
            validator={validator}
            onChange={log('changed')}
            onSubmit={(data) => {UpdateCheck(check, templateId, data.formData, schedule).then((updatedCheck) => { /*setNewCheck(updatedCheck);*/ onCheckUpdate(updatedCheck)}).catch(setError)}}
            onError={log('errors')}
          />
        </FormControl>
        {/* <Text className="whitespace-pre">{StringifyPretty(check)}</Text> */}
        <Button
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
        </Button>
        <Button type="button" onClick={() => {RemoveCheck(check.id); onCheckRemove(check.id)}}>Remove Check</Button>
      </details>
    )
  }

  // const [spans, setSpans] = useState<SpansResponse | null>(null)

  // if (spans === null) {
  //   GetSpans({}).then(setSpans)
  // }

  return (
    <div>
      <Heading>Check List</Heading>
      {checks.map((check) => <CheckDiv key={check.id} check={check} templates={templates} onCheckUpdate={onCheckUpdate} onCheckRemove={onCheckRemove} setError={setError} />)}
      <Heading>Spans</Heading>
      {/* {spans && (
        <Text className="whitespace-pre">
          {StringifyPretty(spans.results)}
        </Text>
      )} */}
    </div>
  )
}
