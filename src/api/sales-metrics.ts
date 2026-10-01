import type { SalesMetricFilters } from "./query-keys.ts"
import { apiFetch } from "./client.ts"
import type { SalesMetrics } from "../types/sales-metrics.ts"

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

export function fetchSalesMetrics(
  companyId: string,
  filters: SalesMetricFilters,
): Promise<SalesMetrics> {
  return apiFetch(
    `/api/companies/${companyId}/sales-metrics${queryString({
      date_from: filters.dateFrom,
      date_to: filters.dateTo,
      pipeline_id: filters.pipelineId,
      stage_id: filters.stageId,
      assigned_to_user_id: filters.assignedTo,
      source: filters.source,
      campaign_id: filters.campaignId,
    })}`,
  )
}
