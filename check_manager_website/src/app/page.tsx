'use client'

import { JSX, useState } from 'react'
import Form from '@rjsf/chakra-ui';
import { Check, CheckId, CheckTemplate, CheckTemplateId, ListChecks, ListCheckTemplates, NewCheck, RemoveCheck, UpdateCheck } from "src/app/server"
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
  const [checkTemplates, setCheckTemplates] = useState<CheckTemplate[] | null>(null)
  if (checkTemplates === null) {
    ListCheckTemplates().then(setCheckTemplates)
  }
  const [checks, setChecks] = useState<Check[] | null>(null)
  if (checks === null) {
    ListChecks().then(setChecks)
  }
  if (checkTemplates === null || checks === null) {
    return (
      <main className="prose lg:prose-xl flex min-h-screen flex-col items-start p-24">
        <Text>Loading</Text>
      </main>
    )
  }
  return (
    // <main className="prose lg:prose-xl flex min-h-screen flex-col items-start p-24">
    <ThemeProvider theme={theme}>
      <CSSReset />
      <main className="flex min-h-screen flex-col items-start p-24">
        {/* <CheckTemplatesListDiv templates={checkTemplates} /> */}
        <CreateCheckDiv templates={checkTemplates} onCreateCheck={(check) => setChecks([...checks, check])} />
        <ChecksDiv
          checks={checks}
          templates={checkTemplates}
          onCheckUpdate={(updatedCheck) => setChecks(checks.map((check) => check.id === updatedCheck.id ? updatedCheck : check))}
          onCheckRemove={(checkId) => setChecks(checks.filter((check) => check.id !== checkId))}
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

function CreateCheckDiv({templates, onCreateCheck}: {templates: CheckTemplate[], onCreateCheck: (check: Check) => void}): JSX.Element {
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
        onSubmit={(data) => {NewCheck(templateId, data.formData, schedule).then((newCheck) => {setCheck(newCheck); onCreateCheck(newCheck)})}}
        onError={log('errors')}
      />
      {/* <div>
        <FormLabel>Tamplate args</FormLabel>
        {for}
      </div> */}
      {/* <button type="button" className="underline text-blue-500" onClick={() => NewCheck(templateId, templateArgs, schedule).then((newCheck) => {setCheck(newCheck); onCreateCheck(newCheck)})}>Create Check</button> */}
      {/* {check && <Text className="whitespace-pre">New Check {StringifyPretty(check)}</Text>} */}
    </div>
  )
}

function ChecksDiv({checks, templates, onCheckUpdate, onCheckRemove}: {checks: Check[], templates: CheckTemplate[], onCheckUpdate: (check: Check) => void, onCheckRemove: (checkId: CheckId) => void}): JSX.Element {
  function CheckDiv({check, templates, onCheckUpdate, onCheckRemove}: {check: Check, templates: CheckTemplate[], onCheckUpdate: (check: Check) => void, onCheckRemove: (checkId: CheckId) => void}): JSX.Element {
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
            onSubmit={(data) => {UpdateCheck(check, templateId, data.formData, schedule).then((updatedCheck) => { /*setNewCheck(updatedCheck);*/ onCheckUpdate(updatedCheck)})}}
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

  return (
    <div>
      <Heading>Check List</Heading>
      {checks.map((check) => <CheckDiv key={check.id} check={check} templates={templates} onCheckUpdate={onCheckUpdate} onCheckRemove={onCheckRemove} />)}
    </div>
  )
}
