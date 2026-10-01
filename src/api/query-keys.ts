export type ListFilters = {
  page: number
  pageSize: number
  search: string
  role: string
  status: string
}

export type CompanyListFilters = {
  page: number
  pageSize: number
  search: string
  status: string
  businessType: string
}

export type ContactFilters = {
  page: number
  pageSize: number
  search: string
  status: string
  source: string
  assignedTo: string
}

export type CampaignFilters = {
  page: number
  pageSize: number
  search: string
  status: string
  channel: string
  campaignType: string
  startDate: string
  endDate: string
}

export type LeadFilters = {
  page: number
  pageSize: number
  search: string
  status: string
  source: string
  priority: string
  campaignId: string
  assignedTo: string
  createdFrom: string
  createdTo: string
}

export type MessageFilters = {
  page: number
  pageSize: number
  search: string
  messageType: string
  status: string
  contactId: string
}

export type LeadMetricFilters = {
  dateFrom: string
  dateTo: string
  status: string
}

export type SalesMetricFilters = {
  dateFrom: string
  dateTo: string
  pipelineId: string
  stageId: string
  assignedTo: string
  source: string
  campaignId: string
}

export type PipelineBoardFilters = {
  search: string
  source: string
  campaignId: string
  assignedTo: string
  closeFrom: string
  closeTo: string
}

export const queryKeys = {
  currentUser: ["auth", "me"] as const,
  availableCompanies: ["companies", "available"] as const,
  adminCompanies: (filters: CompanyListFilters) => ["admin-companies", filters] as const,
  adminCompany: (companyId: string) => ["admin-company", companyId] as const,
  organisationCompanies: (organisationId: string) =>
    ["organisation-companies", organisationId] as const,
  tenantOrganisationCompanies: (organisationId: string) =>
    ["tenant-organisation-companies", organisationId] as const,
  companyUsers: (companyId: string, filters: ListFilters) =>
    ["company-users", companyId, filters] as const,
  adminUsers: (filters: ListFilters) => ["admin-users", filters] as const,
  contacts: (companyId: string, filters: ContactFilters) =>
    ["contacts", companyId, filters] as const,
  contact: (companyId: string, contactId: string) => ["contact", companyId, contactId] as const,
  contactAssignees: (companyId: string) => ["contact-assignees", companyId] as const,
  messages: (companyId: string, filters: MessageFilters) =>
    ["messages", companyId, filters] as const,
  message: (companyId: string, messageId: string) => ["message", companyId, messageId] as const,
  contactMessages: (companyId: string, contactId: string, filters: MessageFilters) =>
    ["contact-messages", companyId, contactId, filters] as const,
  marketingCampaigns: (companyId: string, filters: CampaignFilters) =>
    ["marketing-campaigns", companyId, filters] as const,
  marketingCampaign: (companyId: string, campaignId: string) =>
    ["marketing-campaign", companyId, campaignId] as const,
  marketingSummary: (companyId: string) => ["marketing-summary", companyId] as const,
  leads: (companyId: string, filters: LeadFilters) => ["leads", companyId, filters] as const,
  lead: (companyId: string, leadId: string) => ["lead", companyId, leadId] as const,
  campaignLeads: (companyId: string, campaignId: string, filters: LeadFilters) =>
    ["campaign-leads", companyId, campaignId, filters] as const,
  leadMetrics: (companyId: string, filters: LeadMetricFilters) =>
    ["lead-metrics", companyId, filters] as const,
  leadMetricsTypes: (companyId: string) => ["lead-metrics-types", companyId] as const,
  salesMetrics: (companyId: string, filters: SalesMetricFilters) =>
    ["sales-metrics", companyId, filters] as const,
  salesPipelines: (companyId: string) => ["sales-pipelines", companyId] as const,
  salesPipeline: (companyId: string, pipelineId: string) =>
    ["sales-pipeline", companyId, pipelineId] as const,
  salesPipelineStages: (companyId: string, pipelineId: string) =>
    ["sales-pipeline-stages", companyId, pipelineId] as const,
  salesPipelineBoard: (companyId: string, pipelineId: string, filters: PipelineBoardFilters) =>
    ["sales-pipeline-board", companyId, pipelineId, filters] as const,
}
