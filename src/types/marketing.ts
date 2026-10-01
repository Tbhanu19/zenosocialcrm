import type { Page } from "./management.ts"

export type { Page }

export const CAMPAIGN_TYPES = [
  "promotion",
  "email",
  "sms",
  "social",
  "paid_ad",
  "search",
  "referral",
  "event",
  "other",
] as const

export const CAMPAIGN_CHANNELS = [
  "email",
  "sms",
  "facebook",
  "instagram",
  "google",
  "website",
  "referral",
  "direct",
  "other",
] as const

export const CAMPAIGN_STATUSES = ["draft", "active", "paused", "completed", "archived"] as const

export const LEAD_STATUSES = [
  "new",
  "contacted",
  "qualified",
  "unqualified",
  "converted",
  "lost",
  "archived",
] as const

export const LEAD_PRIORITIES = ["low", "medium", "high"] as const

export const LEAD_SOURCES = [
  "manual",
  "website",
  "email",
  "sms",
  "facebook",
  "instagram",
  "google",
  "referral",
  "campaign",
  "other",
] as const

export type CampaignType = (typeof CAMPAIGN_TYPES)[number]
export type CampaignChannel = (typeof CAMPAIGN_CHANNELS)[number]
export type CampaignStatus = (typeof CAMPAIGN_STATUSES)[number]
export type LeadStatus = (typeof LEAD_STATUSES)[number]
export type LeadPriority = (typeof LEAD_PRIORITIES)[number]
export type LeadSource = (typeof LEAD_SOURCES)[number]

export type CampaignListItem = {
  id: string
  name: string
  campaign_type: CampaignType
  channel: CampaignChannel
  status: CampaignStatus
  start_date: string | null
  end_date: string | null
  budget: string | null
  source: string | null
  created_at: string
}

export type CampaignRecord = CampaignListItem & {
  description: string | null
  external_campaign_id: string | null
  notes: string | null
  created_by_user_id: string | null
  creator_name: string | null
  updated_at: string
}

export type CampaignWrite = {
  name: string
  description: string | null
  campaign_type: CampaignType
  channel: CampaignChannel
  status: CampaignStatus
  start_date: string | null
  end_date: string | null
  budget: string | null
  source: string | null
  external_campaign_id: string | null
  notes: string | null
}

export type MarketingSummary = {
  active_campaigns: number
  total_leads: number
  new_leads: number
  converted_leads: number
}

export const BUSINESS_TYPES = ["hotels", "plumbing", "hvac"] as const

export type BusinessType = (typeof BUSINESS_TYPES)[number]

export const BUSINESS_TYPE_LABELS: Record<BusinessType, string> = {
  hotels: "Hotels",
  plumbing: "Plumbing",
  hvac: "HVAC",
}

export type LeadListItem = {
  id: string
  title: string
  status: LeadStatus
  priority: LeadPriority
  source: LeadSource
  contact_id: string | null
  contact_name: string | null
  campaign_id: string | null
  campaign_name: string | null
  campaign_status: CampaignStatus | null
  assigned_to_user_id: string | null
  assignee_name: string | null
  estimated_value: string | null
  created_at: string
  company_name: string | null
  business_type: BusinessType | null
  address: string | null
  phone_number: string | null
  main_contact_name: string | null
  email: string | null
  phone_number_2: string | null
  comments: string | null
  preferred_contact_type: "email" | "phone" | "in_person" | "others" | null
  pipeline_created_at: string | null
}

export type LeadRecord = LeadListItem & {
  description: string | null
  notes: string | null
  expected_close_date: string | null
  updated_at: string
  pipeline_id: string | null
  pipeline_stage_id: string | null
  pipeline_name: string | null
  stage_name: string | null
}

export type LeadWrite = {
  title: string
  source: LeadSource
  status: LeadStatus
  priority: LeadPriority
  company_name: string
  business_type: BusinessType
  address: string | null
  phone_number: string | null
  main_contact_name: string | null
  email: string | null
  phone_number_2: string | null
  comments: string | null
}
