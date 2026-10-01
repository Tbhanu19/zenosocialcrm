import { useMemo } from "react"
import { zodResolver } from "@hookform/resolvers/zod"
import { useForm } from "react-hook-form"
import { z } from "zod"
import { ApiError } from "../../api/client.ts"
import { Field, fieldClass } from "../../components/common/Field.tsx"
import { UsPhoneInput } from "../../components/common/UsPhoneInput.tsx"
import { formatUsPhone, isUsPhone, roleLabel } from "../../lib/utils.ts"
import type { AssigneeOption, ContactRecord, ContactWrite } from "../../types/crm.ts"
import { CONTACT_SOURCES } from "../../types/crm.ts"

const schema = z.object({
  first_name: z.string().trim().min(1, "First name is required.").max(100),
  last_name: z.string().trim().min(1, "Last name is required.").max(100),
  email: z
    .string()
    .trim()
    .max(320)
    .refine((value) => value === "" || z.email().safeParse(value).success, "Enter a valid email."),
  phone: z.string().refine(isUsPhone, "Enter a US phone number, such as (214) 555-0100."),
  company_name: z.string().max(200),
  address: z.string().max(255),
  city: z.string().max(100),
  state: z.string().max(100),
  zip_code: z.string().max(20),
  source: z.enum(["manual", "website", "import", "campaign", "referral", "other"]),
  status: z.enum(["active", "inactive", "archived"]),
  opted_in: z.enum(["yes", "no"]),
  contact_date: z.string(),
  notes: z.string().max(5000),
  assigned_to_user_id: z.string(),
})

type ContactFormValues = z.infer<typeof schema>

const emptyValues: ContactFormValues = {
  first_name: "",
  last_name: "",
  email: "",
  phone: "",
  company_name: "",
  address: "",
  city: "",
  state: "",
  zip_code: "",
  source: "manual",
  status: "active",
  opted_in: "yes",
  contact_date: "",
  notes: "",
  assigned_to_user_id: "",
}

export function ContactForm({
  mode,
  contact,
  assignees,
  assigneeTotal,
  pending,
  error,
  onSubmit,
}: {
  mode: "create" | "edit"
  contact?: ContactRecord
  assignees: AssigneeOption[]
  assigneeTotal: number
  pending: boolean
  error: unknown
  onSubmit: (body: ContactWrite) => Promise<void>
}) {
  const values = useMemo(() => (contact ? toFormValues(contact) : emptyValues), [contact])
  const form = useForm<ContactFormValues>({
    resolver: zodResolver(schema),
    defaultValues: emptyValues,
    values,
  })
  const options = useMemo(() => {
    if (!contact?.assigned_to_user_id || !contact.assignee_name) {
      return assignees
    }
    if (assignees.some((person) => person.id === contact.assigned_to_user_id)) {
      return assignees
    }
    const [first = "", ...rest] = contact.assignee_name.split(" ")
    return [
      {
        id: contact.assigned_to_user_id,
        first_name: first,
        last_name: rest.join(" "),
      },
      ...assignees,
    ]
  }, [assignees, contact])
  const message =
    error instanceof ApiError ? error.message : error ? "The contact could not be saved." : null
  const statuses = mode === "create" ? (["active", "inactive"] as const) : (["active", "inactive", "archived"] as const)

  return (
    <form
      className="mt-6 grid gap-4"
      noValidate
      onSubmit={form.handleSubmit(async (formValues) => {
        await onSubmit({
          first_name: formValues.first_name.trim(),
          last_name: formValues.last_name.trim(),
          email: formValues.email.trim().toLowerCase() || null,
          phone: blank(formValues.phone),
          company_name: blank(formValues.company_name),
          address: blank(formValues.address),
          city: blank(formValues.city),
          state: blank(formValues.state),
          zip_code: blank(formValues.zip_code),
          source: formValues.source,
          status: formValues.status,
          opted_in: formValues.opted_in === "yes",
          contact_date: blank(formValues.contact_date),
          notes: blank(formValues.notes),
          assigned_to_user_id: formValues.assigned_to_user_id || null,
        })
      })}
    >
      {message ? (
        <p className="rounded-md border border-danger/30 bg-paper px-4 py-3 text-sm" role="alert">
          {message}
        </p>
      ) : null}
      <div className="grid gap-4 sm:grid-cols-2">
        <Field id="first_name" label="First name" error={form.formState.errors.first_name?.message}>
          <input id="first_name" className={fieldClass} aria-invalid={Boolean(form.formState.errors.first_name)} {...form.register("first_name")} />
        </Field>
        <Field id="last_name" label="Last name" error={form.formState.errors.last_name?.message}>
          <input id="last_name" className={fieldClass} aria-invalid={Boolean(form.formState.errors.last_name)} {...form.register("last_name")} />
        </Field>
        <Field id="email" label="Email" error={form.formState.errors.email?.message}>
          <input id="email" type="email" autoComplete="email" className={fieldClass} aria-invalid={Boolean(form.formState.errors.email)} {...form.register("email")} />
        </Field>
        <Field id="phone" label="Phone" error={form.formState.errors.phone?.message}>
          <UsPhoneInput id="phone" registration={form.register("phone")} />
        </Field>
        <Field id="company_name" label="Company" error={form.formState.errors.company_name?.message}>
          <input id="company_name" className={fieldClass} {...form.register("company_name")} />
        </Field>
        <Field id="source" label="Source" error={form.formState.errors.source?.message}>
          <select id="source" className={fieldClass} {...form.register("source")}>
            {CONTACT_SOURCES.map((source) => (
              <option key={source} value={source}>
                {roleLabel(source)}
              </option>
            ))}
          </select>
        </Field>
        <Field id="opted_in" label="Opted in" error={form.formState.errors.opted_in?.message}>
          <select id="opted_in" className={fieldClass} {...form.register("opted_in")}>
            <option value="yes">Yes</option>
            <option value="no">No</option>
          </select>
        </Field>
        <Field id="contact_date" label="Date" error={form.formState.errors.contact_date?.message}>
          <input id="contact_date" type="date" className={fieldClass} {...form.register("contact_date")} />
        </Field>
        <Field id="status" label="Status" error={form.formState.errors.status?.message}>
          <select id="status" className={fieldClass} {...form.register("status")}>
            {statuses.map((status) => (
              <option key={status} value={status}>
                {roleLabel(status)}
              </option>
            ))}
          </select>
        </Field>
        <Field id="assigned_to_user_id" label="Assigned to" error={form.formState.errors.assigned_to_user_id?.message}>
          <select id="assigned_to_user_id" className={fieldClass} {...form.register("assigned_to_user_id")}>
            <option value="">Unassigned</option>
            {options.map((person) => (
              <option key={person.id} value={person.id}>
                {person.first_name} {person.last_name}
              </option>
            ))}
          </select>
        </Field>
      </div>
      {assigneeTotal > assignees.length ? (
        <p className="text-sm text-pine">Showing the first 100 people in this company.</p>
      ) : null}
      <Field id="address" label="Address" error={form.formState.errors.address?.message}>
        <input id="address" className={fieldClass} {...form.register("address")} />
      </Field>
      <div className="grid gap-4 sm:grid-cols-3">
        <Field id="city" label="City" error={form.formState.errors.city?.message}>
          <input id="city" className={fieldClass} {...form.register("city")} />
        </Field>
        <Field id="state" label="State" error={form.formState.errors.state?.message}>
          <input id="state" className={fieldClass} {...form.register("state")} />
        </Field>
        <Field id="zip_code" label="ZIP code" error={form.formState.errors.zip_code?.message}>
          <input id="zip_code" className={fieldClass} {...form.register("zip_code")} />
        </Field>
      </div>
      <Field id="notes" label="Notes" error={form.formState.errors.notes?.message}>
        <textarea id="notes" rows={4} className={fieldClass} {...form.register("notes")} />
      </Field>
      <button
        type="submit"
        className="w-fit rounded-md bg-copper px-4 py-2 font-semibold text-paper disabled:opacity-60"
        disabled={pending}
      >
        {pending ? "Saving…" : mode === "create" ? "Add contact" : "Save changes"}
      </button>
    </form>
  )
}

function toFormValues(contact: ContactRecord): ContactFormValues {
  return {
    first_name: contact.first_name,
    last_name: contact.last_name,
    email: contact.email ?? "",
    phone: formatUsPhone(contact.phone ?? ""),
    company_name: contact.company_name ?? "",
    address: contact.address ?? "",
    city: contact.city ?? "",
    state: contact.state ?? "",
    zip_code: contact.zip_code ?? "",
    source: contact.source,
    status: contact.status,
    opted_in: contact.opted_in ? "yes" : "no",
    contact_date: contact.contact_date ?? "",
    notes: contact.notes ?? "",
    assigned_to_user_id: contact.assigned_to_user_id ?? "",
  }
}

function blank(value: string): string | null {
  const trimmed = value.trim()
  return trimmed ? trimmed : null
}
