import type { LeadSource } from "./marketing.ts"

export type SalesMetricSummary = {
  total_opportunities: number
  total_pipeline_value: string
  converted_leads: number
  converted_value: string
  lost_leads: number
  lost_value: string
  conversion_rate: string
  average_opportunity_value: string
}

export type SalesStageMetric = {
  stage_id: string | null
  stage_name: string | null
  position: number | null
  lead_count: number
  pipeline_value: string
  converted_count: number
  converted_value: string
}

export type SalesSourceMetric = {
  source: LeadSource
  lead_count: number
  pipeline_value: string
  converted_count: number
  converted_value: string
}

export type SalesCampaignMetric = {
  campaign_id: string | null
  campaign_name: string | null
  lead_count: number
  pipeline_value: string
  converted_count: number
  converted_value: string
}

export type SalesUserMetric = {
  user_id: string | null
  user_name: string | null
  opportunity_count: number
  pipeline_value: string
  converted_count: number
  converted_value: string
}

export type SalesTrendPoint = {
  period: string
  opportunity_count: number
  pipeline_value: string
  converted_count: number
  converted_value: string
}

export type ExpectedCloseMetrics = {
  upcoming_count: number
  upcoming_value: string
  overdue_count: number
  overdue_value: string
}

export type SalesCycleStatus = {
  available: boolean
  reason: string | null
}

export type SalesMetrics = {
  interval: "day" | "week" | "month"
  summary: SalesMetricSummary
  by_stage: SalesStageMetric[]
  by_source: SalesSourceMetric[]
  by_campaign: SalesCampaignMetric[]
  by_assigned_user: SalesUserMetric[]
  trend: SalesTrendPoint[]
  expected_close: ExpectedCloseMetrics
  sales_cycle: SalesCycleStatus
}
