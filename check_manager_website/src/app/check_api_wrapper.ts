// This is important to make sure that ListCheckTemplates aren't called only when building the website
'use client'

import { StrictRJSFSchema } from '@rjsf/utils'
import axios from 'axios'
import { env } from 'next-runtime-env';

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

function GetBaseURL(): string {
  const url = env('NEXT_PUBLIC_CHECK_MANAGER_ENDPOINT')
  if (!url) {
    throw new Error(`environment variable NEXT_PUBLIC_CHECK_MANAGER_ENDPOINT must be set`)
  }
  return url
}

export async function ListCheckTemplates(ids?: CheckTemplateId[]): Promise<CheckTemplate[]> {
  const response = await axios.get(GetBaseURL() + "/check_templates/", {params: ids})
  return response.data
}

export async function NewCheck(templateId: CheckTemplateId, templateArgs: object, schedule: CronExpression): Promise<Check> {
  const response = await axios.post(GetBaseURL() + "/checks/", {template_id: templateId, template_args: templateArgs, schedule: schedule})
  return response.data
}

export async function UpdateCheck(oldCheck: Check, templateId?: CheckTemplateId, templateArgs?: object, schedule?: CronExpression): Promise<Check> {
  if (templateId === oldCheck.metadata.template_id) {
    templateId = undefined
  }

  if (templateArgs === oldCheck.metadata.template_args) {
    templateArgs = undefined
  }
  
  if (schedule === oldCheck.schedule) {
    schedule = undefined
  }
  const response = await axios.patch(GetBaseURL() + `/checks/${oldCheck.id}`, {template_id: templateId, template_args: templateArgs, schedule: schedule})
  return response.data
}

export async function RemoveCheck(checkId: CheckId): Promise<void> {
  await axios.delete(GetBaseURL() + `/checks/${checkId}`)
}

export async function ListChecks(ids?: CheckId[]): Promise<Check[]> {
  const response = await axios.get(GetBaseURL() + "/checks/", {params: ids})
  return response.data
}