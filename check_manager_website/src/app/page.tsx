'use client'

import { JSX, useState } from 'react'
import { Check, CheckTemplate, ListCheckTemplates, NewCheck } from "src/app/server"


// JSON.stringify
export default function Home(): JSX.Element {
  const [checkTemplates, setCheckTemplates] = useState<CheckTemplate[] | null>(null)
  if (!checkTemplates) {
    ListCheckTemplates().then(setCheckTemplates)
  }
  if (!checkTemplates) {
    return (
      <main className="prose lg:prose-xl flex min-h-screen flex-col items-start p-24">
        <p>Loading</p>
      </main>
    )
  }
  return (
    <main className="prose lg:prose-xl flex min-h-screen flex-col items-start p-24">
      <div>
        <h2>Check Template List</h2>
        {checkTemplates.map((template) => <CheckTemplateDiv key={template.id} {...template}/>)}
      </div>
      <CreateCheckDiv templates={checkTemplates} />
    </main>
  )
}

function CheckTemplateDiv(template: CheckTemplate): JSX.Element {
  return (
    <div>
      <h4>{template.metadata.label}</h4>
      <p>{template.metadata.description}</p>
      {/* <button type="button">List Checks</button>
      <button type="button">Create Check</button>
      {JSON.stringify(template)} */}
    </div>
  )
}

function CreateCheckDiv({templates}: {templates: CheckTemplate[]}): JSX.Element {
  const [templateId, setTemplateId] = useState(templates[0].id)
  const [templateArgs, setTemplateArgs] = useState({})
  const [schedule, setSchedule] = useState("")
  const [check, setCheck] = useState<Check | null>(null)
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
      {/* <div>
        <label>Tamplate args</label>
        {for}
      </div> */}
      <button type="button" className="underline text-blue-500" onClick={() => NewCheck(templateId, templateArgs, schedule).then(setCheck)}>Create Check</button>
      {check && <p className="whitespace-pre">New Check {JSON.stringify(check, null, 2)}</p>}
    </div>
  )
}
