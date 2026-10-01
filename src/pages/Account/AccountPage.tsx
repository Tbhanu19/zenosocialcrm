import { useState } from "react"
import { zodResolver } from "@hookform/resolvers/zod"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { useForm } from "react-hook-form"
import { z } from "zod"
import { ApiError } from "../../api/client.ts"
import { updateCurrentUser } from "../../api/auth.ts"
import { queryKeys } from "../../api/query-keys.ts"
import { Field, fieldClass } from "../../components/common/Field.tsx"
import { UsPhoneInput } from "../../components/common/UsPhoneInput.tsx"
import { useSession } from "../../hooks/useSession.ts"
import { blankToNull, displayUsPhone, formatDate, formatUsPhone, isUsPhone, roleLabel } from "../../lib/utils.ts"
import type { CurrentUser } from "../../types/user.ts"

const profileSchema = z.object({
  first_name: z.string().trim().min(1, "First name is required.").max(100),
  last_name: z.string().trim().min(1, "Last name is required.").max(100),
  email: z.string().trim().email("Enter a valid email."),
  phone: z.string().refine(isUsPhone, "Enter a US phone number, such as (214) 555-0100."),
})

type ProfileValues = z.infer<typeof profileSchema>

export function AccountPage() {
  const { currentUser: user, activeCompany, navRole, isLoading } = useSession()
  const [editing, setEditing] = useState(false)

  if (isLoading && !user) {
    return <p className="text-sm text-pine">Loading account</p>
  }
  if (!user) {
    return <p className="text-sm text-pine">Account details are unavailable.</p>
  }

  const fullName = `${user.first_name} ${user.last_name}`

  return (
    <section className="mx-auto max-w-3xl">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-sm font-semibold tracking-[0.12em] text-copper uppercase">Account</p>
          <h1 className="mt-2 font-display text-4xl">{fullName}</h1>
          <p className="mt-2 text-pine">{user.email}</p>
        </div>
        {editing ? null : (
          <button
            type="button"
            className="rounded-md border border-line bg-paper px-4 py-2 font-semibold"
            onClick={() => setEditing(true)}
          >
            Edit
          </button>
        )}
      </div>
      {editing ? (
        <ProfileForm
          user={user}
          onCancel={() => setEditing(false)}
          onSaved={() => setEditing(false)}
        />
      ) : (
        <dl className="mt-8 grid gap-4 sm:grid-cols-2">
          <Detail label="First name" value={user.first_name} />
          <Detail label="Last name" value={user.last_name} />
          <Detail label="Email" value={user.email} />
          <Detail label="Phone" value={displayUsPhone(user.phone)} />
        </dl>
      )}
      <dl className="mt-4 grid gap-4 sm:grid-cols-2">
        <Detail label="Role" value={navRole ? roleLabel(navRole) : null} />
        <Detail label="Status" value={roleLabel(user.status)} />
        <Detail label="Organisation" value={activeCompany?.name ?? null} />
        <Detail label="Member since" value={formatDate(user.created_at)} />
        <Detail label="Profile updated" value={formatDate(user.updated_at)} />
      </dl>
    </section>
  )
}

function ProfileForm({
  user,
  onCancel,
  onSaved,
}: {
  user: CurrentUser
  onCancel: () => void
  onSaved: () => void
}) {
  const queryClient = useQueryClient()
  const form = useForm<ProfileValues>({
    resolver: zodResolver(profileSchema),
    defaultValues: {
      first_name: user.first_name,
      last_name: user.last_name,
      email: user.email,
      phone: formatUsPhone(user.phone ?? ""),
    },
  })
  const save = useMutation({
    mutationFn: updateCurrentUser,
    onSuccess: (updated) => {
      queryClient.setQueryData(queryKeys.currentUser, updated)
      onSaved()
    },
  })
  const message =
    save.error instanceof ApiError
      ? save.error.message
      : save.error
        ? "The profile could not be saved."
        : null

  return (
    <form
      className="mt-8 grid gap-4 sm:grid-cols-2"
      noValidate
      onSubmit={form.handleSubmit(async (values) => {
        await save.mutateAsync({
          first_name: values.first_name.trim(),
          last_name: values.last_name.trim(),
          email: values.email.trim(),
          phone: blankToNull(values.phone),
        })
      })}
    >
      <Field id="account-first" label="First name" error={form.formState.errors.first_name?.message}>
        <input id="account-first" className={fieldClass} {...form.register("first_name")} />
      </Field>
      <Field id="account-last" label="Last name" error={form.formState.errors.last_name?.message}>
        <input id="account-last" className={fieldClass} {...form.register("last_name")} />
      </Field>
      <Field id="account-email" label="Email" error={form.formState.errors.email?.message}>
        <input id="account-email" type="email" autoComplete="email" className={fieldClass} {...form.register("email")} />
      </Field>
      <Field id="account-phone" label="Phone" error={form.formState.errors.phone?.message}>
        <UsPhoneInput id="account-phone" registration={form.register("phone")} />
      </Field>
      {message ? (
        <p className="text-sm text-danger sm:col-span-2" role="alert">
          {message}
        </p>
      ) : null}
      <div className="flex gap-3 sm:col-span-2">
        <button
          type="submit"
          className="rounded-md bg-copper px-4 py-2 font-semibold text-paper disabled:opacity-60"
          disabled={save.isPending}
        >
          {save.isPending ? "Saving…" : "Save"}
        </button>
        <button
          type="button"
          className="rounded-md border border-line bg-paper px-4 py-2 font-semibold"
          onClick={onCancel}
          disabled={save.isPending}
        >
          Cancel
        </button>
      </div>
    </form>
  )
}

function Detail({ label, value }: { label: string; value: string | null }) {
  return (
    <div className="rounded-lg border border-line bg-paper p-5">
      <dt className="text-sm font-semibold tracking-wide text-moss uppercase">{label}</dt>
      <dd className="mt-2 text-lg">{value || "—"}</dd>
    </div>
  )
}
