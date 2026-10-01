import { Link, useNavigate, useParams } from "react-router-dom"
import { ApiError } from "../../api/client.ts"
import { canManageMarketing } from "../../auth/permissions.ts"
import { EmptyState } from "../../components/common/EmptyState.tsx"
import { ErrorState } from "../../components/common/ErrorState.tsx"
import { LoadingState } from "../../components/common/LoadingState.tsx"
import { useCreateLead, useLead, useUpdateLead } from "../../hooks/useMarketing.ts"
import { useSession } from "../../hooks/useSession.ts"
import { LeadForm } from "./LeadForm.tsx"

export function LeadFormPage() {
  const { leadId = "" } = useParams()
  const navigate = useNavigate()
  const session = useSession()
  const companyId = session.activeCompany?.id ?? null
  const editing = Boolean(leadId)
  const canManage = canManageMarketing(session.navRole)
  const leadQuery = useLead(canManage && editing ? companyId : null, leadId)
  const createLead = useCreateLead(companyId ?? "")
  const updateLead = useUpdateLead(companyId ?? "", leadId)

  if (!companyId) {
    return <EmptyState title="No company selected" message="Choose a company before editing leads." />
  }
  if (!canManage) {
    return (
      <EmptyState title="Leads are unavailable" message="Your role cannot change leads." />
    )
  }
  if (editing && leadQuery.isPending) {
    return <LoadingState label="Loading lead" />
  }
  if (editing && (leadQuery.isError || !leadQuery.data)) {
    return (
      <ErrorState
        message={leadQuery.error instanceof ApiError ? leadQuery.error.message : "Lead could not be loaded."}
      />
    )
  }

  const pending = createLead.isPending || updateLead.isPending
  const error = editing ? updateLead.error : createLead.error

  return (
    <section className="mx-auto max-w-3xl">
      <Link
        to={editing ? `/leads/${leadId}` : "/leads"}
        className="text-sm font-semibold text-pine underline"
      >
        {editing ? "Back to lead" : "Back to leads"}
      </Link>
      <h1 className="mt-3 font-display text-4xl">{editing ? "Edit lead" : "Add lead"}</h1>
      <p className="mt-2 text-pine">Saved for {session.activeCompany?.name}.</p>
      <LeadForm
        organisationId={companyId}
        lead={leadQuery.data}
        pending={pending}
        error={error}
        onSubmit={async (body) => {
          if (editing) {
            await updateLead.mutateAsync(body)
            void navigate(`/leads/${leadId}`, { state: { notice: "Lead saved." } })
            return
          }
          const created = await createLead.mutateAsync(body)
          void navigate(`/leads/${created.id}`, { state: { notice: "Lead added." } })
        }}
      />
    </section>
  )
}
