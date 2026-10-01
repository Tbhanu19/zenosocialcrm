import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import {
  createCampaign,
  createLead,
  fetchCampaign,
  fetchCampaignLeads,
  fetchCampaigns,
  fetchLead,
  fetchLeads,
  fetchMarketingSummary,
  updateCampaign,
  updateLead,
} from "../api/marketing.ts"
import {
  queryKeys,
  type CampaignFilters,
  type LeadFilters,
} from "../api/query-keys.ts"
import type { CampaignWrite, LeadWrite } from "../types/marketing.ts"

export function useMarketingSummary(companyId: string | null) {
  return useQuery({
    queryKey: queryKeys.marketingSummary(companyId ?? ""),
    queryFn: () => fetchMarketingSummary(companyId ?? ""),
    enabled: Boolean(companyId),
  })
}

export function useCampaigns(
  companyId: string | null,
  filters: CampaignFilters,
  enabled = true,
) {
  return useQuery({
    queryKey: queryKeys.marketingCampaigns(companyId ?? "", filters),
    queryFn: () => fetchCampaigns(companyId ?? "", filters),
    enabled: enabled && Boolean(companyId),
  })
}

export function useCampaign(companyId: string | null, campaignId: string) {
  return useQuery({
    queryKey: queryKeys.marketingCampaign(companyId ?? "", campaignId),
    queryFn: () => fetchCampaign(companyId ?? "", campaignId),
    enabled: Boolean(companyId) && Boolean(campaignId),
  })
}

export function useCampaignLeads(
  companyId: string | null,
  campaignId: string,
  filters: Pick<LeadFilters, "page" | "pageSize" | "status">,
  enabled: boolean,
) {
  const listFilters: LeadFilters = {
    page: filters.page,
    pageSize: filters.pageSize,
    search: "",
    status: filters.status,
    source: "",
    priority: "",
    campaignId,
    assignedTo: "",
    createdFrom: "",
    createdTo: "",
  }
  return useQuery({
    queryKey: queryKeys.campaignLeads(companyId ?? "", campaignId, listFilters),
    queryFn: () => fetchCampaignLeads(companyId ?? "", campaignId, filters),
    enabled: enabled && Boolean(companyId) && Boolean(campaignId),
  })
}

export function useLeads(companyId: string | null, filters: LeadFilters, enabled = true) {
  return useQuery({
    queryKey: queryKeys.leads(companyId ?? "", filters),
    queryFn: () => fetchLeads(companyId ?? "", filters),
    enabled: enabled && Boolean(companyId),
  })
}

export function useLead(companyId: string | null, leadId: string) {
  return useQuery({
    queryKey: queryKeys.lead(companyId ?? "", leadId),
    queryFn: () => fetchLead(companyId ?? "", leadId),
    enabled: Boolean(companyId) && Boolean(leadId),
  })
}

function invalidateCampaigns(
  queryClient: ReturnType<typeof useQueryClient>,
  companyId: string,
  campaignId?: string,
) {
  void queryClient.invalidateQueries({ queryKey: ["marketing-campaigns", companyId] })
  void queryClient.invalidateQueries({ queryKey: ["marketing-summary", companyId] })
  if (campaignId) {
    void queryClient.invalidateQueries({
      queryKey: ["marketing-campaign", companyId, campaignId],
    })
  }
}

export function useCreateCampaign(companyId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: CampaignWrite) => createCampaign(companyId, body),
    onSuccess: (campaign) => {
      invalidateCampaigns(queryClient, companyId, campaign.id)
    },
  })
}

export function useUpdateCampaign(companyId: string, campaignId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: Partial<CampaignWrite>) => updateCampaign(companyId, campaignId, body),
    onSuccess: () => {
      invalidateCampaigns(queryClient, companyId, campaignId)
      void queryClient.invalidateQueries({
        queryKey: ["campaign-leads", companyId, campaignId],
      })
    },
  })
}

export function useCreateLead(companyId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: LeadWrite) => createLead(companyId, body),
    onSuccess: (lead) => {
      void queryClient.invalidateQueries({ queryKey: ["leads", companyId] })
      void queryClient.invalidateQueries({ queryKey: ["lead", companyId, lead.id] })
      void queryClient.invalidateQueries({ queryKey: ["marketing-summary", companyId] })
      void queryClient.invalidateQueries({ queryKey: ["lead-metrics", companyId] })
      void queryClient.invalidateQueries({ queryKey: ["sales-metrics", companyId] })
      void queryClient.invalidateQueries({ queryKey: ["sales-pipeline-board", companyId] })
      if (lead.campaign_id) {
        void queryClient.invalidateQueries({
          queryKey: ["campaign-leads", companyId, lead.campaign_id],
        })
      }
    },
  })
}

export function useUpdateLead(companyId: string, leadId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: Partial<LeadWrite>) => updateLead(companyId, leadId, body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["leads", companyId] })
      void queryClient.invalidateQueries({ queryKey: ["lead", companyId, leadId] })
      void queryClient.invalidateQueries({ queryKey: ["marketing-summary", companyId] })
      void queryClient.invalidateQueries({ queryKey: ["campaign-leads", companyId] })
      void queryClient.invalidateQueries({ queryKey: ["lead-metrics", companyId] })
      void queryClient.invalidateQueries({ queryKey: ["sales-metrics", companyId] })
      void queryClient.invalidateQueries({ queryKey: ["sales-pipeline-board", companyId] })
    },
  })
}
