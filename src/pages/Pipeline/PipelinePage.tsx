import { useEffect, useMemo, useState } from "react"
import { Link } from "react-router-dom"
import { useQueryClient } from "@tanstack/react-query"
import { ApiError } from "../../api/client.ts"
import { updateLead } from "../../api/marketing.ts"
import { createPipeline, createStage, fetchStages, fetchStageLeads } from "../../api/pipeline.ts"
import type { LeadFilters, PipelineBoardFilters } from "../../api/query-keys.ts"
import { canManagePipeline } from "../../auth/permissions.ts"
import { EmptyState } from "../../components/common/EmptyState.tsx"
import { ErrorState } from "../../components/common/ErrorState.tsx"
import { fieldClass } from "../../components/common/Field.tsx"
import { LoadingState } from "../../components/common/LoadingState.tsx"
import { useTenantOrganisationCompanies } from "../../hooks/useManagement.ts"
import { useLead, useLeads } from "../../hooks/useMarketing.ts"
import {
  useMoveLeadStage,
  useSalesPipelineBoard,
  useSalesPipelines,
  useUpdatePipeline,
} from "../../hooks/usePipeline.ts"
import { useSession } from "../../hooks/useSession.ts"
import { formatCalendarDate, roleLabel } from "../../lib/utils.ts"
import type {
  PipelineBoard,
  PipelineCard,
  PipelineStatus,
  PreferredContactType,
  StageColor,
} from "../../types/pipeline.ts"
import {
  PIPELINE_STATUSES,
  PREFERRED_CONTACT_LABELS,
  PREFERRED_CONTACT_TYPES,
} from "../../types/pipeline.ts"

const EMPTY_FILTERS: PipelineBoardFilters = {
  search: "",
  source: "",
  campaignId: "",
  assignedTo: "",
  closeFrom: "",
  closeTo: "",
}

const LEAD_OPTIONS: LeadFilters = {
  page: 1,
  pageSize: 100,
  search: "",
  status: "",
  source: "",
  priority: "",
  campaignId: "",
  assignedTo: "",
  createdFrom: "",
  createdTo: "",
}

const DEFAULT_STAGES = [
  { name: "New", color: "copper" as const },
  { name: "Qualified", color: "pine" as const },
  { name: "Won", color: "moss" as const },
]

const COLOR_CLASS: Record<StageColor, string> = {
  copper: "bg-copper",
  pine: "bg-pine",
  moss: "bg-moss",
  ink: "bg-ink",
  danger: "bg-danger",
}

export function PipelinePage() {
  const session = useSession()
  const companyId = session.activeCompany?.id ?? null
  const canConfigure = canManagePipeline(session.navRole)
  const pipelinesQuery = useSalesPipelines(companyId)
  const [pipelineId, setPipelineId] = useState("")
  const selectedId = pipelineId || pipelinesQuery.data?.items[0]?.id || ""
  const boardQuery = useSalesPipelineBoard(companyId, selectedId, EMPTY_FILTERS)

  if (!companyId) {
    return <EmptyState title="No company selected" message="Choose a company to view the pipeline." />
  }

  return (
    <section>
      <div>
        <p className="text-sm font-semibold tracking-[0.12em] text-copper uppercase">Sales Activity</p>
        <h1 className="mt-2 font-display text-4xl">Sales Pipeline</h1>
      </div>
      {pipelinesQuery.isPending ? <LoadingState label="Loading pipeline..." /> : null}
      {pipelinesQuery.isError ? (
        <ErrorState title="Unable to load pipeline." message="Unable to load pipeline." />
      ) : null}
      {pipelinesQuery.data ? (
        <>
          {pipelinesQuery.data.items.length > 1 ? (
            <label className="mt-6 block max-w-sm text-sm font-semibold">
              Pipeline
              <select
                className={fieldClass}
                value={selectedId}
                onChange={(event) => setPipelineId(event.target.value)}
              >
                {pipelinesQuery.data.items.map((pipeline) => (
                  <option key={pipeline.id} value={pipeline.id}>
                    {pipeline.name}
                  </option>
                ))}
              </select>
            </label>
          ) : null}
          <PipelineEntryForm
            companyId={companyId}
            pipelineId={selectedId}
            canConfigure={canConfigure}
            onPipelineReady={(id) => setPipelineId(id)}
          />
          <div className="mt-6">
            {selectedId ? (
              <>
                {boardQuery.isPending ? <LoadingState label="Loading pipeline..." /> : null}
                {boardQuery.isError ? (
                  <ErrorState
                    title="Unable to load pipeline."
                    message={
                      boardQuery.error instanceof ApiError
                        ? boardQuery.error.message
                        : "Unable to load pipeline."
                    }
                  />
                ) : null}
                {boardQuery.data ? (
                  <Board
                    key={selectedId}
                    companyId={companyId}
                    filters={EMPTY_FILTERS}
                    board={boardQuery.data}
                  />
                ) : null}
              </>
            ) : null}
          </div>
        </>
      ) : null}
    </section>
  )
}

function Board({
  companyId,
  filters,
  board,
}: {
  companyId: string
  filters: PipelineBoardFilters
  board: PipelineBoard
}) {
  const moveLead = useMoveLeadStage(companyId)
  const [extra, setExtra] = useState<Record<string, PipelineCard[]>>({})
  const [loadingStage, setLoadingStage] = useState("")
  const [moveError, setMoveError] = useState("")

  async function moveCard(leadId: string, fromStageId: string, toStageId: string) {
    if (fromStageId === toStageId) {
      return
    }
    setMoveError("")
    try {
      await moveLead.mutateAsync({
        leadId,
        pipelineId: board.pipeline_id,
        stageId: toStageId,
        expectedStageId: fromStageId,
      })
    } catch (error) {
      setMoveError(error instanceof ApiError ? error.message : "Unable to move this lead.")
    }
  }

  async function viewMore(stageId: string, shown: number) {
    setLoadingStage(stageId)
    try {
      const page = await fetchStageLeads(
        companyId,
        board.pipeline_id,
        stageId,
        Math.floor(shown / board.per_stage) + 1,
        filters,
      )
      setExtra((current) => ({
        ...current,
        [stageId]: [...(current[stageId] ?? []), ...page.items],
      }))
    } catch (error) {
      setMoveError(error instanceof ApiError ? error.message : "Unable to load more leads.")
    } finally {
      setLoadingStage("")
    }
  }

  if (board.stages.length === 0) {
    return (
      <EmptyState
        title="No stages configured."
        message="Add an active stage in pipeline settings before placing leads."
      />
    )
  }

  return (
    <div>
      {moveError ? <p className="mb-3 text-sm text-danger">{moveError}</p> : null}
      <nav className="mb-3 flex gap-2 overflow-x-auto md:hidden" aria-label="Pipeline stages">
        {board.stages.map((stage) => (
          <a
            key={stage.stage_id}
            href={`#stage-${stage.stage_id}`}
            className="shrink-0 rounded-md border border-line bg-paper px-3 py-1 text-sm font-semibold"
          >
            {stage.stage_name}
          </a>
        ))}
      </nav>
      <div className="flex gap-4 overflow-x-auto pb-4">
        {board.stages.map((stage) => {
          const cards = [...stage.leads, ...(extra[stage.stage_id] ?? [])]
          return (
            <section
              key={stage.stage_id}
              id={`stage-${stage.stage_id}`}
              className="w-72 shrink-0 rounded-lg border border-line bg-cream p-3"
              onDragOver={(event) => event.preventDefault()}
              onDrop={(event) => {
                event.preventDefault()
                const raw = event.dataTransfer.getData("text/plain")
                if (!raw) {
                  return
                }
                let payload: { leadId?: string; stageId?: string }
                try {
                  payload = JSON.parse(raw) as { leadId?: string; stageId?: string }
                } catch {
                  return
                }
                if (!payload.leadId || !payload.stageId) {
                  return
                }
                void moveCard(payload.leadId, payload.stageId, stage.stage_id)
              }}
            >
              <div className={`mb-2 h-1 rounded ${COLOR_CLASS[stage.color]}`} />
              <h2 className="font-display text-xl">{stage.stage_name}</h2>
              <p className="text-sm text-pine">
                {stage.lead_count} leads · {stage.estimated_value_total}
              </p>
              <ul className="mt-3 space-y-3">
                {cards.length === 0 ? (
                  <li className="text-sm text-pine">No leads in this stage.</li>
                ) : null}
                {cards.map((card) => (
                  <li key={card.id}>
                    <article
                      draggable
                      className="rounded-md border border-line bg-paper p-3"
                      onDragStart={(event) => {
                        event.dataTransfer.setData(
                          "text/plain",
                          JSON.stringify({ leadId: card.id, stageId: card.pipeline_stage_id }),
                        )
                        event.dataTransfer.effectAllowed = "move"
                      }}
                    >
                      <Link to={`/leads/${card.id}`} className="font-semibold underline">
                        {card.title}
                      </Link>
                      <p className="mt-1 text-sm">{card.contact_name || "No contact"}</p>
                      <p className="text-sm text-pine">
                        {card.preferred_contact_type
                          ? PREFERRED_CONTACT_LABELS[card.preferred_contact_type]
                          : "No preferred contact"}
                      </p>
                      <p className="text-sm text-pine">{formatCreatedAt(card.pipeline_created_at)}</p>
                      <p className="text-sm text-pine">
                        {card.estimated_value || "—"} · {roleLabel(card.source)}
                      </p>
                      <p className="text-sm text-pine">
                        {card.assignee_name || "Unassigned"} ·{" "}
                        {formatCalendarDate(card.expected_close_date)}
                      </p>
                      <label className="mt-2 block text-xs font-semibold" htmlFor={`move-${card.id}`}>
                        Move to stage
                        <select
                          id={`move-${card.id}`}
                          className={fieldClass}
                          value={card.pipeline_stage_id}
                          onChange={(event) => {
                            void moveCard(card.id, card.pipeline_stage_id, event.target.value)
                          }}
                        >
                          {board.stages.map((option) => (
                            <option key={option.stage_id} value={option.stage_id}>
                              {option.stage_name}
                            </option>
                          ))}
                        </select>
                      </label>
                    </article>
                  </li>
                ))}
              </ul>
              {stage.has_more && cards.length < stage.lead_count ? (
                <button
                  type="button"
                  className="mt-3 text-sm font-semibold underline"
                  disabled={loadingStage === stage.stage_id}
                  onClick={() => {
                    void viewMore(stage.stage_id, cards.length)
                  }}
                >
                  View more
                </button>
              ) : null}
            </section>
          )
        })}
      </div>
    </div>
  )
}

function PipelineEntryForm({
  companyId,
  pipelineId,
  canConfigure,
  onPipelineReady,
}: {
  companyId: string
  pipelineId: string
  canConfigure: boolean
  onPipelineReady: (pipelineId: string) => void
}) {
  const queryClient = useQueryClient()
  const pipelinesQuery = useSalesPipelines(companyId)
  const leadsQuery = useLeads(companyId, LEAD_OPTIONS)
  const companiesQuery = useTenantOrganisationCompanies(companyId)
  const updatePipeline = useUpdatePipeline(companyId, pipelineId || "pending")
  const moveLead = useMoveLeadStage(companyId)
  const selectedPipeline = pipelinesQuery.data?.items.find((item) => item.id === pipelineId)
  const [status, setStatus] = useState<PipelineStatus>(selectedPipeline?.status ?? "active")
  const [leadId, setLeadId] = useState("")
  const [companyName, setCompanyName] = useState("")
  const [contactType, setContactType] = useState<PreferredContactType | "">("")
  const [createdAt, setCreatedAt] = useState("")
  const [message, setMessage] = useState("")
  const [error, setError] = useState("")
  const [pending, setPending] = useState(false)
  const leadQuery = useLead(companyId, leadId)
  const companyOptions = useMemo(() => {
    const names = (companiesQuery.data ?? []).map((company) => company.name)
    if (companyName && !names.includes(companyName)) {
      return [companyName, ...names]
    }
    return names
  }, [companiesQuery.data, companyName])

  useEffect(() => {
    if (selectedPipeline) {
      setStatus(selectedPipeline.status)
    }
  }, [selectedPipeline])

  useEffect(() => {
    if (!leadQuery.data) {
      return
    }
    setCompanyName(leadQuery.data.company_name || leadQuery.data.title || "")
    setContactType(leadQuery.data.preferred_contact_type ?? "")
    setCreatedAt(toDateTimeLocal(leadQuery.data.pipeline_created_at))
  }, [leadQuery.data])

  return (
    <form
      className="mt-6 grid gap-4 sm:grid-cols-2"
      onSubmit={(event) => {
        event.preventDefault()
        setMessage("")
        setError("")
        if (!leadId) {
          setError("Choose a lead.")
          return
        }
        if (!companyName.trim()) {
          setError("Choose a company.")
          return
        }
        if (!contactType) {
          setError("Choose a preferred contact type.")
          return
        }
        if (!createdAt) {
          setError("Enter the pipeline created date and time.")
          return
        }
        void (async () => {
          setPending(true)
          try {
            let activePipelineId = pipelineId
            let stages = activePipelineId ? await fetchStages(companyId, activePipelineId) : []

            if (!activePipelineId) {
              if (!canConfigure) {
                setError("A pipeline has not been set up for this company yet.")
                return
              }
              const pipeline = await createPipeline(companyId, {
                name: "Sales Pipeline",
                description: null,
                status,
              })
              activePipelineId = pipeline.id
              for (const stage of DEFAULT_STAGES) {
                await createStage(companyId, activePipelineId, {
                  name: stage.name,
                  description: null,
                  color: stage.color,
                })
              }
              stages = await fetchStages(companyId, activePipelineId)
              onPipelineReady(activePipelineId)
              await queryClient.invalidateQueries({ queryKey: ["sales-pipelines", companyId] })
            } else if (canConfigure && selectedPipeline && status !== selectedPipeline.status) {
              await updatePipeline.mutateAsync({ status })
            }

            const updated = await updateLead(companyId, leadId, {
              company_name: companyName.trim(),
              preferred_contact_type: contactType,
              pipeline_created_at: createdAt,
            })
            if (updated.pipeline_id !== activePipelineId) {
              const stage = stages.find((item) => item.status === "active") ?? stages[0]
              if (!stage) {
                setError("No pipeline stage is available yet.")
                return
              }
              await moveLead.mutateAsync({
                leadId,
                pipelineId: activePipelineId,
                stageId: stage.id,
                expectedStageId: updated.pipeline_stage_id,
              })
            }
            await queryClient.invalidateQueries({ queryKey: ["lead", companyId, leadId] })
            await queryClient.invalidateQueries({ queryKey: ["sales-pipeline-board", companyId] })
            await queryClient.invalidateQueries({ queryKey: ["leads", companyId] })
            setMessage("Pipeline details saved.")
          } catch (saveError) {
            setError(
              saveError instanceof ApiError
                ? saveError.message
                : "The pipeline details could not be saved.",
            )
          } finally {
            setPending(false)
          }
        })()
      }}
    >
      <label className="text-sm font-semibold" htmlFor="pipeline-status">
        Pipeline status
        <select
          id="pipeline-status"
          className={fieldClass}
          value={status}
          disabled={!canConfigure}
          onChange={(event) => setStatus(event.target.value as PipelineStatus)}
        >
          {PIPELINE_STATUSES.map((item) => (
            <option key={item} value={item}>
              {roleLabel(item)}
            </option>
          ))}
        </select>
      </label>
      <label className="text-sm font-semibold" htmlFor="pipeline-lead">
        Leads
        <select
          id="pipeline-lead"
          className={fieldClass}
          value={leadId}
          onChange={(event) => setLeadId(event.target.value)}
        >
          <option value="">Choose a lead</option>
          {(leadsQuery.data?.items ?? []).map((lead) => (
            <option key={lead.id} value={lead.id}>
              {lead.company_name || lead.title}
            </option>
          ))}
        </select>
      </label>
      <label className="text-sm font-semibold" htmlFor="pipeline-company-name">
        Company name
        <select
          id="pipeline-company-name"
          className={fieldClass}
          value={companyName}
          disabled={companiesQuery.isPending || (companyOptions.length === 0 && !companyName)}
          onChange={(event) => setCompanyName(event.target.value)}
        >
          <option value="">Select a company</option>
          {companyOptions.map((name) => (
            <option key={name} value={name}>
              {name}
            </option>
          ))}
        </select>
        {companiesQuery.isError ? (
          <span className="mt-1 block text-sm font-normal text-danger">
            {companiesQuery.error instanceof ApiError
              ? companiesQuery.error.message
              : "Companies could not be loaded."}
          </span>
        ) : null}
        {!companiesQuery.isPending &&
        !companiesQuery.isError &&
        (companiesQuery.data?.length ?? 0) === 0 ? (
          <span className="mt-1 block text-sm font-normal text-pine">
            No companies under this organisation yet. Add one from Organisations.
          </span>
        ) : null}
      </label>
      <label className="text-sm font-semibold" htmlFor="preferred-contact">
        Preferred contact type
        <select
          id="preferred-contact"
          className={fieldClass}
          value={contactType}
          onChange={(event) => setContactType(event.target.value as PreferredContactType | "")}
        >
          <option value="">Choose a contact type</option>
          {PREFERRED_CONTACT_TYPES.map((item) => (
            <option key={item} value={item}>
              {PREFERRED_CONTACT_LABELS[item]}
            </option>
          ))}
        </select>
      </label>
      <label className="text-sm font-semibold" htmlFor="pipeline-created">
        Pipeline created date and time
        <input
          id="pipeline-created"
          type="datetime-local"
          className={fieldClass}
          value={createdAt}
          onChange={(event) => setCreatedAt(event.target.value)}
        />
      </label>
      {error ? <p className="text-sm text-danger sm:col-span-2">{error}</p> : null}
      {message ? <p className="text-sm text-pine sm:col-span-2">{message}</p> : null}
      <div className="sm:col-span-2">
        <button
          type="submit"
          className="w-fit rounded-md bg-copper px-4 py-2 font-semibold text-paper disabled:opacity-60"
          disabled={pending || updatePipeline.isPending || moveLead.isPending}
        >
          {pending || updatePipeline.isPending || moveLead.isPending ? "Saving…" : "Save"}
        </button>
      </div>
    </form>
  )
}

function toDateTimeLocal(value: string | null): string {
  if (!value) {
    return ""
  }
  const match = /^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2})/.exec(value)
  return match?.[1] ?? ""
}

function formatCreatedAt(value: string | null): string {
  const local = toDateTimeLocal(value)
  if (!local) {
    return "—"
  }
  const [datePart, timePart] = local.split("T")
  const date = new Date(`${datePart}T${timePart}`)
  if (Number.isNaN(date.getTime())) {
    return local.replace("T", " ")
  }
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(date)
}
