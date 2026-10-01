import { useState } from "react"
import { Link } from "react-router-dom"
import { ApiError } from "../../api/client.ts"
import { canManageMarketing } from "../../auth/permissions.ts"
import { EmptyState } from "../../components/common/EmptyState.tsx"
import { ErrorState } from "../../components/common/ErrorState.tsx"
import { LoadingState } from "../../components/common/LoadingState.tsx"
import { Pagination } from "../../components/common/Pagination.tsx"
import { useCreateLead, useLeads } from "../../hooks/useMarketing.ts"
import { usePagedFilters } from "../../hooks/usePagedFilters.ts"
import { useSession } from "../../hooks/useSession.ts"
import { displayUsPhone } from "../../lib/utils.ts"
import type { LeadListItem } from "../../types/marketing.ts"
import { LeadForm, businessTypeLabel } from "./LeadForm.tsx"

const PAGE_SIZE = 20

export function LeadsPage() {
  const session = useSession()
  const companyId = session.activeCompany?.id ?? null
  const canManage = canManageMarketing(session.navRole)
  const [formKey, setFormKey] = useState(0)
  const [saveError, setSaveError] = useState<Error | null>(null)
  const createLead = useCreateLead(companyId ?? "")
  const filters = usePagedFilters(companyId ?? "")
  const leadsQuery = useLeads(companyId, {
    page: filters.page,
    pageSize: PAGE_SIZE,
    search: "",
    status: "",
    source: "",
    priority: "",
    campaignId: "",
    assignedTo: "",
    createdFrom: "",
    createdTo: "",
  })

  return (
    <section>
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-sm font-semibold tracking-[0.12em] text-copper uppercase">Marketing</p>
          <h1 className="mt-2 font-display text-4xl">Leads</h1>
          <p className="mt-2 text-pine">
            Leads for {session.activeCompany?.name ?? "the selected company"}.
          </p>
        </div>
      </div>
      {canManage ? (
        <LeadForm
          key={formKey}
          organisationId={companyId}
          pending={createLead.isPending}
          error={companyId ? createLead.error : saveError}
          onSubmit={async (body) => {
            if (!companyId) {
              setSaveError(new Error("Choose a company in the header before saving a lead."))
              return
            }
            setSaveError(null)
            await createLead.mutateAsync(body)
            setFormKey((current) => current + 1)
          }}
        />
      ) : null}
      {!companyId ? (
        <p className="mt-3 text-sm text-pine">Choose a company in the header before saving a lead.</p>
      ) : null}
      {!companyId ? (
        <div className="mt-6">
          <EmptyState title="No company selected" message="Choose a company in the header to see its leads." />
        </div>
      ) : (
        <LeadResults
          isPending={leadsQuery.isPending}
          isError={leadsQuery.isError}
          error={leadsQuery.error}
          items={leadsQuery.data?.items}
          total={leadsQuery.data?.total ?? 0}
          page={leadsQuery.data?.page ?? filters.page}
          totalPages={leadsQuery.data?.total_pages ?? 0}
          onPage={filters.setPage}
        />
      )}
    </section>
  )
}

function LeadResults({
  isPending,
  isError,
  error,
  items,
  total,
  page,
  totalPages,
  onPage,
}: {
  isPending: boolean
  isError: boolean
  error: unknown
  items: LeadListItem[] | undefined
  total: number
  page: number
  totalPages: number
  onPage: (page: number) => void
}) {
  if (isPending) {
    return <LoadingState label="Loading leads" />
  }
  if (isError) {
    return (
      <div className="mt-6">
        <ErrorState message={error instanceof ApiError ? error.message : "Leads could not be loaded."} />
      </div>
    )
  }
  if (!items || items.length === 0) {
    return (
      <div className="mt-6">
        <EmptyState
          title="No leads found."
          message="Add a lead to start tracking interest for this company."
        />
      </div>
    )
  }

  return (
    <div className="mt-6">
      <p className="text-sm text-pine">{total} leads</p>
      <div className="mt-3 hidden overflow-x-auto rounded-lg border border-line bg-paper md:block">
        <table className="w-full text-left text-sm">
          <caption className="sr-only">Leads</caption>
          <thead className="border-b border-line text-moss">
            <tr>
              <th scope="col" className="px-4 py-3 font-semibold">Company Name</th>
              <th scope="col" className="px-4 py-3 font-semibold">Business Type</th>
              <th scope="col" className="px-4 py-3 font-semibold">Address</th>
              <th scope="col" className="px-4 py-3 font-semibold">Phone Number</th>
              <th scope="col" className="px-4 py-3 font-semibold">Main Contact person Name</th>
              <th scope="col" className="px-4 py-3 font-semibold">Email</th>
              <th scope="col" className="px-4 py-3 font-semibold">Phone Number</th>
              <th scope="col" className="px-4 py-3 font-semibold">Comments</th>
            </tr>
          </thead>
          <tbody>
            {items.map((lead) => (
              <tr key={lead.id} className="border-t border-line">
                <td className="px-4 py-3 font-semibold">
                  <Link to={`/leads/${lead.id}`} className="underline">
                    {lead.company_name || lead.title}
                  </Link>
                </td>
                <td className="px-4 py-3">{businessTypeLabel(lead.business_type)}</td>
                <td className="px-4 py-3">{lead.address || "—"}</td>
                <td className="px-4 py-3">{displayUsPhone(lead.phone_number) || "—"}</td>
                <td className="px-4 py-3">{lead.main_contact_name || "—"}</td>
                <td className="px-4 py-3">{lead.email || "—"}</td>
                <td className="px-4 py-3">{displayUsPhone(lead.phone_number_2) || "—"}</td>
                <td className="px-4 py-3">{lead.comments || "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <ul className="mt-3 space-y-3 md:hidden">
        {items.map((lead) => (
          <li key={lead.id} className="rounded-lg border border-line bg-paper p-4">
            <Link to={`/leads/${lead.id}`} className="font-semibold underline">
              {lead.company_name || lead.title}
            </Link>
            <p className="mt-1 text-sm">{businessTypeLabel(lead.business_type)}</p>
            <p className="mt-1 text-sm">{displayUsPhone(lead.phone_number) || lead.email || "No contact details"}</p>
          </li>
        ))}
      </ul>
      <Pagination page={page} totalPages={totalPages} onPage={onPage} />
    </div>
  )
}
