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

export type CheckTemplate = {
  id: CheckTemplateId
  metadata: CheckTemplateMetadata
  arguments: StrictRJSFSchema
}

export type Check = {
  id: CheckId
  metadata: object
  schedule: CronExpression
  outcomeFilter: object
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

export async function UpdateCheck(checkId: CheckId, templateId?: CheckTemplateId, templateArgs?: object, schedule?: CronExpression): Promise<Check> {
  await connection()
  const response = await client.post(`/checks/${checkId}`, {template_id: templateId, template_args: templateArgs, schedule: schedule})
  return response.data
}

export async function RemoveCheck(checkId: CheckId): Promise<void> {
  await connection()
  await client.delete(`/checks/${checkId}`)
}

export async function ListChecks(ids?: CheckId[]): Promise<Check[]> {
  await connection()
  const response = await client.get("/checks/", {params: ids})
  return response.data
}