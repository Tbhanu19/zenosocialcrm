import { useState } from "react"
import { Link, useLocation, useParams } from "react-router-dom"
import { ApiError } from "../../api/client.ts"
import { canManageMarketing } from "../../auth/permissions.ts"
import { Dialog } from "../../components/common/Dialog.tsx"
import { EmptyState } from "../../components/common/EmptyState.tsx"
import { ErrorState } from "../../components/common/ErrorState.tsx"
import { LoadingState } from "../../components/common/LoadingState.tsx"
import { useLead, useUpdateLead } from "../../hooks/useMarketing.ts"
import { useMoveLeadStage, useSalesPipeline, useSalesPipelines } from "../../hooks/usePipeline.ts"
import { useSession } from "../../hooks/useSession.ts"
import { displayUsPhone, formatDate } from "../../lib/utils.ts"
import { businessTypeLabel } from "./LeadForm.tsx"

export function LeadDetailPage() {
  const { leadId = "" } = useParams()
  const location = useLocation()
  const session = useSession()
  const companyId = session.activeCompany?.id ?? null
  const canManage = canManageMarketing(session.navRole)
  const leadQuery = useLead(companyId, leadId)
  const updateLead = useUpdateLead(companyId ?? "", leadId)
  const [confirmArchive, setConfirmArchive] = useState(false)
  const notice = readNotice(location.state)

  if (!companyId) {
    return <EmptyState title="No company selected" message="Choose a company to view this lead." />
  }
  if (leadQuery.isPending) {
    return <LoadingState label="Loading lead" />
  }
  if (leadQuery.isError || !leadQuery.data) {
    return (
      <ErrorState
        message={leadQuery.error instanceof ApiError ? leadQuery.error.message : "Lead could not be loaded."}
      />
    )
  }

  const lead = leadQuery.data
  const archived = lead.status === "archived"

  return (
    <section className="mx-auto max-w-3xl">
      <Link to="/leads" className="text-sm font-semibold text-pine underline">
        Back to leads
      </Link>
      {notice ? <p className="mt-4 rounded-md bg-paper px-4 py-3 text-sm">{notice}</p> : null}
      <div className="mt-3 flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-sm font-semibold tracking-[0.12em] text-copper uppercase">Lead</p>
          <h1 className="mt-2 font-display text-4xl">{lead.company_name || lead.title}</h1>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link
            to={`/leads/${lead.id}/edit`}
            className="rounded-md border border-line bg-paper px-4 py-2 font-semibold"
          >
            Edit
          </Link>
          {canManage && !archived ? (
            <button
              type="button"
              className="rounded-md border border-line bg-paper px-4 py-2 font-semibold"
              onClick={() => setConfirmArchive(true)}
            >
              Archive
            </button>
          ) : null}
          {canManage && archived ? (
            <button
              type="button"
              className="rounded-md border border-line bg-paper px-4 py-2 font-semibold disabled:opacity-60"
              disabled={updateLead.isPending}
              onClick={() => {
                void updateLead.mutateAsync({ status: "new" })
              }}
            >
              Restore
            </button>
          ) : null}
        </div>
      </div>
      <dl className="mt-6 grid gap-4 sm:grid-cols-2">
        <Info label="Company Name" value={lead.company_name || lead.title} />
        <Info label="Business Type" value={businessTypeLabel(lead.business_type)} />
        <Info label="Address" value={lead.address} />
        <Info label="Phone Number" value={displayUsPhone(lead.phone_number)} />
        <Info label="Main Contact person Name" value={lead.main_contact_name} />
        <Info label="Email" value={lead.email} />
        <Info label="Phone Number" value={displayUsPhone(lead.phone_number_2)} />
        <Info label="Comments" value={lead.comments} />
        <Info label="Created" value={formatDate(lead.created_at)} />
        <Info label="Updated" value={formatDate(lead.updated_at)} />
      </dl>
      {canManage && !archived ? (
        <PlaceOnPipeline
          key={`${lead.id}:${lead.pipeline_stage_id ?? ""}`}
          companyId={companyId}
          leadId={lead.id}
          pipelineId={lead.pipeline_id}
          stageId={lead.pipeline_stage_id}
        />
      ) : null}
      <Dialog open={confirmArchive} title="Archive lead" onClose={() => setConfirmArchive(false)}>
        <p className="text-sm text-pine">Archived leads stay in history and leave the current list.</p>
        <div className="mt-4 flex justify-end gap-3">
          <button type="button" className="rounded-md px-3 py-2" onClick={() => setConfirmArchive(false)}>
            Cancel
          </button>
          <button
            type="button"
            className="rounded-md bg-copper px-4 py-2 font-semibold text-paper disabled:opacity-60"
            disabled={updateLead.isPending}
            onClick={() => {
              void updateLead.mutateAsync({ status: "archived" }).then(() => {
                setConfirmArchive(false)
              })
            }}
          >
            Archive
          </button>
        </div>
      </Dialog>
    </section>
  )
}

function PlaceOnPipeline({
  companyId,
  leadId,
  pipelineId,
  stageId,
}: {
  companyId: string
  leadId: string
  pipelineId: string | null
  stageId: string | null
}) {
  const pipelines = useSalesPipelines(companyId)
  const [selectedPipeline, setSelectedPipeline] = useState(pipelineId ?? "")
  const [selectedStage, setSelectedStage] = useState(stageId ?? "")
  const [error, setError] = useState("")
  const pipeline = useSalesPipeline(companyId, selectedPipeline)
  const moveLead = useMoveLeadStage(companyId)
  const stages = (pipeline.data?.stages ?? []).filter((stage) => stage.status === "active")

  return (
    <form
      className="mt-6 grid gap-3 rounded-lg border border-line bg-paper p-4"
      onSubmit={(event) => {
        event.preventDefault()
        setError("")
        void moveLead
          .mutateAsync({
            leadId,
            pipelineId: selectedPipeline,
            stageId: selectedStage,
            expectedStageId: stageId,
          })
          .catch((caught: unknown) => {
            setError(caught instanceof ApiError ? caught.message : "Unable to move this lead.")
          })
      }}
    >
      <h2 className="font-display text-2xl">Pipeline stage</h2>
      <p className="text-sm text-pine">Moving a lead changes its sales stage. Lead status stays the same.</p>
      <label className="text-sm font-semibold">
        Pipeline
        <select
          className="mt-1 w-full rounded-md border border-line bg-paper px-3 py-2"
          value={selectedPipeline}
          onChange={(event) => {
            setSelectedPipeline(event.target.value)
            setSelectedStage("")
          }}
        >
          <option value="">Choose a pipeline</option>
          {(pipelines.data?.items ?? []).map((item) => (
            <option key={item.id} value={item.id}>
              {item.name}
            </option>
          ))}
        </select>
      </label>
      <label className="text-sm font-semibold">
        Stage
        <select
          className="mt-1 w-full rounded-md border border-line bg-paper px-3 py-2"
          value={selectedStage}
          onChange={(event) => setSelectedStage(event.target.value)}
        >
          <option value="">Choose a stage</option>
          {stages.map((stage) => (
            <option key={stage.id} value={stage.id}>
              {stage.name}
            </option>
          ))}
        </select>
      </label>
      <button
        type="submit"
        className="w-fit rounded-md bg-ink px-4 py-2 font-semibold text-paper disabled:opacity-60"
        disabled={!selectedPipeline || !selectedStage || moveLead.isPending}
      >
        Move lead
      </button>
      {error ? <p className="text-sm text-danger">{error}</p> : null}
    </form>
  )
}

function Info({ label, value }: { label: string; value: string | null }) {
  return (
    <div>
      <dt className="text-sm font-semibold text-moss">{label}</dt>
      <dd className="mt-1 whitespace-pre-wrap">{value || "—"}</dd>
    </div>
  )
}

function readNotice(state: unknown): string | null {
  if (typeof state !== "object" || state === null || !("notice" in state)) {
    return null
  }
  return typeof state.notice === "string" ? state.notice : null
}
