import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import {
  createPipeline,
  createStage,
  fetchPipeline,
  fetchPipelineBoard,
  fetchPipelines,
  fetchStages,
  moveLeadStage,
  reorderStages,
  updatePipeline,
  updateStage,
} from "../api/pipeline.ts"
import { queryKeys, type PipelineBoardFilters } from "../api/query-keys.ts"
import type { PipelineWrite, StageWrite } from "../types/pipeline.ts"

function invalidatePipeline(
  queryClient: ReturnType<typeof useQueryClient>,
  companyId: string,
  pipelineId?: string,
) {
  void queryClient.invalidateQueries({ queryKey: ["sales-pipelines", companyId] })
  void queryClient.invalidateQueries({ queryKey: ["sales-pipeline-board", companyId] })
  if (pipelineId) {
    void queryClient.invalidateQueries({ queryKey: ["sales-pipeline", companyId, pipelineId] })
    void queryClient.invalidateQueries({
      queryKey: ["sales-pipeline-stages", companyId, pipelineId],
    })
  }
}

function invalidateLeadMovement(
  queryClient: ReturnType<typeof useQueryClient>,
  companyId: string,
  leadId: string,
) {
  void queryClient.invalidateQueries({ queryKey: ["sales-pipeline-board", companyId] })
  void queryClient.invalidateQueries({ queryKey: ["lead", companyId, leadId] })
  void queryClient.invalidateQueries({ queryKey: ["leads", companyId] })
  void queryClient.invalidateQueries({ queryKey: ["lead-metrics", companyId] })
  void queryClient.invalidateQueries({ queryKey: ["sales-metrics", companyId] })
}

export function useSalesPipelines(companyId: string | null) {
  return useQuery({
    queryKey: queryKeys.salesPipelines(companyId ?? ""),
    queryFn: () => fetchPipelines(companyId ?? ""),
    enabled: Boolean(companyId),
  })
}

export function useSalesPipeline(companyId: string | null, pipelineId: string) {
  return useQuery({
    queryKey: queryKeys.salesPipeline(companyId ?? "", pipelineId),
    queryFn: () => fetchPipeline(companyId ?? "", pipelineId),
    enabled: Boolean(companyId) && Boolean(pipelineId),
  })
}

export function useSalesPipelineStages(companyId: string | null, pipelineId: string) {
  return useQuery({
    queryKey: queryKeys.salesPipelineStages(companyId ?? "", pipelineId),
    queryFn: () => fetchStages(companyId ?? "", pipelineId),
    enabled: Boolean(companyId) && Boolean(pipelineId),
  })
}

export function useSalesPipelineBoard(
  companyId: string | null,
  pipelineId: string,
  filters: PipelineBoardFilters,
) {
  return useQuery({
    queryKey: queryKeys.salesPipelineBoard(companyId ?? "", pipelineId, filters),
    queryFn: () => fetchPipelineBoard(companyId ?? "", pipelineId, filters),
    enabled: Boolean(companyId) && Boolean(pipelineId),
  })
}

export function useCreatePipeline(companyId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: PipelineWrite) => createPipeline(companyId, body),
    onSuccess: (pipeline) => {
      invalidatePipeline(queryClient, companyId, pipeline.id)
    },
  })
}

export function useUpdatePipeline(companyId: string, pipelineId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: Partial<PipelineWrite>) => updatePipeline(companyId, pipelineId, body),
    onSuccess: () => {
      invalidatePipeline(queryClient, companyId, pipelineId)
    },
  })
}

export function useCreateStage(companyId: string, pipelineId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: StageWrite) => createStage(companyId, pipelineId, body),
    onSuccess: () => {
      invalidatePipeline(queryClient, companyId, pipelineId)
    },
  })
}

export function useUpdateStage(companyId: string, pipelineId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (input: { stageId: string; body: Partial<StageWrite> }) =>
      updateStage(companyId, pipelineId, input.stageId, input.body),
    onSuccess: () => {
      invalidatePipeline(queryClient, companyId, pipelineId)
    },
  })
}

export function useReorderStages(companyId: string, pipelineId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (stageIds: string[]) => reorderStages(companyId, pipelineId, stageIds),
    onSuccess: () => {
      invalidatePipeline(queryClient, companyId, pipelineId)
    },
  })
}

export function useMoveLeadStage(companyId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (input: {
      leadId: string
      pipelineId: string
      stageId: string
      expectedStageId: string | null
    }) =>
      moveLeadStage(companyId, input.leadId, {
        pipeline_id: input.pipelineId,
        pipeline_stage_id: input.stageId,
        expected_pipeline_stage_id: input.expectedStageId,
      }),
    onSuccess: (lead) => {
      invalidateLeadMovement(queryClient, companyId, lead.id)
    },
  })
}
