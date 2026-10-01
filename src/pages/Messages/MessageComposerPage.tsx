import { useEffect } from "react"
import { zodResolver } from "@hookform/resolvers/zod"
import { useForm } from "react-hook-form"
import { Link, useNavigate, useSearchParams } from "react-router-dom"
import { z } from "zod"
import { ApiError } from "../../api/client.ts"
import { EmptyState } from "../../components/common/EmptyState.tsx"
import { ErrorState } from "../../components/common/ErrorState.tsx"
import { Field, fieldClass } from "../../components/common/Field.tsx"
import { LoadingState } from "../../components/common/LoadingState.tsx"
import { useContact, useCreateMessage } from "../../hooks/useCrm.ts"
import { useSession } from "../../hooks/useSession.ts"
import { displayUsPhone } from "../../lib/utils.ts"

const schema = z
  .object({
    message_type: z.enum(["email", "sms"]),
    subject: z.string().trim().max(200),
    body: z.string().trim().min(1, "Message is required.").max(5000),
  })
  .superRefine((values, context) => {
    if (values.message_type === "email" && !values.subject) {
      context.addIssue({
        code: "custom",
        path: ["subject"],
        message: "Subject is required for email.",
      })
    }
  })

type ComposerValues = z.infer<typeof schema>

export function MessageComposerPage() {
  const session = useSession()
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const companyId = session.activeCompany?.id ?? null
  const contactId = params.get("contact") ?? ""
  const requestedType = params.get("type") === "sms" ? "sms" : "email"
  const contactQuery = useContact(companyId, contactId)
  const createMessage = useCreateMessage(companyId ?? "")
  const form = useForm<ComposerValues>({
    resolver: zodResolver(schema),
    defaultValues: { message_type: requestedType, subject: "", body: "" },
  })
  const messageType = form.watch("message_type")
  const body = form.watch("body")
  const contact = contactQuery.data

  useEffect(() => {
    if (!contact) {
      return
    }
    if (messageType === "email" && !contact.email && contact.phone) {
      form.setValue("message_type", "sms")
    }
    if (messageType === "sms" && !contact.phone && contact.email) {
      form.setValue("message_type", "email")
    }
  }, [contact, form, messageType])

  if (!companyId) {
    return <EmptyState title="No company selected" message="Choose a company before writing a message." />
  }
  if (!contactId) {
    return (
      <EmptyState
        title="Choose a contact"
        message="Open a contact and use Send email or Send SMS. Messages are written to one person."
      />
    )
  }
  if (contactQuery.isPending) {
    return <LoadingState label="Loading contact" />
  }
  if (contactQuery.isError || !contact) {
    return (
      <ErrorState
        message={
          contactQuery.error instanceof ApiError
            ? contactQuery.error.message
            : "Contact could not be loaded."
        }
      />
    )
  }

  const emailReady = Boolean(contact.email)
  const smsReady = Boolean(contact.phone)
  const selectedReady = messageType === "email" ? emailReady : smsReady
  const destination =
    messageType === "email"
      ? contact.email
      : displayUsPhone(contact.phone)
  const message =
    createMessage.error instanceof ApiError
      ? createMessage.error.message
      : createMessage.error
        ? "The message could not be saved."
        : null

  return (
    <section className="mx-auto max-w-3xl">
      <Link to={`/contacts/${contact.id}`} className="text-sm font-semibold text-pine underline">
        Back to contact
      </Link>
      <h1 className="mt-3 font-display text-4xl">Send message</h1>
      <p className="mt-2 text-pine">
        To {contact.first_name} {contact.last_name}
        {destination ? ` · ${destination}` : ""}
      </p>
      <form
        className="mt-6 grid gap-4"
        noValidate
        onSubmit={form.handleSubmit(async (values, event) => {
          const submitter = event?.nativeEvent instanceof SubmitEvent ? event.nativeEvent.submitter : null
          const deliver = submitter instanceof HTMLButtonElement && submitter.value === "send"
          const result = await createMessage.mutateAsync({
            contact_id: contact.id,
            message_type: values.message_type,
            subject: values.message_type === "email" ? values.subject.trim() : null,
            body: values.body.trim(),
            deliver,
          })
          const notice =
            result.provider_status === "unavailable"
              ? "Saved as a draft. No email or SMS provider is configured, so it was not sent."
              : "Draft saved."
          void navigate(`/messages/${result.message.id}`, { state: { notice } })
        })}
      >
        {message ? (
          <p className="rounded-md border border-danger/30 bg-paper px-4 py-3 text-sm" role="alert">
            {message}
          </p>
        ) : null}
        <Field id="message_type" label="Type" error={form.formState.errors.message_type?.message}>
          <select id="message_type" className={fieldClass} {...form.register("message_type")}>
            <option value="email" disabled={!emailReady}>
              Email
            </option>
            <option value="sms" disabled={!smsReady}>
              SMS
            </option>
          </select>
        </Field>
        {!selectedReady ? (
          <p className="text-sm text-pine" role="status">
            {messageType === "email"
              ? "This contact has no email address."
              : "This contact has no phone number."}
          </p>
        ) : null}
        {messageType === "email" ? (
          <Field id="subject" label="Subject" error={form.formState.errors.subject?.message}>
            <input
              id="subject"
              className={fieldClass}
              aria-invalid={Boolean(form.formState.errors.subject)}
              {...form.register("subject")}
            />
          </Field>
        ) : null}
        <Field id="body" label="Message" error={form.formState.errors.body?.message}>
          <textarea
            id="body"
            rows={6}
            className={fieldClass}
            aria-invalid={Boolean(form.formState.errors.body)}
            {...form.register("body")}
          />
        </Field>
        {messageType === "sms" ? (
          <p className="text-sm text-pine">{body.trim().length} characters</p>
        ) : null}
        <div className="flex flex-wrap gap-3">
          <button
            type="submit"
            className="rounded-md border border-line bg-paper px-4 py-2 font-semibold disabled:opacity-60"
            value="draft"
            disabled={createMessage.isPending || !selectedReady}
          >
            Save draft
          </button>
          <button
            type="submit"
            className="rounded-md bg-copper px-4 py-2 font-semibold text-paper disabled:opacity-60"
            value="send"
            disabled={createMessage.isPending || !selectedReady}
          >
            {createMessage.isPending ? "Saving…" : "Send"}
          </button>
        </div>
      </form>
    </section>
  )
}
