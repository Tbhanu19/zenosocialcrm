import { useMemo } from "react"
import { zodResolver } from "@hookform/resolvers/zod"
import { useForm } from "react-hook-form"
import { z } from "zod"
import { ApiError } from "../../api/client.ts"
import { Field, fieldClass } from "../../components/common/Field.tsx"
import { UsPhoneInput } from "../../components/common/UsPhoneInput.tsx"
import { useTenantOrganisationCompanies } from "../../hooks/useManagement.ts"
import { formatUsPhone, isUsPhone } from "../../lib/utils.ts"
import {
  BUSINESS_TYPES,
  BUSINESS_TYPE_LABELS,
  type BusinessType,
  type LeadRecord,
  type LeadWrite,
} from "../../types/marketing.ts"

const schema = z.object({
  company_name: z.string().trim().min(1, "Select a company.").max(200),
  business_type: z
    .string()
    .refine(
      (value) => (BUSINESS_TYPES as readonly string[]).includes(value),
      "Select a business type.",
    ),
  address: z.string().max(255),
  phone_number: z.string().refine(isUsPhone, "Enter a US phone number, such as (214) 555-0100."),
  main_contact_name: z.string().max(200),
  email: z
    .string()
    .max(320)
    .refine(
      (value) => value.trim() === "" || z.string().email().safeParse(value.trim()).success,
      "Enter a valid email address.",
    ),
  phone_number_2: z.string().refine(isUsPhone, "Enter a US phone number, such as (214) 555-0100."),
  comments: z.string().max(5000),
})

type LeadFormValues = z.infer<typeof schema>

const emptyValues: LeadFormValues = {
  company_name: "",
  business_type: "hotels",
  address: "",
  phone_number: "",
  main_contact_name: "",
  email: "",
  phone_number_2: "",
  comments: "",
}

export function LeadForm({
  organisationId,
  lead,
  pending,
  error,
  onSubmit,
}: {
  organisationId: string | null
  lead?: LeadRecord
  pending: boolean
  error: unknown
  onSubmit: (body: LeadWrite) => Promise<void>
}) {
  const companiesQuery = useTenantOrganisationCompanies(organisationId)
  const companies = companiesQuery.data ?? []
  const values = useMemo(() => (lead ? toFormValues(lead) : emptyValues), [lead])
  const form = useForm<LeadFormValues>({
    resolver: zodResolver(schema),
    defaultValues: emptyValues,
    values,
  })
  const selectedName = form.watch("company_name")
  const companyOptions = useMemo(() => {
    const names = companies.map((company) => company.name)
    if (selectedName && !names.includes(selectedName)) {
      return [selectedName, ...names]
    }
    return names
  }, [companies, selectedName])
  const message =
    error instanceof ApiError
      ? error.message
      : error instanceof Error
        ? error.message
        : error
          ? "The lead could not be saved."
          : null
  const companyHint = (() => {
    if (!organisationId) {
      return "Choose an organisation in the header first."
    }
    if (companiesQuery.isPending) {
      return "Loading companies…"
    }
    if (companiesQuery.isError) {
      return companiesQuery.error instanceof ApiError
        ? companiesQuery.error.message
        : "Companies could not be loaded."
    }
    if (companies.length === 0 && !selectedName) {
      return "No companies under this organisation yet. Add one from Organisations."
    }
    return null
  })()
  const companyError = companyHint ?? form.formState.errors.company_name?.message

  return (
    <form
      className="mt-6 grid gap-4 sm:grid-cols-2"
      noValidate
      onSubmit={form.handleSubmit(async (formValues) => {
        const companyName = formValues.company_name.trim()
        await onSubmit({
          title: companyName,
          source: lead?.source ?? "manual",
          status: lead?.status ?? "new",
          priority: lead?.priority ?? "medium",
          company_name: companyName,
          business_type: formValues.business_type as BusinessType,
          address: blank(formValues.address),
          phone_number: blank(formValues.phone_number),
          main_contact_name: blank(formValues.main_contact_name),
          email: blank(formValues.email),
          phone_number_2: blank(formValues.phone_number_2),
          comments: blank(formValues.comments),
        })
      })}
    >
      <Field id="company_name" label="Company Name" error={companyError}>
        <select
          id="company_name"
          className={fieldClass}
          disabled={!organisationId || companiesQuery.isPending || (companies.length === 0 && !selectedName)}
          {...form.register("company_name")}
        >
          <option value="">Select a company</option>
          {companyOptions.map((name) => (
            <option key={name} value={name}>
              {name}
            </option>
          ))}
        </select>
      </Field>
      <Field id="business_type" label="Business Type" error={form.formState.errors.business_type?.message}>
        <select id="business_type" className={fieldClass} {...form.register("business_type")}>
          {BUSINESS_TYPES.map((item) => (
            <option key={item} value={item}>
              {BUSINESS_TYPE_LABELS[item]}
            </option>
          ))}
        </select>
      </Field>
      <div className="sm:col-span-2">
        <Field id="address" label="Address" error={form.formState.errors.address?.message}>
          <input id="address" className={fieldClass} {...form.register("address")} />
        </Field>
      </div>
      <Field id="phone_number" label="Phone Number" error={form.formState.errors.phone_number?.message}>
        <UsPhoneInput id="phone_number" registration={form.register("phone_number")} />
      </Field>
      <Field
        id="main_contact_name"
        label="Main Contact person Name"
        error={form.formState.errors.main_contact_name?.message}
      >
        <input id="main_contact_name" className={fieldClass} {...form.register("main_contact_name")} />
      </Field>
      <Field id="email" label="Email" error={form.formState.errors.email?.message}>
        <input
          id="email"
          type="email"
          autoComplete="email"
          inputMode="email"
          placeholder="name@company.com"
          className={fieldClass}
          {...form.register("email")}
        />
      </Field>
      <Field id="phone_number_2" label="Phone Number" error={form.formState.errors.phone_number_2?.message}>
        <UsPhoneInput id="phone_number_2" registration={form.register("phone_number_2")} />
      </Field>
      <div className="sm:col-span-2">
        <Field id="comments" label="Comments" error={form.formState.errors.comments?.message}>
          <textarea id="comments" className={fieldClass} rows={3} {...form.register("comments")} />
        </Field>
      </div>
      {message ? <p className="text-sm text-danger sm:col-span-2">{message}</p> : null}
      <div className="sm:col-span-2">
        <button
          type="submit"
          className="w-fit rounded-md bg-copper px-4 py-2 font-semibold text-paper disabled:opacity-60"
          disabled={pending}
        >
          {pending ? "Saving…" : "Save lead"}
        </button>
      </div>
    </form>
  )
}

function blank(value: string): string | null {
  const trimmed = value.trim()
  return trimmed ? trimmed : null
}

function toFormValues(lead: LeadRecord): LeadFormValues {
  return {
    company_name: lead.company_name ?? lead.title,
    business_type: lead.business_type ?? "hotels",
    address: lead.address ?? "",
    phone_number: formatUsPhone(lead.phone_number ?? ""),
    main_contact_name: lead.main_contact_name ?? "",
    email: lead.email ?? "",
    phone_number_2: formatUsPhone(lead.phone_number_2 ?? ""),
    comments: lead.comments ?? "",
  }
}

export function businessTypeLabel(value: BusinessType | null): string {
  if (!value) {
    return "—"
  }
  return BUSINESS_TYPE_LABELS[value]
}
