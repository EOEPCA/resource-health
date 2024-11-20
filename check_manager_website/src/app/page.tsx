'use client'

import { JSX, useState } from 'react'
import Form from '@rjsf/core';
import { Check, CheckId, CheckTemplate, ListChecks, ListCheckTemplates, NewCheck, RemoveCheck } from "src/app/server"
import validator from '@rjsf/validator-ajv8';


const log = (type: string) => console.log.bind(console, type);

function StringifyPretty(json: object): string {
  return JSON.stringify(json, null, 2)
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
        <p>Loading</p>
      </main>
    )
  }
  return (
    <main className="prose lg:prose-xl flex min-h-screen flex-col items-start p-24">
      <CheckTemplatesListDiv templates={checkTemplates} />
      <CreateCheckDiv templates={checkTemplates} onCreateCheck={(check) => setChecks([...checks, check])} />
      <ChecksDiv checks={checks} onCheckRemove={(checkId) => setChecks(checks.filter((check) => check.id !== checkId))} />
    </main>
  )
}

function CheckTemplatesListDiv({templates}: {templates: CheckTemplate[]}): JSX.Element {
  function CheckTemplateDiv(template: CheckTemplate): JSX.Element {
    return (
      <details>
        <summary>{template.metadata.label}</summary>
        <p>{template.metadata.description}</p>
        {/* <button type="button">List Checks</button>
        <button type="button">Create Check</button>
        {StringifyPretty(template)} */}
      </details>
    )
  }
  
  return (
    <div>
      <h2>Check Template List</h2>
      {templates.map((template) => <CheckTemplateDiv key={template.id} {...template}/>)}
    </div>
  )
}

function CreateCheckDiv({templates, onCreateCheck}: {templates: CheckTemplate[], onCreateCheck: (check: Check) => void}): JSX.Element {
  const [templateId, setTemplateId] = useState(templates[0].id)
  // const [templateArgs, setTemplateArgs] = useState({})
  const [schedule, setSchedule] = useState("")
  const [check, setCheck] = useState<Check | null>(null)
  const template: CheckTemplate = templates.find((template) => template.id === templateId) as CheckTemplate
  return (
    <div>
      <h2>Create Check</h2>
      <div className="flex flex-row">
        <label>Check Template Id</label>
        {/* <p>{templateId}</p> */}
        <select className="mx-4">
          {templates.map((template) => (<option key={template.id} onClick={() => setTemplateId(template.id)}>{template.id}</option>))}
        </select>
      </div>
      <div className="flex flex-row">
        <label>Schedule</label>
        <input className="border-2 mx-4"
          value={schedule}
          onChange={e => setSchedule(e.target.value)}
        />
      </div>
      <Form
        schema={template.arguments}
        validator={validator}
        onChange={log('changed')}
        onSubmit={(data) => {NewCheck(templateId, data.formData, schedule).then((newCheck) => {setCheck(newCheck); onCreateCheck(newCheck)})}}
        onError={log('errors')}
      />,
      {/* <div>
        <label>Tamplate args</label>
        {for}
      </div> */}
      {/* <button type="button" className="underline text-blue-500" onClick={() => NewCheck(templateId, templateArgs, schedule).then((newCheck) => {setCheck(newCheck); onCreateCheck(newCheck)})}>Create Check</button> */}
      {check && <p className="whitespace-pre">New Check {StringifyPretty(check)}</p>}
    </div>
  )
}

function ChecksDiv({checks, onCheckRemove}: {checks: Check[], onCheckRemove: (checkId: CheckId) => void}): JSX.Element {
  function CheckDiv({check, onCheckRemove}: {check: Check, onCheckRemove: (checkId: CheckId) => void}): JSX.Element {
    return (
      <details>
        <summary>{check.metadata.label || check.id}</summary>
        {/* <p>{check.metadata.description}</p> */}
        <p className="whitespace-pre">{StringifyPretty(check)}</p>
        <button type="button" className="underline text-blue-500" onClick={() => {RemoveCheck(check.id); onCheckRemove(check.id)}}>Remove Check</button>
      </details>
    )
  }

  return (
    <div>
      <h2>Check List</h2>
      {checks.map((check) => <CheckDiv key={check.id} check={check} onCheckRemove={onCheckRemove} />)}
    </div>
  )
}
