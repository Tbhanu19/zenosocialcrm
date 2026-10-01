import { useState } from "react"
import { Link, useLocation, useParams } from "react-router-dom"
import { ApiError } from "../../api/client.ts"
import { canManageContacts } from "../../auth/permissions.ts"
import { Dialog } from "../../components/common/Dialog.tsx"
import { EmptyState } from "../../components/common/EmptyState.tsx"
import { ErrorState } from "../../components/common/ErrorState.tsx"
import { LoadingState } from "../../components/common/LoadingState.tsx"
import { useContact, useContactMessages, useUpdateContact } from "../../hooks/useCrm.ts"
import { useSession } from "../../hooks/useSession.ts"
import { displayUsPhone, formatCalendarDate, formatDate, roleLabel } from "../../lib/utils.ts"
import type { ContactRecord, MessageListItem } from "../../types/crm.ts"

const previewFilters = {
  page: 1,
  pageSize: 10,
  search: "",
  messageType: "",
  status: "",
  contactId: "",
}

export function ContactDetailPage() {
  const { contactId = "" } = useParams()
  const location = useLocation()
  const session = useSession()
  const companyId = session.activeCompany?.id ?? null
  const canManage = canManageContacts(session.navRole)
  const contactQuery = useContact(companyId, contactId)
  const messageFilters = { ...previewFilters, contactId }
  const messagesQuery = useContactMessages(companyId, contactId, messageFilters)
  const updateContact = useUpdateContact(companyId ?? "", contactId)
  const [confirmArchive, setConfirmArchive] = useState(false)
  const notice = readNotice(location.state)

  if (!companyId) {
    return <EmptyState title="No company selected" message="Choose a company to view this contact." />
  }
  if (contactQuery.isPending) {
    return <LoadingState label="Loading contact" />
  }
  if (contactQuery.isError || !contactQuery.data) {
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

  const contact = contactQuery.data
  const archived = contact.status === "archived"

  return (
    <section className="mx-auto max-w-3xl">
      <Link to="/contacts" className="text-sm font-semibold text-pine underline">
        Back to contacts
      </Link>
      <div className="mt-3 flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-sm font-semibold tracking-[0.12em] text-copper uppercase">Contact</p>
          <h1 className="mt-2 font-display text-4xl">
            {contact.first_name} {contact.last_name}
          </h1>
        </div>
        <div className="flex flex-wrap gap-2">
          {canManage ? (
            <Link
              to={`/contacts/${contact.id}/edit`}
              className="rounded-md border border-line bg-paper px-4 py-2 font-semibold"
            >
              Edit
            </Link>
          ) : null}
          {canManage && !archived ? (
            <button
              type="button"
              className="rounded-md border border-line bg-paper px-4 py-2 font-semibold"
              onClick={() => setConfirmArchive(true)}
            >
              Archive
            </button>
          ) : null}
          {canManage && archived ? (
            <button
              type="button"
              className="rounded-md border border-line bg-paper px-4 py-2 font-semibold"
              disabled={updateContact.isPending}
              onClick={() => {
                void updateContact.mutateAsync({ status: "active" })
              }}
            >
              Restore
            </button>
          ) : null}
        </div>
      </div>
      {notice ? (
        <p className="mt-4 rounded-md border border-line bg-paper px-4 py-3 text-sm" role="status">
          {notice}
        </p>
      ) : null}
      {updateContact.error ? (
        <p className="mt-4 text-sm text-danger" role="alert">
          {updateContact.error instanceof ApiError
            ? updateContact.error.message
            : "The contact could not be updated."}
        </p>
      ) : null}
      <dl className="mt-6 grid gap-4 rounded-lg border border-line bg-paper p-5 sm:grid-cols-2">
        <Info label="Email" value={contact.email} />
        <Info label="Phone" value={displayUsPhone(contact.phone)} />
        <Info label="Company" value={contact.company_name} />
        <Info label="Address" value={formatAddress(contact)} />
        <Info label="Source" value={roleLabel(contact.source)} />
        <Info label="Opted in" value={contact.opted_in ? "Yes" : "No"} />
        <Info label="Date" value={contact.contact_date ? formatCalendarDate(contact.contact_date) : null} />
        <Info label="Status" value={roleLabel(contact.status)} />
        <Info label="Assigned user" value={contact.assignee_name} />
        <Info label="Created" value={formatDate(contact.created_at)} />
        <Info label="Updated" value={formatDate(contact.updated_at)} />
      </dl>
      {contact.notes ? (
        <div className="mt-4 rounded-lg border border-line bg-paper p-5">
          <h2 className="text-sm font-semibold text-moss">Notes</h2>
          <p className="mt-2 whitespace-pre-wrap">{contact.notes}</p>
        </div>
      ) : null}
      <div className="mt-4 flex flex-wrap gap-2">
        {contact.email ? (
          <Link
            to={`/messages/new?contact=${contact.id}&type=email`}
            className="rounded-md bg-copper px-4 py-2 font-semibold text-paper"
          >
            Send email
          </Link>
        ) : (
          <p className="text-sm text-pine">Add an email address before sending email.</p>
        )}
        {contact.phone ? (
          <Link
            to={`/messages/new?contact=${contact.id}&type=sms`}
            className="rounded-md border border-line bg-paper px-4 py-2 font-semibold"
          >
            Send SMS
          </Link>
        ) : (
          <p className="text-sm text-pine">Add a phone number before sending SMS.</p>
        )}
      </div>
      <h2 className="mt-8 font-display text-2xl">Messages</h2>
      <MessagePreview
        isPending={messagesQuery.isPending}
        isError={messagesQuery.isError}
        error={messagesQuery.error}
        items={messagesQuery.data?.items}
        contactId={contact.id}
      />
      <Dialog open={confirmArchive} title="Archive contact" onClose={() => setConfirmArchive(false)}>
        <p className="text-sm text-pine">
          Archived contacts stay in history and leave the current list.
        </p>
        <div className="mt-4 flex justify-end gap-3">
          <button type="button" className="rounded-md px-3 py-2" onClick={() => setConfirmArchive(false)}>
            Cancel
          </button>
          <button
            type="button"
            className="rounded-md bg-copper px-4 py-2 font-semibold text-paper disabled:opacity-60"
            disabled={updateContact.isPending}
            onClick={() => {
              void updateContact.mutateAsync({ status: "archived" }).then(() => {
                setConfirmArchive(false)
              })
            }}
          >
            Archive
          </button>
        </div>
      </Dialog>
    </section>
  )
}

function MessagePreview({
  isPending,
  isError,
  error,
  items,
  contactId,
}: {
  isPending: boolean
  isError: boolean
  error: unknown
  items: MessageListItem[] | undefined
  contactId: string
}) {
  if (isPending) {
    return <LoadingState label="Loading messages" />
  }
  if (isError) {
    return (
      <div className="mt-3">
        <ErrorState
          message={error instanceof ApiError ? error.message : "Messages could not be loaded."}
        />
      </div>
    )
  }
  return (
    <div className="mt-3">
      {!items || items.length === 0 ? (
        <EmptyState title="No messages yet" message="Email and SMS drafts for this contact will show here." />
      ) : (
        <ul className="space-y-3">
          {items.map((message) => (
            <li key={message.id} className="rounded-lg border border-line bg-paper p-4">
              <p className="font-semibold">
                {roleLabel(message.message_type)} · {message.subject || "No subject"}
              </p>
              <p className="mt-1 text-sm text-pine">
                {roleLabel(message.status)} · {formatDate(message.created_at)}
              </p>
              <Link to={`/messages/${message.id}`} className="mt-2 inline-block font-semibold text-pine underline">
                View message
              </Link>
            </li>
          ))}
        </ul>
      )}
      <Link
        to={`/messages?contact=${contactId}`}
        className="mt-4 inline-block font-semibold text-pine underline"
      >
        View all messages
      </Link>
    </div>
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

function formatAddress(contact: ContactRecord): string | null {
  const parts = [contact.address, contact.city, contact.state, contact.zip_code].filter(Boolean)
  return parts.length > 0 ? parts.join(", ") : null
}

function readNotice(state: unknown): string | null {
  if (typeof state !== "object" || state === null || !("notice" in state)) {
    return null
  }
  return typeof state.notice === "string" ? state.notice : null
}
