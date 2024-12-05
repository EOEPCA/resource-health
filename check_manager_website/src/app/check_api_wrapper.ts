import { StrictRJSFSchema } from '@rjsf/utils'
import axios from 'axios'
import { connection } from 'next/server'

export type CheckTemplateId = string
export type CheckId = string
export type CronExpression = string

export type CheckTemplateMetadata = object & {
  label?: string
  description?: string
}

export type CheckMetadata = object & {
  template_id?: CheckTemplateId
  template_args?: object & {
    label?: string
    description?: string
  }
}

export type CheckTemplate = {
  id: CheckTemplateId
  metadata: CheckTemplateMetadata
  arguments: StrictRJSFSchema
}

export type Check = {
  id: CheckId
  metadata: CheckMetadata
  schedule: CronExpression
  outcome_filter: object
}

const client = axios.create({
  baseURL: "http://127.0.0.1:8000",
  headers: {
    // "Cache-Control": "no-cache",
    // "Access-Control-Allow-Origin": "*",
  }
})

export async function ListCheckTemplates(ids?: CheckTemplateId[]): Promise<CheckTemplate[]> {
  // To make this request be performed upon the client connection, not on build as per https://nextjs.org/docs/app/api-reference/functions/connection
  await connection()
  const response = await client.get("/check_templates/", {params: ids})
  return response.data
}

export async function NewCheck(templateId: CheckTemplateId, templateArgs: object, schedule: CronExpression): Promise<Check> {
  await connection()
  const response = await client.post("/checks/", {template_id: templateId, template_args: templateArgs, schedule: schedule})
  return response.data
}

export async function UpdateCheck(oldCheck: Check, templateId?: CheckTemplateId, templateArgs?: object, schedule?: CronExpression): Promise<Check> {
  await connection()
  if (templateId === oldCheck.metadata.template_id) {
    templateId = undefined
  }

  if (templateArgs === oldCheck.metadata.template_args) {
    templateArgs = undefined
  }
  
  if (schedule === oldCheck.schedule) {
    schedule = undefined
  }
  const response = await client.patch(`/checks/${oldCheck.id}`, {template_id: templateId, template_args: templateArgs, schedule: schedule})
  return response.data
}


// export async function UpdateCheck(checkId: CheckId, templateId?: CheckTemplateId, templateArgs?: object, schedule?: CronExpression): Promise<Check> {
//   await connection()
//   const response = await client.patch(`/checks/${checkId}`, {template_id: templateId, template_args: templateArgs, schedule: schedule})
//   return response.data
// }

export async function RemoveCheck(checkId: CheckId): Promise<void> {
  await connection()
  await client.delete(`/checks/${checkId}`)
}

export async function ListChecks(ids?: CheckId[]): Promise<Check[]> {
  await connection()
  const response = await client.get("/checks/", {params: ids})
  return response.data
}