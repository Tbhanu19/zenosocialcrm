import type { CampaignFilters, LeadFilters } from "./query-keys.ts"
import { apiFetch } from "./client.ts"
import type {
  CampaignListItem,
  CampaignRecord,
  CampaignWrite,
  LeadListItem,
  LeadRecord,
  LeadWrite,
  MarketingSummary,
  Page,
} from "../types/marketing.ts"

function queryString(entries: Record<string, string | number>): string {
  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(entries)) {
    if (value !== "") {
      params.set(key, String(value))
    }
  }
  const text = params.toString()
  return text ? `?${text}` : ""
}

export function fetchMarketingSummary(companyId: string): Promise<MarketingSummary> {
  return apiFetch(`/api/companies/${companyId}/marketing/summary`)
}

export function fetchCampaigns(
  companyId: string,
  filters: CampaignFilters,
): Promise<Page<CampaignListItem>> {
  return apiFetch(
    `/api/companies/${companyId}/marketing/campaigns${queryString({
      page: filters.page,
      page_size: filters.pageSize,
      search: filters.search,
      status: filters.status,
      channel: filters.channel,
      campaign_type: filters.campaignType,
      start_date: filters.startDate,
      end_date: filters.endDate,
    })}`,
  )
}

export function fetchCampaign(companyId: string, campaignId: string): Promise<CampaignRecord> {
  return apiFetch(`/api/companies/${companyId}/marketing/campaigns/${campaignId}`)
}

export function createCampaign(companyId: string, body: CampaignWrite): Promise<CampaignRecord> {
  return apiFetch(`/api/companies/${companyId}/marketing/campaigns`, {
    method: "POST",
    body: JSON.stringify(body),
  })
}

export function updateCampaign(
  companyId: string,
  campaignId: string,
  body: Partial<CampaignWrite>,
): Promise<CampaignRecord> {
  return apiFetch(`/api/companies/${companyId}/marketing/campaigns/${campaignId}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  })
}

export function fetchCampaignLeads(
  companyId: string,
  campaignId: string,
  filters: Pick<LeadFilters, "page" | "pageSize" | "status">,
): Promise<Page<LeadListItem>> {
  return apiFetch(
    `/api/companies/${companyId}/marketing/campaigns/${campaignId}/leads${queryString({
      page: filters.page,
      page_size: filters.pageSize,
      status: filters.status,
    })}`,
  )
}

export function fetchLeads(companyId: string, filters: LeadFilters): Promise<Page<LeadListItem>> {
  return apiFetch(
    `/api/companies/${companyId}/leads${queryString({
      page: filters.page,
      page_size: filters.pageSize,
      search: filters.search,
      status: filters.status,
      source: filters.source,
      priority: filters.priority,
      campaign_id: filters.campaignId,
      assigned_to: filters.assignedTo,
      created_from: filters.createdFrom,
      created_to: filters.createdTo,
    })}`,
  )
}

export function fetchLead(companyId: string, leadId: string): Promise<LeadRecord> {
  return apiFetch(`/api/companies/${companyId}/leads/${leadId}`)
}

export function createLead(companyId: string, body: LeadWrite): Promise<LeadRecord> {
  return apiFetch(`/api/companies/${companyId}/leads`, {
    method: "POST",
    body: JSON.stringify(body),
  })
}

export function updateLead(
  companyId: string,
  leadId: string,
  body: Partial<LeadWrite> & {
    preferred_contact_type?: string | null
    pipeline_created_at?: string | null
  },
): Promise<LeadRecord> {
  return apiFetch(`/api/companies/${companyId}/leads/${leadId}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  })
}
