import type { Page } from "./management.ts"
import type { LeadSource, LeadStatus } from "./marketing.ts"

export type { Page }

export const STAGE_COLORS = ["copper", "pine", "moss", "ink", "danger"] as const
export const PIPELINE_STATUSES = ["active", "archived"] as const
export const PREFERRED_CONTACT_TYPES = ["email", "phone", "in_person", "others"] as const

export const PREFERRED_CONTACT_LABELS: Record<PreferredContactType, string> = {
  email: "Email",
  phone: "Phone",
  in_person: "In person",
  others: "Others",
}
export const STAGE_STATUSES = ["active", "inactive"] as const

export type StageColor = (typeof STAGE_COLORS)[number]
export type PipelineStatus = (typeof PIPELINE_STATUSES)[number]
export type PreferredContactType = (typeof PREFERRED_CONTACT_TYPES)[number]
export type StageStatus = (typeof STAGE_STATUSES)[number]

export type PipelineListItem = {
  id: string
  name: string
  status: PipelineStatus
  created_at: string
}

export type StageRecord = {
  id: string
  pipeline_id: string
  name: string
  description: string | null
  position: number
  color: StageColor
  status: StageStatus
}

export type PipelineRecord = PipelineListItem & {
  description: string | null
  updated_at: string
  stages: StageRecord[]
}

export type PipelineCard = {
  id: string
  title: string
  contact_name: string | null
  estimated_value: string | null
  assignee_name: string | null
  source: LeadSource
  expected_close_date: string | null
  pipeline_stage_id: string
  preferred_contact_type: PreferredContactType | null
  pipeline_created_at: string | null
}

export type StageColumn = {
  stage_id: string
  stage_name: string
  position: number
  color: StageColor
  lead_count: number
  estimated_value_total: string
  leads: PipelineCard[]
  has_more: boolean
}

export type PipelineBoard = {
  pipeline_id: string
  pipeline_name: string
  per_stage: number
  stages: StageColumn[]
}

export type LeadPipelineResult = {
  id: string
  title: string
  status: LeadStatus
  pipeline_id: string
  pipeline_stage_id: string
  pipeline_name: string
  stage_name: string
}

export type PipelineWrite = {
  name: string
  description: string | null
  status?: PipelineStatus
}

export type StageWrite = {
  name: string
  description: string | null
  color: StageColor
  status?: StageStatus
}
