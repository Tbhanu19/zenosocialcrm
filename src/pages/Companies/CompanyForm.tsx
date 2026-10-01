import { zodResolver } from "@hookform/resolvers/zod"
import { useForm } from "react-hook-form"
import { z } from "zod"
import { ApiError } from "../../api/client.ts"
import { Field, fieldClass } from "../../components/common/Field.tsx"
import { UsPhoneInput } from "../../components/common/UsPhoneInput.tsx"
import { blankToNull, formatUsPhone, isUsPhone } from "../../lib/utils.ts"
import type { CompanyRecord, CompanyWrite, CreateCompanyBody } from "../../types/management.ts"

const companySchema = z
  .object({
    name: z.string().trim().min(1, "Organisation name is required.").max(200),
    business_type: z.string().trim().max(100),
    phone: z.string().refine(isUsPhone, "Enter a US phone number, such as (214) 555-0100."),
    email: z.string().max(320),
    website: z.string().max(500),
    address: z.string().max(255),
    city: z.string().max(100),
    state: z.string().max(100),
    zip_code: z.string().max(20),
    status: z.enum(["active", "inactive"]),
    owner_first_name: z.string().max(100),
    owner_last_name: z.string().max(100),
    owner_email: z.string().max(320),
    owner_phone: z.string().refine(isUsPhone, "Enter a US phone number, such as (214) 555-0100."),
  })
  .superRefine((values, ctx) => {
    checkEmail(values.email, ctx, "email", false)
  })

const createSchema = companySchema.superRefine((values, ctx) => {
  if (!values.business_type.trim()) {
    ctx.addIssue({ code: "custom", message: "Business type is required.", path: ["business_type"] })
  }
  if (!values.owner_first_name.trim()) {
    ctx.addIssue({ code: "custom", message: "First name is required.", path: ["owner_first_name"] })
  }
  if (!values.owner_last_name.trim()) {
    ctx.addIssue({ code: "custom", message: "Last name is required.", path: ["owner_last_name"] })
  }
  checkEmail(values.owner_email, ctx, "owner_email", true)
})

type CompanyFormValues = z.infer<typeof companySchema>

const emptyValues: CompanyFormValues = {
  name: "",
  business_type: "",
  phone: "",
  email: "",
  website: "",
  address: "",
  city: "",
  state: "",
  zip_code: "",
  status: "active",
  owner_first_name: "",
  owner_last_name: "",
  owner_email: "",
  owner_phone: "",
}

function checkEmail(
  value: string,
  ctx: z.RefinementCtx,
  path: string,
  required: boolean,
) {
  const trimmed = value.trim()
  if (!trimmed) {
    if (required) {
      ctx.addIssue({ code: "custom", message: "Email is required.", path: [path] })
    }
    return
  }
  if (!z.string().email().safeParse(trimmed).success) {
    ctx.addIssue({ code: "custom", message: "Enter a valid email.", path: [path] })
  }
}

export function CompanyForm({
  mode,
  company,
  pending,
  error,
  onCreate,
  onUpdate,
}: {
  mode: "create" | "edit"
  company?: CompanyRecord
  pending: boolean
  error: unknown
  onCreate?: (body: CreateCompanyBody) => Promise<void>
  onUpdate?: (body: CompanyWrite) => Promise<void>
}) {
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<CompanyFormValues>({
    resolver: zodResolver(mode === "create" ? createSchema : companySchema),
    defaultValues: company
      ? {
          ...emptyValues,
          name: company.name,
          business_type: company.business_type ?? "",
          phone: formatUsPhone(company.phone ?? ""),
          email: company.email ?? "",
          website: company.website ?? "",
          address: company.address ?? "",
          city: company.city ?? "",
          state: company.state ?? "",
          zip_code: company.zip_code ?? "",
          status: company.status,
        }
      : emptyValues,
  })
  const busy = pending || isSubmitting
  const formError =
    error instanceof ApiError ? error.message : error ? "The company could not be saved." : null

  return (
    <form
      className="mt-6 grid gap-4 sm:grid-cols-2"
      noValidate
      onSubmit={handleSubmit(async (values) => {
        const companyBody: CompanyWrite = {
          name: values.name.trim(),
          business_type: blankToNull(values.business_type),
          phone: blankToNull(values.phone),
          email: blankToNull(values.email),
          website: blankToNull(values.website),
          address: blankToNull(values.address),
          city: blankToNull(values.city),
          state: blankToNull(values.state),
          zip_code: blankToNull(values.zip_code),
          status: values.status,
        }
        if (mode === "create" && onCreate && companyBody.business_type) {
          await onCreate({
            ...companyBody,
            business_type: companyBody.business_type,
            owner: {
              first_name: values.owner_first_name.trim(),
              last_name: values.owner_last_name.trim(),
              email: values.owner_email.trim(),
              phone: blankToNull(values.owner_phone),
            },
          })
          return
        }
        await onUpdate?.(companyBody)
      })}
    >
      <Field id="company-name" label="Organisation name" error={errors.name?.message}>
        <input id="company-name" className={fieldClass} autoComplete="organization" {...register("name")} />
      </Field>
      <Field id="business-type" label="Business type" error={errors.business_type?.message}>
        <input id="business-type" className={fieldClass} {...register("business_type")} />
      </Field>
      <Field id="company-phone" label="Phone" error={errors.phone?.message}>
        <UsPhoneInput id="company-phone" registration={register("phone")} />
      </Field>
      <Field id="company-email" label="Email" error={errors.email?.message}>
        <input id="company-email" type="email" className={fieldClass} {...register("email")} />
      </Field>
      <Field id="website" label="Website" error={errors.website?.message}>
        <input id="website" className={fieldClass} {...register("website")} />
      </Field>
      <Field id="status" label="Status" error={errors.status?.message}>
        <select id="status" className={fieldClass} {...register("status")}>
          <option value="active">Active</option>
          <option value="inactive">Inactive</option>
        </select>
      </Field>
      <Field id="address" label="Address" error={errors.address?.message}>
        <input id="address" className={fieldClass} {...register("address")} />
      </Field>
      <Field id="city" label="City" error={errors.city?.message}>
        <input id="city" className={fieldClass} {...register("city")} />
      </Field>
      <Field id="state" label="State" error={errors.state?.message}>
        <input id="state" className={fieldClass} {...register("state")} />
      </Field>
      <Field id="zip" label="ZIP" error={errors.zip_code?.message}>
        <input id="zip" className={fieldClass} autoComplete="postal-code" {...register("zip_code")} />
      </Field>
      {mode === "create" ? (
        <fieldset className="grid gap-4 border-t border-line pt-4 sm:col-span-2 sm:grid-cols-2">
          <legend className="font-display text-2xl">Initial owner</legend>
          <p className="text-sm text-pine sm:col-span-2">
            A new owner is invited and cannot sign in until an invitation is completed. An existing
            account is linked without changing it.
          </p>
          <Field id="owner-first" label="First name" error={errors.owner_first_name?.message}>
            <input id="owner-first" className={fieldClass} {...register("owner_first_name")} />
          </Field>
          <Field id="owner-last" label="Last name" error={errors.owner_last_name?.message}>
            <input id="owner-last" className={fieldClass} {...register("owner_last_name")} />
          </Field>
          <Field id="owner-email" label="Email" error={errors.owner_email?.message}>
            <input
              id="owner-email"
              type="email"
              autoComplete="off"
              className={fieldClass}
              {...register("owner_email")}
            />
          </Field>
          <Field id="owner-phone" label="Phone" error={errors.owner_phone?.message}>
            <UsPhoneInput id="owner-phone" registration={register("owner_phone")} />
          </Field>
        </fieldset>
      ) : null}
      {formError ? (
        <p className="text-sm text-danger sm:col-span-2" role="alert">
          {formError}
        </p>
      ) : null}
      <div className="sm:col-span-2">
        <button
          type="submit"
          disabled={busy}
          className="rounded-md bg-copper px-4 py-2 font-semibold text-paper disabled:opacity-60"
        >
          {busy ? "Saving" : mode === "create" ? "Create organisation" : "Save changes"}
        </button>
      </div>
    </form>
  )
}
