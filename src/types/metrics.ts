import type { LeadSource, LeadStatus } from "./marketing.ts"

export type LeadMetricSummary = {
  total_leads: number
  new_leads: number
  contacted_leads: number
  qualified_leads: number
  unqualified_leads: number
  converted_leads: number
  lost_leads: number
  conversion_rate: string
}

export type LeadStatusCount = {
  status: LeadStatus
  count: number
}

export type LeadSourceCount = {
  source: LeadSource
  count: number
}

export type LeadCampaignCount = {
  campaign_id: string | null
  campaign_name: string | null
  lead_count: number
  converted_count: number
}

export type LeadTimePoint = {
  period: string
  lead_count: number
  converted_count: number
}

export type LeadMetrics = {
  interval: "day" | "week" | "month"
  summary: LeadMetricSummary
  by_status: LeadStatusCount[]
  by_source: LeadSourceCount[]
  by_campaign: LeadCampaignCount[]
  over_time: LeadTimePoint[]
}
