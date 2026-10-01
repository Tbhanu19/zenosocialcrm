import { useState } from "react"
import { Link, useLocation, useParams } from "react-router-dom"
import { zodResolver } from "@hookform/resolvers/zod"
import { useForm } from "react-hook-form"
import { z } from "zod"
import { ApiError } from "../../api/client.ts"
import { EmptyState } from "../../components/common/EmptyState.tsx"
import { ErrorState } from "../../components/common/ErrorState.tsx"
import { Field, fieldClass } from "../../components/common/Field.tsx"
import { LoadingState } from "../../components/common/LoadingState.tsx"
import { UsPhoneInput } from "../../components/common/UsPhoneInput.tsx"
import {
  useAdminCompany,
  useCreateOrganisationCompany,
  useOrganisationCompanies,
} from "../../hooks/useManagement.ts"
import { blankToNull, displayUsPhone, formatDate, isUsPhone } from "../../lib/utils.ts"
import type { AdminCompanyDetail, OrganisationCompany } from "../../types/management.ts"

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

export function CompanyDetailPage() {
  const { companyId = "" } = useParams()
  const location = useLocation()
  const companyQuery = useAdminCompany(companyId)
  const notice = readNotice(location.state)

  if (companyQuery.isPending) {
    return <LoadingState label="Loading organisation" />
  }
  if (companyQuery.isError || !companyQuery.data) {
    return (
      <ErrorState
        message={
          companyQuery.error instanceof ApiError
            ? companyQuery.error.message
            : "Organisation could not be loaded."
        }
      />
    )
  }

  const organisation = companyQuery.data
  const people = organisation.counts
  const totalUsers =
    people.owners + people.company_managers + people.marketing_managers + people.employees

  return (
    <section className="mx-auto max-w-3xl">
      <Link to="/organisations" className="text-sm font-semibold text-pine underline">
        Back to organisations
      </Link>
      <div className="mt-3 flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-sm font-semibold tracking-[0.12em] text-copper uppercase">
            Organisation
          </p>
          <h1 className="mt-2 font-display text-4xl">{organisation.name}</h1>
        </div>
        <Link
          to={`/organisations/${organisation.id}/edit`}
          className="rounded-md border border-line bg-paper px-4 py-2 font-semibold"
        >
          Edit
        </Link>
      </div>
      {notice ? (
        <p className="mt-4 rounded-md border border-line bg-paper px-4 py-3 text-sm" role="status">
          {notice}
        </p>
      ) : null}
      <dl className="mt-6 grid gap-4 rounded-lg border border-line bg-paper p-5 sm:grid-cols-2">
        <Info label="Business type" value={organisation.business_type} />
        <Info label="Status" value={organisation.status === "active" ? "Active" : "Inactive"} />
        <Info label="Phone" value={displayUsPhone(organisation.phone)} />
        <Info label="Email" value={organisation.email} />
        <Info label="Website" value={organisation.website} />
        <Info label="Address" value={formatAddress(organisation)} />
        <Info label="Created" value={formatDate(organisation.created_at)} />
        <Info label="Updated" value={formatDate(organisation.updated_at)} />
      </dl>
      <OrganisationCompaniesSection organisationId={organisation.id} />
      <h2 className="mt-8 font-display text-2xl">People</h2>
      <dl className="mt-3 grid gap-3 sm:grid-cols-2">
        <Count label="Users" value={totalUsers} />
        <Count label="Owners" value={people.owners} />
        <Count label="Managers" value={people.company_managers} />
        <Count label="Marketing managers" value={people.marketing_managers} />
        <Count label="Employees" value={people.employees} />
      </dl>
    </section>
  )
}

function OrganisationCompaniesSection({ organisationId }: { organisationId: string }) {
  const companiesQuery = useOrganisationCompanies(organisationId)
  const createCompany = useCreateOrganisationCompany(organisationId)
  const [message, setMessage] = useState("")
  const form = useForm<CompanyFormValues>({
    resolver: zodResolver(companySchema),
    defaultValues: emptyCompanyForm,
  })

  return (
    <div className="mt-8">
      <h2 className="font-display text-2xl">Companies</h2>
      <p className="mt-2 text-sm text-pine">
        Create multiple companies inside this organisation.
      </p>
      <form
        className="mt-4 grid gap-4 sm:grid-cols-2"
        noValidate
        onSubmit={form.handleSubmit(async (values) => {
          setMessage("")
          await createCompany.mutateAsync({
            name: values.name.trim(),
            business_type: values.business_type.trim(),
            phone: blankToNull(values.phone),
            email: blankToNull(values.email),
            status: values.status,
          })
          form.reset(emptyCompanyForm)
          setMessage("Company added.")
        })}
      >
        <Field id="org-company-name" label="Company name" error={form.formState.errors.name?.message}>
          <input id="org-company-name" className={fieldClass} {...form.register("name")} />
        </Field>
        <Field
          id="org-company-business-type"
          label="Business type"
          error={form.formState.errors.business_type?.message}
        >
          <input
            id="org-company-business-type"
            className={fieldClass}
            {...form.register("business_type")}
          />
        </Field>
        <Field id="org-company-phone" label="Phone" error={form.formState.errors.phone?.message}>
          <UsPhoneInput id="org-company-phone" registration={form.register("phone")} />
        </Field>
        <Field id="org-company-email" label="Email" error={form.formState.errors.email?.message}>
          <input id="org-company-email" type="email" className={fieldClass} {...form.register("email")} />
        </Field>
        <Field id="org-company-status" label="Status" error={form.formState.errors.status?.message}>
          <select id="org-company-status" className={fieldClass} {...form.register("status")}>
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
          </select>
        </Field>
        {createCompany.error ? (
          <p className="text-sm text-danger sm:col-span-2" role="alert">
            {createCompany.error instanceof ApiError
              ? createCompany.error.message
              : "The company could not be saved."}
          </p>
        ) : null}
        {message ? <p className="text-sm text-pine sm:col-span-2">{message}</p> : null}
        <div className="sm:col-span-2">
          <button
            type="submit"
            className="rounded-md bg-copper px-4 py-2 font-semibold text-paper disabled:opacity-60"
            disabled={createCompany.isPending}
          >
            {createCompany.isPending ? "Saving…" : "Add company"}
          </button>
        </div>
      </form>
      <div className="mt-6">
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
        {companiesQuery.data && companiesQuery.data.length === 0 ? (
          <EmptyState
            title="No companies yet."
            message="Add the first company for this organisation."
          />
        ) : null}
        {companiesQuery.data && companiesQuery.data.length > 0 ? (
          <CompanyList items={companiesQuery.data} />
        ) : null}
      </div>
    </div>
  )
}

function CompanyList({ items }: { items: OrganisationCompany[] }) {
  return (
    <ul className="space-y-3">
      {items.map((company) => (
        <li key={company.id} className="rounded-lg border border-line bg-paper p-4">
          <p className="font-semibold">{company.name}</p>
          <p className="mt-1 text-sm text-pine">
            {company.business_type || "No business type"} · {displayUsPhone(company.phone) || "No phone"} ·{" "}
            {company.email || "No email"}
          </p>
          <p className="mt-1 text-sm capitalize">Status: {company.status}</p>
        </li>
      ))}
    </ul>
  )
}

function Info({ label, value }: { label: string; value: string | null }) {
  return (
    <div>
      <dt className="text-sm font-semibold text-moss">{label}</dt>
      <dd className="mt-1">{value || "—"}</dd>
    </div>
  )
}

function Count({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-lg border border-line bg-paper px-4 py-3">
      <dt className="text-sm text-moss">{label}</dt>
      <dd className="font-display text-2xl">{value}</dd>
    </div>
  )
}

function formatAddress(company: AdminCompanyDetail): string | null {
  const parts = [company.address, company.city, company.state, company.zip_code].filter(Boolean)
  return parts.length > 0 ? parts.join(", ") : null
}

function readNotice(state: unknown): string | null {
  if (typeof state !== "object" || state === null || !("notice" in state)) {
    return null
  }
  return typeof state.notice === "string" ? state.notice : null
}
