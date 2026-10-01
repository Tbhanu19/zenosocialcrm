import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import {
  createLeadMetricsType,
  fetchLeadMetricsTypes,
  updateLeadMetricsType,
} from "../api/lead-metrics-types.ts"
import { queryKeys } from "../api/query-keys.ts"
import type { LeadMetricsTypeUpdate, LeadMetricsTypeWrite } from "../types/lead-metrics-type.ts"

export function useLeadMetricsTypes(companyId: string | null) {
  return useQuery({
    queryKey: queryKeys.leadMetricsTypes(companyId ?? ""),
    queryFn: () => fetchLeadMetricsTypes(companyId ?? ""),
    enabled: Boolean(companyId),
  })
}

export function useCreateLeadMetricsType(companyId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: LeadMetricsTypeWrite) => createLeadMetricsType(companyId, body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.leadMetricsTypes(companyId) })
    },
  })
}

export function useUpdateLeadMetricsType(companyId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ typeId, body }: { typeId: string; body: LeadMetricsTypeUpdate }) =>
      updateLeadMetricsType(companyId, typeId, body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.leadMetricsTypes(companyId) })
    },
  })
}
