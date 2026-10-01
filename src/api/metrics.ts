import type { LeadMetricFilters } from "./query-keys.ts"
import { apiFetch } from "./client.ts"
import type { LeadMetrics } from "../types/metrics.ts"

function queryString(entries: Record<string, string>): string {
  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(entries)) {
    if (value !== "") {
      params.set(key, value)
    }
  }
  const text = params.toString()
  return text ? `?${text}` : ""
}

export function fetchLeadMetrics(
  companyId: string,
  filters: LeadMetricFilters,
): Promise<LeadMetrics> {
  return apiFetch(
    `/api/companies/${companyId}/lead-metrics${queryString({
      date_from: filters.dateFrom,
      date_to: filters.dateTo,
      status: filters.status,
    })}`,
  )
}
