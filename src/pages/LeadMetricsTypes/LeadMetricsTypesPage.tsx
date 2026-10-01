import { useState } from "react"
import { zodResolver } from "@hookform/resolvers/zod"
import { useForm } from "react-hook-form"
import { z } from "zod"
import { ApiError } from "../../api/client.ts"
import { EmptyState } from "../../components/common/EmptyState.tsx"
import { ErrorState } from "../../components/common/ErrorState.tsx"
import { Field, fieldClass } from "../../components/common/Field.tsx"
import { LoadingState } from "../../components/common/LoadingState.tsx"
import {
  useCreateLeadMetricsType,
  useLeadMetricsTypes,
  useUpdateLeadMetricsType,
} from "../../hooks/useLeadMetricsTypes.ts"
import { useSession } from "../../hooks/useSession.ts"
import { blankToNull } from "../../lib/utils.ts"
import type { LeadMetricsType } from "../../types/lead-metrics-type.ts"

const schema = z.object({
  name: z.string().trim().min(1, "Name is required.").max(200),
  description: z.string().max(2000),
  value: z
    .string()
    .trim()
    .min(1, "Value is required.")
    .refine((value) => /^\d+$/.test(value), "Enter a whole number.")
    .transform((value) => Number(value))
    .refine((value) => value >= 0, "Value cannot be negative."),
  status: z.enum(["active", "inactive"]),
})

type FormValues = z.input<typeof schema>
type ParsedFormValues = z.output<typeof schema>

const emptyValues: FormValues = {
  name: "",
  description: "",
  value: "0",
  status: "active",
}

export function LeadMetricsTypesPage() {
  const session = useSession()
  const companyId = session.activeCompany?.id ?? null
  const typesQuery = useLeadMetricsTypes(companyId)
  const createType = useCreateLeadMetricsType(companyId ?? "")
  const updateType = useUpdateLeadMetricsType(companyId ?? "")
  const [editing, setEditing] = useState<LeadMetricsType | null>(null)
  const form = useForm<FormValues, unknown, ParsedFormValues>({
    resolver: zodResolver(schema),
    defaultValues: emptyValues,
  })

  if (!companyId) {
    return (
      <EmptyState
        title="No organisation selected"
        message="Choose an organisation in the header to manage lead metrics types."
      />
    )
  }

  return (
    <section>
      <p className="text-sm font-semibold tracking-[0.12em] text-copper uppercase">Marketing</p>
      <h1 className="mt-2 font-display text-4xl">Lead Metrics Type</h1>
      <p className="mt-2 max-w-3xl text-pine">
        Store lead metrics types for {session.activeCompany?.name ?? "the selected organisation"}.
        Values show as indicators on the Lead Metrics page.
      </p>

      <form
        className="mt-6 grid gap-4 sm:grid-cols-2"
        noValidate
        onSubmit={form.handleSubmit(async (values) => {
          const body = {
            name: values.name.trim(),
            description: blankToNull(values.description),
            value: values.value,
            status: values.status,
          }
          if (editing) {
            await updateType.mutateAsync({ typeId: editing.id, body })
            setEditing(null)
          } else {
            await createType.mutateAsync(body)
          }
          form.reset(emptyValues)
        })}
      >
        <Field id="metrics-type-name" label="Name" error={form.formState.errors.name?.message}>
          <input id="metrics-type-name" className={fieldClass} {...form.register("name")} />
        </Field>
        <Field id="metrics-type-value" label="Value" error={form.formState.errors.value?.message}>
          <input
            id="metrics-type-value"
            type="number"
            min={0}
            step={1}
            className={fieldClass}
            {...form.register("value")}
          />
        </Field>
        <Field id="metrics-type-status" label="Status" error={form.formState.errors.status?.message}>
          <select id="metrics-type-status" className={fieldClass} {...form.register("status")}>
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
          </select>
        </Field>
        <div className="sm:col-span-2">
          <Field
            id="metrics-type-description"
            label="Description"
            error={form.formState.errors.description?.message}
          >
            <textarea
              id="metrics-type-description"
              className={fieldClass}
              rows={3}
              {...form.register("description")}
            />
          </Field>
        </div>
        {createType.error || updateType.error ? (
          <p className="text-sm text-danger sm:col-span-2" role="alert">
            {(createType.error ?? updateType.error) instanceof ApiError
              ? ((createType.error ?? updateType.error) as ApiError).message
              : "The lead metrics type could not be saved."}
          </p>
        ) : null}
        <div className="flex flex-wrap gap-3 sm:col-span-2">
          <button
            type="submit"
            className="rounded-md bg-copper px-4 py-2 font-semibold text-paper disabled:opacity-60"
            disabled={createType.isPending || updateType.isPending}
          >
            {createType.isPending || updateType.isPending
              ? "Saving…"
              : editing
                ? "Save changes"
                : "Add type"}
          </button>
          {editing ? (
            <button
              type="button"
              className="rounded-md border border-line bg-paper px-4 py-2 font-semibold"
              onClick={() => {
                setEditing(null)
                form.reset(emptyValues)
              }}
            >
              Cancel edit
            </button>
          ) : null}
        </div>
      </form>

      <div className="mt-8">
        {typesQuery.isPending ? <LoadingState label="Loading lead metrics types" /> : null}
        {typesQuery.isError ? (
          <ErrorState
            message={
              typesQuery.error instanceof ApiError
                ? typesQuery.error.message
                : "Lead metrics types could not be loaded."
            }
          />
        ) : null}
        {typesQuery.data && typesQuery.data.length === 0 ? (
          <EmptyState
            title="No lead metrics types yet."
            message="Add the first type for this organisation."
          />
        ) : null}
        {typesQuery.data && typesQuery.data.length > 0 ? (
          <ul className="space-y-3">
            {typesQuery.data.map((item) => (
              <li
                key={item.id}
                className="flex flex-wrap items-start justify-between gap-3 rounded-lg border border-line bg-paper px-4 py-3"
              >
                <div className="min-w-0">
                  <p className="font-semibold">{item.name}</p>
                  <p className="mt-1 font-display text-2xl">{item.value}</p>
                  <p className="mt-1 text-sm text-pine">{item.description || "No description"}</p>
                  <p className="mt-1 text-xs font-semibold capitalize text-moss">{item.status}</p>
                </div>
                <button
                  type="button"
                  className="rounded-md border border-line px-3 py-1.5 text-sm font-semibold"
                  onClick={() => {
                    setEditing(item)
                    form.reset({
                      name: item.name,
                      description: item.description ?? "",
                      value: String(item.value),
                      status: item.status,
                    })
                  }}
                >
                  Edit
                </button>
              </li>
            ))}
          </ul>
        ) : null}
      </div>
    </section>
  )
}
