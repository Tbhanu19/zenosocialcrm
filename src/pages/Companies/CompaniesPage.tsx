import { useState } from "react"
import { Link } from "react-router-dom"
import { zodResolver } from "@hookform/resolvers/zod"
import { useForm } from "react-hook-form"
import { z } from "zod"
import { ApiError } from "../../api/client.ts"
import { Dialog } from "../../components/common/Dialog.tsx"
import { EmptyState } from "../../components/common/EmptyState.tsx"
import { ErrorState } from "../../components/common/ErrorState.tsx"
import { Field, fieldClass } from "../../components/common/Field.tsx"
import { LoadingState } from "../../components/common/LoadingState.tsx"
import { Pagination } from "../../components/common/Pagination.tsx"
import { UsPhoneInput } from "../../components/common/UsPhoneInput.tsx"
import { useDebouncedValue } from "../../hooks/useDebouncedValue.ts"
import {
  useAdminCompanies,
  useCreateOrganisationCompany,
  useDeleteCompany,
  useOrganisationCompanies,
} from "../../hooks/useManagement.ts"
import { usePagedFilters } from "../../hooks/usePagedFilters.ts"
import { blankToNull, displayUsPhone, isUsPhone } from "../../lib/utils.ts"
import type { AdminCompanyListItem, OrganisationCompany } from "../../types/management.ts"

const PAGE_SIZE = 20

const companySchema = z.object({
  name: z.string().trim().min(1, "Company name is required.").max(200),
  business_type: z.string().trim().min(1, "Business type is required.").max(100),
  phone: z.string().refine(isUsPhone, "Enter a US phone number, such as (214) 555-0100."),
  email: z
    .string()
    .max(320)
    .refine(
      (value) => value.trim() === "" || z.string().email().safeParse(value.trim()).success,
      "Enter a valid email.",
    ),
  status: z.enum(["active", "inactive"]),
})

type CompanyFormValues = z.infer<typeof companySchema>

const emptyCompanyForm: CompanyFormValues = {
  name: "",
  business_type: "",
  phone: "",
  email: "",
  status: "active",
}

export function CompaniesPage() {
  const [searchInput, setSearchInput] = useState("")
  const [status, setStatus] = useState("")
  const [businessTypeInput, setBusinessTypeInput] = useState("")
  const [pendingDelete, setPendingDelete] = useState<AdminCompanyListItem | null>(null)
  const [deleteError, setDeleteError] = useState("")
  const [addFor, setAddFor] = useState<AdminCompanyListItem | null>(null)
  const search = useDebouncedValue(searchInput, 400).trim()
  const businessType = useDebouncedValue(businessTypeInput, 400).trim()
  const filters = usePagedFilters(`${search}|${status}|${businessType}`)
  const companiesQuery = useAdminCompanies({
    page: filters.page,
    pageSize: PAGE_SIZE,
    search,
    status,
    businessType,
  })
  const deleteCompany = useDeleteCompany()

  return (
    <section>
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-sm font-semibold tracking-[0.12em] text-copper uppercase">Super Admin</p>
          <h1 className="mt-2 font-display text-4xl">Organisations</h1>
        </div>
        <Link
          to="/organisations/new"
          className="rounded-md bg-copper px-4 py-2 font-semibold text-paper"
        >
          Create organisation
        </Link>
      </div>
      <div className="mt-6 grid gap-3 md:grid-cols-[1fr_10rem_12rem]">
        <input
          className={fieldClass}
          value={searchInput}
          onChange={(event) => setSearchInput(event.target.value)}
          placeholder="Search organisations"
          aria-label="Search organisations"
        />
        <select
          className={fieldClass}
          value={status}
          aria-label="Status"
          onChange={(event) => setStatus(event.target.value)}
        >
          <option value="">All statuses</option>
          <option value="active">Active</option>
          <option value="inactive">Inactive</option>
        </select>
        <input
          className={fieldClass}
          value={businessTypeInput}
          onChange={(event) => setBusinessTypeInput(event.target.value)}
          placeholder="Business type"
          aria-label="Business type"
        />
      </div>
      <OrganisationResults
        isPending={companiesQuery.isPending}
        isError={companiesQuery.isError}
        error={companiesQuery.error}
        items={companiesQuery.data?.items}
        total={companiesQuery.data?.total ?? 0}
        page={companiesQuery.data?.page ?? filters.page}
        totalPages={companiesQuery.data?.total_pages ?? 0}
        filtered={Boolean(search || status || businessType)}
        onPage={filters.setPage}
        onDelete={(organisation) => {
          setDeleteError("")
          setPendingDelete(organisation)
        }}
        onAddCompany={setAddFor}
      />
      <Dialog
        open={Boolean(pendingDelete)}
        title="Delete organisation"
        onClose={() => {
          if (!deleteCompany.isPending) {
            setPendingDelete(null)
            setDeleteError("")
          }
        }}
      >
        <p className="text-sm text-pine">Delete {pendingDelete?.name}? This cannot be undone.</p>
        {deleteError ? (
          <p className="mt-3 text-sm text-danger" role="alert">
            {deleteError}
          </p>
        ) : null}
        <div className="mt-4 flex justify-end gap-3">
          <button
            type="button"
            className="rounded-md border border-line bg-paper px-4 py-2 font-semibold"
            disabled={deleteCompany.isPending}
            onClick={() => {
              setPendingDelete(null)
              setDeleteError("")
            }}
          >
            Cancel
          </button>
          <button
            type="button"
            className="rounded-md bg-danger px-4 py-2 font-semibold text-paper disabled:opacity-60"
            disabled={deleteCompany.isPending || !pendingDelete}
            onClick={() => {
              if (!pendingDelete) {
                return
              }
              void deleteCompany
                .mutateAsync(pendingDelete.id)
                .then(() => {
                  setPendingDelete(null)
                  setDeleteError("")
                })
                .catch((error: unknown) => {
                  setDeleteError(
                    error instanceof ApiError
                      ? error.message
                      : "The organisation could not be deleted.",
                  )
                })
            }}
          >
            {deleteCompany.isPending ? "Deleting…" : "Delete"}
          </button>
        </div>
      </Dialog>
      <AddCompanyDialog
        organisation={addFor}
        onClose={() => setAddFor(null)}
      />
    </section>
  )
}

function OrganisationResults({
  isPending,
  isError,
  error,
  items,
  total,
  page,
  totalPages,
  filtered,
  onPage,
  onDelete,
  onAddCompany,
}: {
  isPending: boolean
  isError: boolean
  error: unknown
  items: AdminCompanyListItem[] | undefined
  total: number
  page: number
  totalPages: number
  filtered: boolean
  onPage: (page: number) => void
  onDelete: (organisation: AdminCompanyListItem) => void
  onAddCompany: (organisation: AdminCompanyListItem) => void
}) {
  if (isPending) {
    return <LoadingState label="Loading organisations" />
  }
  if (isError) {
    return (
      <div className="mt-6">
        <ErrorState
          message={error instanceof ApiError ? error.message : "Organisations could not be loaded."}
        />
      </div>
    )
  }
  if (!items || items.length === 0) {
    return (
      <div className="mt-6">
        <EmptyState
          title={filtered ? "No organisations match your search." : "No organisations found."}
          message={
            filtered
              ? "Try a different name, status, or business type."
              : "Create an organisation to add its first owner and companies."
          }
        />
      </div>
    )
  }

  return (
    <div className="mt-6">
      <p className="text-sm text-pine">{total} organisations</p>
      <ul className="mt-4 space-y-4">
        {items.map((organisation) => (
          <li key={organisation.id}>
            <OrganisationCard
              organisation={organisation}
              onDelete={onDelete}
              onAddCompany={onAddCompany}
            />
          </li>
        ))}
      </ul>
      <Pagination page={page} totalPages={totalPages} onPage={onPage} />
    </div>
  )
}

function OrganisationCard({
  organisation,
  onDelete,
  onAddCompany,
}: {
  organisation: AdminCompanyListItem
  onDelete: (organisation: AdminCompanyListItem) => void
  onAddCompany: (organisation: AdminCompanyListItem) => void
}) {
  const [expanded, setExpanded] = useState(true)
  const companiesQuery = useOrganisationCompanies(organisation.id)
  const companies = companiesQuery.data ?? []
  const companyCount = companiesQuery.isPending ? null : companies.length
  const ownerLabel = organisation.owner_name
    ? `Owner ${organisation.owner_name}`
    : "Owner not assigned"
  const summary =
    companyCount === null
      ? ownerLabel
      : `${companyCount} ${companyCount === 1 ? "company" : "companies"} · ${ownerLabel}`

  return (
    <article className="rounded-xl border border-line bg-paper shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-3 px-5 py-4">
        <button
          type="button"
          className="flex min-w-0 flex-1 items-start gap-3 text-left"
          onClick={() => setExpanded((value) => !value)}
          aria-expanded={expanded}
        >
          <span
            className="mt-0.5 grid h-10 w-10 shrink-0 place-items-center rounded-lg bg-cream text-copper"
            aria-hidden="true"
          >
            <OrganisationIcon />
          </span>
          <span className="min-w-0">
            <span className="block font-display text-2xl">{organisation.name}</span>
            <span className="mt-1 block text-sm text-pine">{summary}</span>
            {organisation.business_type ? (
              <span className="mt-1 block text-sm text-moss">{organisation.business_type}</span>
            ) : null}
          </span>
        </button>
        <div className="flex flex-wrap items-center gap-2">
          <span
            className={`rounded-md px-2.5 py-1 text-xs font-semibold capitalize ${
              organisation.status === "active"
                ? "bg-cream text-moss"
                : "bg-line/40 text-pine"
            }`}
          >
            {organisation.status}
          </span>
          <details className="relative">
            <summary
              className="cursor-pointer list-none rounded-md border border-line px-2.5 py-2 text-sm font-semibold"
              aria-label={`Actions for ${organisation.name}`}
            >
              ⋮
            </summary>
            <div className="absolute right-0 z-10 mt-2 w-40 rounded-md border border-line bg-paper p-2 shadow-sm">
              <Link
                className="block rounded-md px-3 py-2 text-sm font-semibold hover:bg-cream"
                to={`/organisations/${organisation.id}`}
              >
                View
              </Link>
              <Link
                className="block rounded-md px-3 py-2 text-sm font-semibold hover:bg-cream"
                to={`/organisations/${organisation.id}/edit`}
              >
                Edit
              </Link>
              <button
                type="button"
                className="block w-full rounded-md px-3 py-2 text-left text-sm font-semibold text-danger hover:bg-cream"
                onClick={() => onDelete(organisation)}
              >
                Delete
              </button>
            </div>
          </details>
          <button
            type="button"
            className="rounded-md border border-line px-2.5 py-2 text-sm font-semibold"
            aria-label={expanded ? "Collapse companies" : "Expand companies"}
            onClick={() => setExpanded((value) => !value)}
          >
            {expanded ? "▴" : "▾"}
          </button>
        </div>
      </div>
      {expanded ? (
        <div className="space-y-3 border-t border-line px-5 py-4">
          {companiesQuery.isPending ? <LoadingState label="Loading companies" /> : null}
          {companiesQuery.isError ? (
            <ErrorState
              message={
                companiesQuery.error instanceof ApiError
                  ? companiesQuery.error.message
                  : "Companies could not be loaded."
              }
            />
          ) : null}
          {!companiesQuery.isPending && !companiesQuery.isError && companies.length > 0 ? (
            <CompanyRows items={companies} />
          ) : null}
          {!companiesQuery.isPending && !companiesQuery.isError ? (
            <button
              type="button"
              className="flex w-full items-center justify-center gap-2 rounded-lg border border-dashed border-line bg-cream/60 px-4 py-4 text-sm font-semibold text-pine transition hover:border-copper hover:bg-cream hover:text-ink"
              onClick={() => onAddCompany(organisation)}
            >
              <span aria-hidden="true">+</span>
              Add Company
            </button>
          ) : null}
        </div>
      ) : null}
    </article>
  )
}

function CompanyRows({ items }: { items: OrganisationCompany[] }) {
  return (
    <ul className="space-y-3">
      {items.map((company) => (
        <li
          key={company.id}
          className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-line bg-cream/40 px-4 py-3"
        >
          <div className="flex min-w-0 items-start gap-3">
            <span
              className="mt-0.5 grid h-9 w-9 shrink-0 place-items-center rounded-md bg-paper text-copper"
              aria-hidden="true"
            >
              <CompanyIcon />
            </span>
            <div className="min-w-0">
              <p className="font-semibold">{company.name}</p>
              <p className="mt-1 text-sm text-pine">
                {company.business_type || "No business type"} · {displayUsPhone(company.phone) || "No phone"} ·{" "}
                {company.email || "No email"}
              </p>
            </div>
          </div>
          <span className="rounded-md bg-paper px-2 py-1 text-xs font-semibold capitalize text-moss">
            {company.status}
          </span>
        </li>
      ))}
    </ul>
  )
}

function AddCompanyDialog({
  organisation,
  onClose,
}: {
  organisation: AdminCompanyListItem | null
  onClose: () => void
}) {
  const createCompany = useCreateOrganisationCompany(organisation?.id ?? "")
  const form = useForm<CompanyFormValues>({
    resolver: zodResolver(companySchema),
    defaultValues: emptyCompanyForm,
  })

  return (
    <Dialog
      open={Boolean(organisation)}
      title={organisation ? `Add company to ${organisation.name}` : "Add company"}
      onClose={() => {
        if (!createCompany.isPending) {
          form.reset(emptyCompanyForm)
          onClose()
        }
      }}
    >
      <form
        className="grid gap-4"
        noValidate
        onSubmit={form.handleSubmit(async (values) => {
          if (!organisation) {
            return
          }
          await createCompany.mutateAsync({
            name: values.name.trim(),
            business_type: values.business_type.trim(),
            phone: blankToNull(values.phone),
            email: blankToNull(values.email),
            status: values.status,
          })
          form.reset(emptyCompanyForm)
          onClose()
        })}
      >
        <Field id="add-company-name" label="Company name" error={form.formState.errors.name?.message}>
          <input id="add-company-name" className={fieldClass} {...form.register("name")} />
        </Field>
        <Field
          id="add-company-business-type"
          label="Business type"
          error={form.formState.errors.business_type?.message}
        >
          <input
            id="add-company-business-type"
            className={fieldClass}
            {...form.register("business_type")}
          />
        </Field>
        <Field id="add-company-phone" label="Phone" error={form.formState.errors.phone?.message}>
          <UsPhoneInput id="add-company-phone" registration={form.register("phone")} />
        </Field>
        <Field id="add-company-email" label="Email" error={form.formState.errors.email?.message}>
          <input id="add-company-email" type="email" className={fieldClass} {...form.register("email")} />
        </Field>
        <Field id="add-company-status" label="Status" error={form.formState.errors.status?.message}>
          <select id="add-company-status" className={fieldClass} {...form.register("status")}>
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
          </select>
        </Field>
        {createCompany.error ? (
          <p className="text-sm text-danger" role="alert">
            {createCompany.error instanceof ApiError
              ? createCompany.error.message
              : "The company could not be saved."}
          </p>
        ) : null}
        <div className="flex justify-end gap-3">
          <button
            type="button"
            className="rounded-md border border-line bg-paper px-4 py-2 font-semibold"
            disabled={createCompany.isPending}
            onClick={() => {
              form.reset(emptyCompanyForm)
              onClose()
            }}
          >
            Cancel
          </button>
          <button
            type="submit"
            className="rounded-md bg-copper px-4 py-2 font-semibold text-paper disabled:opacity-60"
            disabled={createCompany.isPending}
          >
            {createCompany.isPending ? "Saving…" : "Add company"}
          </button>
        </div>
      </form>
    </Dialog>
  )
}

function OrganisationIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="1.8">
      <path d="M4 20V8l8-4 8 4v12" />
      <path d="M9 20v-6h6v6" />
      <path d="M9 10h.01M15 10h.01M12 10h.01" />
    </svg>
  )
}

function CompanyIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="1.8">
      <path d="M3 20h18" />
      <path d="M5 20V9l7-4 7 4v11" />
      <path d="M10 20v-5h4v5" />
    </svg>
  )
}
