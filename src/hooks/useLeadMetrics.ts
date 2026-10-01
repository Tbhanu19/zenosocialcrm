import { useQuery } from "@tanstack/react-query"
import { fetchLeadMetrics } from "../api/metrics.ts"
import { queryKeys, type LeadMetricFilters } from "../api/query-keys.ts"

export function useLeadMetrics(companyId: string | null, filters: LeadMetricFilters) {
  return useQuery({
    queryKey: queryKeys.leadMetrics(companyId ?? "", filters),
    queryFn: () => fetchLeadMetrics(companyId ?? "", filters),
    enabled: Boolean(companyId),
  })
}
