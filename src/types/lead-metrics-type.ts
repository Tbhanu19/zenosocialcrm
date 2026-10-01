export type LeadMetricsTypeStatus = "active" | "inactive"

export type LeadMetricsType = {
  id: string
  company_id: string
  name: string
  description: string | null
  value: number
  status: LeadMetricsTypeStatus
  created_at: string
  updated_at: string
}

export type LeadMetricsTypeWrite = {
  name: string
  description: string | null
  value: number
  status: LeadMetricsTypeStatus
}

export type LeadMetricsTypeUpdate = {
  name?: string
  description?: string | null
  value?: number
  status?: LeadMetricsTypeStatus
}
