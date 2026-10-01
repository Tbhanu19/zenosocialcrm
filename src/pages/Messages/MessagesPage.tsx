import { useEffect, useMemo, useState } from "react"
import { useSearchParams } from "react-router-dom"
import { ApiError } from "../../api/client.ts"
import { EmptyState } from "../../components/common/EmptyState.tsx"
import { ErrorState } from "../../components/common/ErrorState.tsx"
import { fieldClass } from "../../components/common/Field.tsx"
import { LoadingState } from "../../components/common/LoadingState.tsx"
import {
  useContact,
  useContacts,
  useCreateMessage,
  useMessages,
} from "../../hooks/useCrm.ts"
import { useDebouncedValue } from "../../hooks/useDebouncedValue.ts"
import { usePagedFilters } from "../../hooks/usePagedFilters.ts"
import { useSession } from "../../hooks/useSession.ts"
import {
  displayUsPhone,
  formatCalendarDate,
  formatDate,
  roleLabel,
} from "../../lib/utils.ts"
import type { ContactListItem, MessageListItem } from "../../types/crm.ts"

const CONTACT_PAGE_SIZE = 25
const THREAD_PAGE_SIZE = 100

export function MessagesPage() {
  const session = useSession()
  const companyId = session.activeCompany?.id ?? null
  const [params, setParams] = useSearchParams()
  const selectedContactId = params.get("contact") ?? ""
  const [searchInput, setSearchInput] = useState("")
  const search = useDebouncedValue(searchInput, 400).trim()
  const contactPaging = usePagedFilters(`${companyId ?? ""}|${search}`)
  const contactsQuery = useContacts(companyId, {
    page: contactPaging.page,
    pageSize: CONTACT_PAGE_SIZE,
    search,
    status: "",
    source: "",
    assignedTo: "",
  })
  const selectedContactQuery = useContact(
    selectedContactId ? companyId : null,
    selectedContactId,
  )
  const threadQuery = useMessages(
    companyId,
    {
      page: 1,
      pageSize: THREAD_PAGE_SIZE,
      search: "",
      messageType: "",
      status: "",
      contactId: selectedContactId,
    },
    Boolean(selectedContactId),
  )

  function selectContact(contactId: string) {
    const updated = new URLSearchParams(params)
    if (contactId) {
      updated.set("contact", contactId)
    } else {
      updated.delete("contact")
    }
    setParams(updated)
  }

  if (!companyId) {
    return (
      <EmptyState
        title="No organisation selected"
        message="Choose an organisation in the header to open messages."
      />
    )
  }

  const contacts = contactsQuery.data?.items ?? []
  const totalContacts = contactsQuery.data?.total ?? 0
  const totalPages = contactsQuery.data?.total_pages ?? 0
  const page = contactsQuery.data?.page ?? contactPaging.page
  const rangeStart = totalContacts === 0 ? 0 : (page - 1) * CONTACT_PAGE_SIZE + 1
  const rangeEnd = Math.min(page * CONTACT_PAGE_SIZE, totalContacts)

  return (
    <section className="flex min-h-[calc(100dvh-8rem)] flex-1 flex-col md:min-h-0">
      <div className="mb-4 shrink-0">
        <p className="text-sm font-semibold tracking-[0.12em] text-copper uppercase">Messages</p>
        <h1 className="mt-2 font-display text-4xl">Messages</h1>
        <p className="mt-2 text-pine">
          Conversations for {session.activeCompany?.name ?? "the selected organisation"}.
        </p>
      </div>

      <div className="grid min-h-0 w-full flex-1 overflow-hidden rounded-xl border border-line bg-paper lg:grid-cols-[22rem_minmax(0,1fr)]">
        <aside className="flex min-h-[22rem] flex-col border-b border-line lg:min-h-0 lg:h-full lg:border-r lg:border-b-0">
          <div className="border-b border-line px-4 py-3 shrink-0">
            <h2 className="font-display text-2xl">Contacts</h2>
            <label className="mt-3 block">
              <span className="sr-only">Search contacts</span>
              <input
                className={fieldClass}
                value={searchInput}
                onChange={(event) => setSearchInput(event.target.value)}
                placeholder="Search conversations…"
              />
            </label>
          </div>

          <div className="min-h-0 flex-1 overflow-y-auto">
            {contactsQuery.isPending ? <LoadingState label="Loading contacts" /> : null}
            {contactsQuery.isError ? (
              <div className="p-4">
                <ErrorState
                  message={
                    contactsQuery.error instanceof ApiError
                      ? contactsQuery.error.message
                      : "Contacts could not be loaded."
                  }
                />
              </div>
            ) : null}
            {!contactsQuery.isPending && !contactsQuery.isError && contacts.length === 0 ? (
              <div className="p-4">
                <EmptyState
                  title={search ? "No contacts match your search." : "No contacts yet."}
                  message={
                    search
                      ? "Try a different phone number or name."
                      : "Add contacts first, then message them here."
                  }
                />
              </div>
            ) : null}
            <ul>
              {contacts.map((contact) => (
                <li key={contact.id}>
                  <button
                    type="button"
                    className={`flex w-full items-start gap-3 border-b border-line px-4 py-3 text-left transition hover:bg-cream/70 ${
                      selectedContactId === contact.id ? "bg-cream" : "bg-paper"
                    }`}
                    onClick={() => selectContact(contact.id)}
                  >
                    <span
                      className="mt-0.5 grid h-10 w-10 shrink-0 place-items-center rounded-full bg-copper/15 text-sm font-semibold text-copper"
                      aria-hidden="true"
                    >
                      {avatarDigits(contact.phone)}
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="flex items-start justify-between gap-2">
                        <span className="truncate font-semibold">
                          {displayUsPhone(contact.phone) ||
                            `${contact.first_name} ${contact.last_name}`}
                        </span>
                        <span className="shrink-0 text-xs text-pine">
                          {contact.contact_date
                            ? formatCalendarDate(contact.contact_date)
                            : formatDate(contact.created_at)}
                        </span>
                      </span>
                      <span className="mt-1 block truncate text-sm text-pine">
                        {roleLabel(contact.source)}
                        {contact.opted_in ? " · Opted in" : " · Not opted in"}
                      </span>
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          </div>

          <div className="border-t border-line px-4 py-3 shrink-0">
            <p className="text-xs text-pine">
              Showing {rangeStart}–{rangeEnd} of {totalContacts}
              {totalPages > 0 ? ` (page ${page} of ${totalPages})` : ""}
            </p>
            <div className="mt-2 flex gap-2">
              <button
                type="button"
                className="rounded-md border border-line px-3 py-1.5 text-sm font-semibold uppercase disabled:opacity-50"
                disabled={page <= 1 || contactsQuery.isPending}
                onClick={() => contactPaging.setPage(page - 1)}
              >
                Previous
              </button>
              <button
                type="button"
                className="rounded-md border border-line px-3 py-1.5 text-sm font-semibold uppercase disabled:opacity-50"
                disabled={page >= totalPages || contactsQuery.isPending || totalPages === 0}
                onClick={() => contactPaging.setPage(page + 1)}
              >
                Next
              </button>
            </div>
          </div>
        </aside>

        <ChatPane
          companyId={companyId}
          contactId={selectedContactId}
          contact={selectedContactQuery.data}
          contactPending={Boolean(selectedContactId) && selectedContactQuery.isPending}
          contactError={selectedContactQuery.error}
          messages={threadQuery.data?.items}
          messagesPending={Boolean(selectedContactId) && threadQuery.isPending}
          messagesError={threadQuery.error}
          onClear={() => selectContact("")}
        />
      </div>
    </section>
  )
}

function ChatPane({
  companyId,
  contactId,
  contact,
  contactPending,
  contactError,
  messages,
  messagesPending,
  messagesError,
  onClear,
}: {
  companyId: string
  contactId: string
  contact: ContactListItem | undefined
  contactPending: boolean
  contactError: unknown
  messages: MessageListItem[] | undefined
  messagesPending: boolean
  messagesError: unknown
  onClear: () => void
}) {
  const createMessage = useCreateMessage(companyId)
  const [draft, setDraft] = useState("")
  const [sendError, setSendError] = useState("")

  useEffect(() => {
    setDraft("")
    setSendError("")
  }, [contactId])

  const chronological = useMemo(() => {
    if (!messages) {
      return []
    }
    return [...messages].reverse()
  }, [messages])

  if (!contactId) {
    return (
      <div className="grid h-full min-h-[22rem] place-items-center px-8 py-12 text-center">
        <div>
          <h2 className="font-display text-2xl">Select a contact</h2>
          <p className="mt-2 text-pine">Choose a contact from the list to view and send messages.</p>
        </div>
      </div>
    )
  }

  if (contactPending) {
    return <LoadingState label="Loading conversation" />
  }

  if (contactError || !contact) {
    return (
      <div className="p-6">
        <ErrorState
          message={
            contactError instanceof ApiError
              ? contactError.message
              : "Contact could not be loaded."
          }
        />
        <button type="button" className="mt-4 font-semibold text-pine underline" onClick={onClear}>
          Back to list
        </button>
      </div>
    )
  }

  const phoneLabel = displayUsPhone(contact.phone) || `${contact.first_name} ${contact.last_name}`
  const canSms = Boolean(contact.phone)
  const canEmail = Boolean(contact.email)

  return (
    <div className="flex h-full min-h-[22rem] flex-col lg:min-h-0">
      <div className="flex shrink-0 flex-wrap items-center justify-between gap-3 border-b border-line px-5 py-4">
        <div>
          <h2 className="font-display text-2xl">{phoneLabel}</h2>
          <p className="mt-1 text-sm text-pine">
            {roleLabel(contact.source)}
            {contact.opted_in ? " · Opted in" : " · Not opted in"}
          </p>
        </div>
        <button type="button" className="text-sm font-semibold text-pine underline" onClick={onClear}>
          Close
        </button>
      </div>

      <div className="min-h-0 flex-1 space-y-4 overflow-y-auto bg-cream/40 px-5 py-4">
        {messagesPending ? <LoadingState label="Loading messages" /> : null}
        {messagesError ? (
          <ErrorState
            message={
              messagesError instanceof ApiError
                ? messagesError.message
                : "Messages could not be loaded."
            }
          />
        ) : null}
        {!messagesPending && !messagesError && chronological.length === 0 ? (
          <p className="text-sm text-pine">No messages yet. Send the first one below.</p>
        ) : null}
        {chronological.map((message) => (
          <div
            key={message.id}
            className={`flex ${message.direction === "outbound" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm ${
                message.direction === "outbound"
                  ? "bg-copper text-paper"
                  : "border border-line bg-paper text-ink"
              }`}
            >
              {message.subject ? <p className="mb-1 font-semibold">{message.subject}</p> : null}
              <p className="whitespace-pre-wrap">{message.body}</p>
              <p
                className={`mt-2 text-xs ${
                  message.direction === "outbound" ? "text-paper/80" : "text-pine"
                }`}
              >
                {formatDate(message.created_at)} · {roleLabel(message.message_type)} ·{" "}
                {roleLabel(message.status)}
              </p>
            </div>
          </div>
        ))}
      </div>

      <form
        className="shrink-0 border-t border-line px-4 py-3"
        onSubmit={(event) => {
          event.preventDefault()
          const body = draft.trim()
          if (!body) {
            return
          }
          if (!canSms && !canEmail) {
            setSendError("This contact has no phone or email.")
            return
          }
          setSendError("")
          const messageType = canSms ? "sms" : "email"
          void createMessage
            .mutateAsync({
              contact_id: contact.id,
              message_type: messageType,
              subject: messageType === "email" ? "Message" : null,
              body,
              deliver: true,
            })
            .then(() => setDraft(""))
            .catch((error: unknown) => {
              setSendError(
                error instanceof ApiError ? error.message : "The message could not be sent.",
              )
            })
        }}
      >
        {sendError ? (
          <p className="mb-2 text-sm text-danger" role="alert">
            {sendError}
          </p>
        ) : null}
        {!canSms && !canEmail ? (
          <p className="mb-2 text-sm text-pine">Add a phone or email on the contact to send messages.</p>
        ) : null}
        <div className="flex items-end gap-2">
          <textarea
            className={`${fieldClass} min-h-[2.75rem] resize-none`}
            rows={2}
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            placeholder="Type a message…"
            disabled={createMessage.isPending || (!canSms && !canEmail)}
          />
          <button
            type="submit"
            className="grid h-11 w-11 shrink-0 place-items-center rounded-full bg-copper text-paper disabled:opacity-60"
            disabled={createMessage.isPending || !draft.trim() || (!canSms && !canEmail)}
            aria-label="Send message"
          >
            <SendIcon />
          </button>
        </div>
      </form>
    </div>
  )
}

function avatarDigits(phone: string | null): string {
  const digits = (phone ?? "").replace(/\D/g, "")
  if (digits.length >= 2) {
    return digits.slice(-2)
  }
  return "?"
}

function SendIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-5 w-5" fill="currentColor" aria-hidden="true">
      <path d="M3.4 20.6 21 12 3.4 3.4 3.4 10.2 15 12 3.4 13.8z" />
    </svg>
  )
}
