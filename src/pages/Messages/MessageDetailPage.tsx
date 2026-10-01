import { zodResolver } from "@hookform/resolvers/zod"
import { useForm } from "react-hook-form"
import { Link, useLocation, useParams } from "react-router-dom"
import { z } from "zod"
import { ApiError } from "../../api/client.ts"
import { EmptyState } from "../../components/common/EmptyState.tsx"
import { ErrorState } from "../../components/common/ErrorState.tsx"
import { Field, fieldClass } from "../../components/common/Field.tsx"
import { LoadingState } from "../../components/common/LoadingState.tsx"
import { useMessage, useUpdateMessage } from "../../hooks/useCrm.ts"
import { useSession } from "../../hooks/useSession.ts"
import { formatDate, roleLabel } from "../../lib/utils.ts"

const schema = z.object({
  subject: z.string().trim().max(200),
  body: z.string().trim().min(1, "Message is required.").max(5000),
})

type DraftValues = z.infer<typeof schema>

export function MessageDetailPage() {
  const { messageId = "" } = useParams()
  const location = useLocation()
  const session = useSession()
  const companyId = session.activeCompany?.id ?? null
  const messageQuery = useMessage(companyId, messageId)
  const updateMessage = useUpdateMessage(
    companyId ?? "",
    messageId,
    messageQuery.data?.contact_id ?? null,
  )
  const notice = readNotice(location.state)
  const form = useForm<DraftValues>({
    resolver: zodResolver(schema),
    values: {
      subject: messageQuery.data?.subject ?? "",
      body: messageQuery.data?.body ?? "",
    },
  })
  const draftBody = form.watch("body")

  if (!companyId) {
    return <EmptyState title="No company selected" message="Choose a company to view this message." />
  }
  if (messageQuery.isPending) {
    return <LoadingState label="Loading message" />
  }
  if (messageQuery.isError || !messageQuery.data) {
    return (
      <ErrorState
        message={
          messageQuery.error instanceof ApiError
            ? messageQuery.error.message
            : "Message could not be loaded."
        }
      />
    )
  }

  const message = messageQuery.data
  const draft = message.status === "draft"

  return (
    <section className="mx-auto max-w-3xl">
      <Link to="/messages" className="text-sm font-semibold text-pine underline">
        Back to messages
      </Link>
      <p className="mt-3 text-sm font-semibold tracking-[0.12em] text-copper uppercase">
        {roleLabel(message.message_type)}
      </p>
      <h1 className="mt-2 font-display text-4xl">{message.subject || "No subject"}</h1>
      {notice ? (
        <p className="mt-4 rounded-md border border-line bg-paper px-4 py-3 text-sm" role="status">
          {notice}
        </p>
      ) : null}
      {message.error_message ? (
        <p className="mt-4 rounded-md border border-line bg-paper px-4 py-3 text-sm" role="status">
          {message.error_message}
        </p>
      ) : null}
      <dl className="mt-6 grid gap-4 rounded-lg border border-line bg-paper p-5 sm:grid-cols-2">
        <Info label="Contact" value={message.contact_name} />
        <Info label="Status" value={roleLabel(message.status)} />
        <Info label="Direction" value={roleLabel(message.direction)} />
        <Info label="Created by" value={message.creator_name} />
        <Info label="Created" value={formatDate(message.created_at)} />
        <Info label="Updated" value={formatDate(message.updated_at)} />
      </dl>
      {draft ? (
        <form
          className="mt-6 grid gap-4"
          noValidate
          onSubmit={form.handleSubmit(async (values) => {
            if (message.message_type === "email" && !values.subject.trim()) {
              form.setError("subject", { message: "Subject is required for email." })
              return
            }
            await updateMessage.mutateAsync({
              subject: message.message_type === "email" ? values.subject.trim() : null,
              body: values.body.trim(),
            })
          })}
        >
          {message.message_type === "email" ? (
            <Field id="subject" label="Subject" error={form.formState.errors.subject?.message}>
              <input id="subject" className={fieldClass} {...form.register("subject")} />
            </Field>
          ) : null}
          <Field id="body" label="Message" error={form.formState.errors.body?.message}>
            <textarea id="body" rows={6} className={fieldClass} {...form.register("body")} />
          </Field>
          {message.message_type === "sms" ? (
            <p className="text-sm text-pine">{draftBody.trim().length} characters</p>
          ) : null}
          {updateMessage.error ? (
            <p className="text-sm text-danger" role="alert">
              {updateMessage.error instanceof ApiError
                ? updateMessage.error.message
                : "The draft could not be saved."}
            </p>
          ) : null}
          <button
            type="submit"
            className="w-fit rounded-md bg-copper px-4 py-2 font-semibold text-paper disabled:opacity-60"
            disabled={updateMessage.isPending}
          >
            {updateMessage.isPending ? "Saving…" : "Save draft"}
          </button>
        </form>
      ) : (
        <div className="mt-6 rounded-lg border border-line bg-paper p-5">
          <h2 className="text-sm font-semibold text-moss">Message</h2>
          <p className="mt-2 whitespace-pre-wrap">{message.body}</p>
        </div>
      )}
      {message.contact_id ? (
        <Link
          to={`/contacts/${message.contact_id}`}
          className="mt-4 inline-block font-semibold text-pine underline"
        >
          View contact
        </Link>
      ) : null}
    </section>
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

function readNotice(state: unknown): string | null {
  if (typeof state !== "object" || state === null || !("notice" in state)) {
    return null
  }
  return typeof state.notice === "string" ? state.notice : null
}
