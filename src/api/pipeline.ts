import type { PipelineBoardFilters } from "./query-keys.ts"
import { apiFetch } from "./client.ts"
import type { Page } from "../types/management.ts"
import type {
  LeadPipelineResult,
  PipelineBoard,
  PipelineCard,
  PipelineListItem,
  PipelineRecord,
  PipelineWrite,
  StageRecord,
  StageWrite,
} from "../types/pipeline.ts"

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

export function fetchPipelines(companyId: string): Promise<Page<PipelineListItem>> {
  return apiFetch(
    `/api/companies/${companyId}/sales-pipelines${queryString({ page: 1, page_size: 100 })}`,
  )
}

export function fetchPipeline(companyId: string, pipelineId: string): Promise<PipelineRecord> {
  return apiFetch(`/api/companies/${companyId}/sales-pipelines/${pipelineId}`)
}

export function createPipeline(companyId: string, body: PipelineWrite): Promise<PipelineRecord> {
  return apiFetch(`/api/companies/${companyId}/sales-pipelines`, {
    method: "POST",
    body: JSON.stringify(body),
  })
}

export function updatePipeline(
  companyId: string,
  pipelineId: string,
  body: Partial<PipelineWrite>,
): Promise<PipelineRecord> {
  return apiFetch(`/api/companies/${companyId}/sales-pipelines/${pipelineId}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  })
}

export function fetchStages(companyId: string, pipelineId: string): Promise<StageRecord[]> {
  return apiFetch(`/api/companies/${companyId}/sales-pipelines/${pipelineId}/stages`)
}

export function createStage(
  companyId: string,
  pipelineId: string,
  body: StageWrite,
): Promise<StageRecord> {
  return apiFetch(`/api/companies/${companyId}/sales-pipelines/${pipelineId}/stages`, {
    method: "POST",
    body: JSON.stringify(body),
  })
}

export function updateStage(
  companyId: string,
  pipelineId: string,
  stageId: string,
  body: Partial<StageWrite>,
): Promise<StageRecord> {
  return apiFetch(`/api/companies/${companyId}/sales-pipelines/${pipelineId}/stages/${stageId}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  })
}

export function reorderStages(
  companyId: string,
  pipelineId: string,
  stageIds: string[],
): Promise<StageRecord[]> {
  return apiFetch(`/api/companies/${companyId}/sales-pipelines/${pipelineId}/stages/reorder`, {
    method: "PATCH",
    body: JSON.stringify({ stage_ids: stageIds }),
  })
}

export function fetchPipelineBoard(
  companyId: string,
  pipelineId: string,
  filters: PipelineBoardFilters,
): Promise<PipelineBoard> {
  return apiFetch(
    `/api/companies/${companyId}/sales-pipelines/${pipelineId}/board${queryString({
      per_stage: 20,
      search: filters.search,
      source: filters.source,
      campaign_id: filters.campaignId,
      assigned_to: filters.assignedTo,
      close_from: filters.closeFrom,
      close_to: filters.closeTo,
    })}`,
  )
}

export function fetchStageLeads(
  companyId: string,
  pipelineId: string,
  stageId: string,
  page: number,
  filters: PipelineBoardFilters,
): Promise<Page<PipelineCard>> {
  return apiFetch(
    `/api/companies/${companyId}/sales-pipelines/${pipelineId}/stages/${stageId}/leads${queryString({
      page,
      page_size: 20,
      search: filters.search,
      source: filters.source,
      campaign_id: filters.campaignId,
      assigned_to: filters.assignedTo,
      close_from: filters.closeFrom,
      close_to: filters.closeTo,
    })}`,
  )
}

export function moveLeadStage(
  companyId: string,
  leadId: string,
  body: {
    pipeline_id: string
    pipeline_stage_id: string
    expected_pipeline_stage_id: string | null
  },
): Promise<LeadPipelineResult> {
  return apiFetch(`/api/companies/${companyId}/leads/${leadId}/pipeline`, {
    method: "PATCH",
    body: JSON.stringify(body),
  })
}
