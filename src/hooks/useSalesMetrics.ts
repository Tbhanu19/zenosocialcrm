import { useQuery } from "@tanstack/react-query"
import { fetchSalesMetrics } from "../api/sales-metrics.ts"
import { queryKeys, type SalesMetricFilters } from "../api/query-keys.ts"

export function useSalesMetrics(companyId: string | null, filters: SalesMetricFilters) {
  return useQuery({
    queryKey: queryKeys.salesMetrics(companyId ?? "", filters),
    queryFn: () => fetchSalesMetrics(companyId ?? "", filters),
    enabled: Boolean(companyId),
  })
}
