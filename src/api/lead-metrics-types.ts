import { apiFetch } from "./client.ts"
import type {
  LeadMetricsType,
  LeadMetricsTypeUpdate,
  LeadMetricsTypeWrite,
} from "../types/lead-metrics-type.ts"

export function fetchLeadMetricsTypes(companyId: string): Promise<LeadMetricsType[]> {
  return apiFetch(`/api/companies/${companyId}/lead-metrics-types`)
}

export function createLeadMetricsType(
  companyId: string,
  body: LeadMetricsTypeWrite,
): Promise<LeadMetricsType> {
  return apiFetch(`/api/companies/${companyId}/lead-metrics-types`, {
    method: "POST",
    body: JSON.stringify(body),
  })
}

export function updateLeadMetricsType(
  companyId: string,
  typeId: string,
  body: LeadMetricsTypeUpdate,
): Promise<LeadMetricsType> {
  return apiFetch(`/api/companies/${companyId}/lead-metrics-types/${typeId}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  })
}
