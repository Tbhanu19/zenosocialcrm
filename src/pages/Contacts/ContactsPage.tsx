import { useState } from "react"
import { Link } from "react-router-dom"
import { zodResolver } from "@hookform/resolvers/zod"
import { useForm } from "react-hook-form"
import { z } from "zod"
import { ApiError } from "../../api/client.ts"
import { canManageContacts } from "../../auth/permissions.ts"
import { Dialog } from "../../components/common/Dialog.tsx"
import { EmptyState } from "../../components/common/EmptyState.tsx"
import { ErrorState } from "../../components/common/ErrorState.tsx"
import { Field, fieldClass } from "../../components/common/Field.tsx"
import { LoadingState } from "../../components/common/LoadingState.tsx"
import { Pagination } from "../../components/common/Pagination.tsx"
import { UsPhoneInput } from "../../components/common/UsPhoneInput.tsx"
import { useAssignees, useContacts, useCreateContact, useDeleteContact } from "../../hooks/useCrm.ts"
import { useDebouncedValue } from "../../hooks/useDebouncedValue.ts"
import { usePagedFilters } from "../../hooks/usePagedFilters.ts"
import { useSession } from "../../hooks/useSession.ts"
import { displayUsPhone, formatCalendarDate, isUsPhone, roleLabel } from "../../lib/utils.ts"
import type { ContactListItem } from "../../types/crm.ts"
import { CONTACT_SOURCES } from "../../types/crm.ts"

const PAGE_SIZE = 20

const quickSchema = z.object({
  phone: z
    .string()
    .refine((value) => value.trim().length > 0, "Phone is required.")
    .refine(isUsPhone, "Enter a US phone number, such as (214) 555-0100."),
  source: z.enum(["manual", "website", "import", "campaign", "referral", "other"]),
  opted_in: z.enum(["yes", "no"]),
  contact_date: z.string().min(1, "Date is required."),
})

type QuickFormValues = z.infer<typeof quickSchema>

function todayInputValue(): string {
  const now = new Date()
  const month = String(now.getMonth() + 1).padStart(2, "0")
  const day = String(now.getDate()).padStart(2, "0")
  return `${now.getFullYear()}-${month}-${day}`
}

const emptyQuickForm: QuickFormValues = {
  phone: "",
  source: "manual",
  opted_in: "yes",
  contact_date: todayInputValue(),
}

export function ContactsPage() {
  const session = useSession()
  const companyId = session.activeCompany?.id ?? null
  const canManage = canManageContacts(session.navRole)
  const [searchInput, setSearchInput] = useState("")
  const [status, setStatus] = useState("")
  const [source, setSource] = useState("")
  const [assignedTo, setAssignedTo] = useState("")
  const [pendingDelete, setPendingDelete] = useState<ContactListItem | null>(null)
  const [deleteError, setDeleteError] = useState("")
  const search = useDebouncedValue(searchInput, 400).trim()
  const filters = usePagedFilters(`${companyId ?? ""}|${search}|${status}|${source}|${assignedTo}`)
  const listFilters = {
    page: filters.page,
    pageSize: PAGE_SIZE,
    search,
    status,
    source,
    assignedTo,
  }
  const contactsQuery = useContacts(companyId, listFilters)
  const assigneesQuery = useAssignees(companyId)
  const createContact = useCreateContact(companyId ?? "")
  const deleteContact = useDeleteContact(companyId ?? "")
  const form = useForm<QuickFormValues>({
    resolver: zodResolver(quickSchema),
    defaultValues: emptyQuickForm,
  })

  return (
    <section>
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-sm font-semibold tracking-[0.12em] text-copper uppercase">Contacts</p>
          <h1 className="mt-2 font-display text-4xl">Contacts</h1>
          <p className="mt-2 text-pine">
            People for {session.activeCompany?.name ?? "the selected company"}.
          </p>
        </div>
      </div>

      {canManage && companyId ? (
        <div className="mt-6 rounded-xl border border-line bg-paper p-5 shadow-sm">
          <h2 className="font-display text-2xl">Add contact</h2>
          <form
            className="mt-4 grid gap-4 sm:grid-cols-2"
            noValidate
            onSubmit={form.handleSubmit(async (values) => {
              const digits = values.phone.replace(/\D/g, "")
              await createContact.mutateAsync({
                first_name: "Contact",
                last_name: digits.slice(-4) || "Phone",
                email: null,
                phone: values.phone.trim(),
                company_name: null,
                address: null,
                city: null,
                state: null,
                zip_code: null,
                source: values.source,
                status: "active",
                opted_in: values.opted_in === "yes",
                contact_date: values.contact_date,
                notes: null,
                assigned_to_user_id: null,
              })
              form.reset({ ...emptyQuickForm, contact_date: todayInputValue() })
            })}
          >
            <Field id="quick-phone" label="Phone" error={form.formState.errors.phone?.message}>
              <UsPhoneInput id="quick-phone" registration={form.register("phone")} />
            </Field>
            <Field id="quick-source" label="Source" error={form.formState.errors.source?.message}>
              <select id="quick-source" className={fieldClass} {...form.register("source")}>
                {CONTACT_SOURCES.map((item) => (
                  <option key={item} value={item}>
                    {roleLabel(item)}
                  </option>
                ))}
              </select>
            </Field>
            <Field id="quick-opted-in" label="Opted in" error={form.formState.errors.opted_in?.message}>
              <select id="quick-opted-in" className={fieldClass} {...form.register("opted_in")}>
                <option value="yes">Yes</option>
                <option value="no">No</option>
              </select>
            </Field>
            <Field
              id="quick-contact-date"
              label="Date"
              error={form.formState.errors.contact_date?.message}
            >
              <input
                id="quick-contact-date"
                type="date"
                className={fieldClass}
                {...form.register("contact_date")}
              />
            </Field>
            {createContact.error ? (
              <p className="text-sm text-danger sm:col-span-2" role="alert">
                {createContact.error instanceof ApiError
                  ? createContact.error.message
                  : "The contact could not be saved."}
              </p>
            ) : null}
            <div className="sm:col-span-2">
              <button
                type="submit"
                className="rounded-md bg-copper px-5 py-2.5 font-semibold uppercase tracking-wide text-paper disabled:opacity-60"
                disabled={createContact.isPending}
              >
                {createContact.isPending ? "Saving…" : "Add contact"}
              </button>
            </div>
          </form>
        </div>
      ) : null}

      <div className="mt-6 grid gap-3 md:grid-cols-4">
        <input
          className={fieldClass}
          value={searchInput}
          onChange={(event) => setSearchInput(event.target.value)}
          placeholder="Search contacts"
          aria-label="Search contacts"
        />
        <select
          className={fieldClass}
          aria-label="Status"
          value={status}
          onChange={(event) => setStatus(event.target.value)}
        >
          <option value="">All current</option>
          <option value="active">Active</option>
          <option value="inactive">Inactive</option>
          <option value="archived">Archived</option>
        </select>
        <select
          className={fieldClass}
          aria-label="Source"
          value={source}
          onChange={(event) => setSource(event.target.value)}
        >
          <option value="">All sources</option>
          {CONTACT_SOURCES.map((item) => (
            <option key={item} value={item}>
              {roleLabel(item)}
            </option>
          ))}
        </select>
        <select
          className={fieldClass}
          aria-label="Assigned user"
          value={assignedTo}
          onChange={(event) => setAssignedTo(event.target.value)}
        >
          <option value="">Anyone</option>
          {(assigneesQuery.data?.items ?? []).map((person) => (
            <option key={person.id} value={person.id}>
              {person.first_name} {person.last_name}
            </option>
          ))}
        </select>
      </div>
      {!companyId ? (
        <div className="mt-6">
          <EmptyState title="No company selected" message="Choose a company in the header to see its contacts." />
        </div>
      ) : (
        <ContactResults
          isPending={contactsQuery.isPending}
          isError={contactsQuery.isError}
          error={contactsQuery.error}
          items={contactsQuery.data?.items}
          total={contactsQuery.data?.total ?? 0}
          page={contactsQuery.data?.page ?? filters.page}
          totalPages={contactsQuery.data?.total_pages ?? 0}
          filtered={Boolean(search || status || source || assignedTo)}
          canManage={canManage}
          onPage={filters.setPage}
          onDelete={(contact) => {
            setDeleteError("")
            setPendingDelete(contact)
          }}
        />
      )}
      <Dialog
        open={Boolean(pendingDelete)}
        title="Delete contact"
        onClose={() => {
          if (!deleteContact.isPending) {
            setPendingDelete(null)
            setDeleteError("")
          }
        }}
      >
        <p className="text-sm text-pine">
          Delete {displayUsPhone(pendingDelete?.phone) || pendingDelete?.first_name}? This cannot be
          undone.
        </p>
        {deleteError ? (
          <p className="mt-3 text-sm text-danger" role="alert">
            {deleteError}
          </p>
        ) : null}
        <div className="mt-4 flex justify-end gap-3">
          <button
            type="button"
            className="rounded-md border border-line bg-paper px-4 py-2 font-semibold"
            disabled={deleteContact.isPending}
            onClick={() => {
              setPendingDelete(null)
              setDeleteError("")
            }}
          >
            Cancel
          </button>
          <button
            type="button"
            className="rounded-md bg-danger px-4 py-2 font-semibold text-paper disabled:opacity-60"
            disabled={deleteContact.isPending || !pendingDelete}
            onClick={() => {
              if (!pendingDelete) {
                return
              }
              void deleteContact
                .mutateAsync(pendingDelete.id)
                .then(() => {
                  setPendingDelete(null)
                  setDeleteError("")
                })
                .catch((error: unknown) => {
                  setDeleteError(
                    error instanceof ApiError
                      ? error.message
                      : "The contact could not be deleted.",
                  )
                })
            }}
          >
            {deleteContact.isPending ? "Deleting…" : "Delete"}
          </button>
        </div>
      </Dialog>
    </section>
  )
}

function ContactResults({
  isPending,
  isError,
  error,
  items,
  total,
  page,
  totalPages,
  filtered,
  canManage,
  onPage,
  onDelete,
}: {
  isPending: boolean
  isError: boolean
  error: unknown
  items: ContactListItem[] | undefined
  total: number
  page: number
  totalPages: number
  filtered: boolean
  canManage: boolean
  onPage: (page: number) => void
  onDelete: (contact: ContactListItem) => void
}) {
  if (isPending) {
    return <LoadingState label="Loading contacts" />
  }
  if (isError) {
    return (
      <div className="mt-6">
        <ErrorState message={error instanceof ApiError ? error.message : "Contacts could not be loaded."} />
      </div>
    )
  }
  if (!items || items.length === 0) {
    return (
      <div className="mt-6">
        <EmptyState
          title={filtered ? "No contacts match these filters." : "No contacts yet."}
          message={
            filtered
              ? "Try a different name, email, phone, status, or source."
              : canManage
                ? "Add a contact above to start a record for this company."
                : "Contacts added by a manager will appear here."
          }
        />
      </div>
    )
  }

  return (
    <div className="mt-6">
      <p className="text-sm text-pine">{total} contacts</p>
      <div className="mt-3 hidden overflow-x-auto rounded-lg border border-line bg-paper md:block">
        <table className="w-full text-left text-sm">
          <caption className="sr-only">Contacts</caption>
          <thead className="border-b border-line text-moss">
            <tr>
              <th scope="col" className="px-4 py-3 font-semibold">Phone</th>
              <th scope="col" className="px-4 py-3 font-semibold">Source</th>
              <th scope="col" className="px-4 py-3 font-semibold">Opted in</th>
              <th scope="col" className="px-4 py-3 font-semibold">Date</th>
              <th scope="col" className="px-4 py-3 font-semibold">Name</th>
              <th scope="col" className="px-4 py-3 font-semibold">Actions</th>
            </tr>
          </thead>
          <tbody>
            {items.map((contact) => (
              <tr key={contact.id} className="border-t border-line">
                <td className="px-4 py-3">{displayUsPhone(contact.phone) || "—"}</td>
                <td className="px-4 py-3">{roleLabel(contact.source)}</td>
                <td className="px-4 py-3">{contact.opted_in ? "Yes" : "No"}</td>
                <td className="px-4 py-3">
                  {contact.contact_date ? formatCalendarDate(contact.contact_date) : "—"}
                </td>
                <td className="px-4 py-3 font-semibold">
                  {contact.first_name} {contact.last_name}
                </td>
                <td className="px-4 py-3">
                  <ContactActions
                    contact={contact}
                    canManage={canManage}
                    onDelete={() => onDelete(contact)}
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <ul className="mt-3 space-y-3 md:hidden">
        {items.map((contact) => (
          <li key={contact.id} className="rounded-lg border border-line bg-paper p-4">
            <p className="font-semibold">{displayUsPhone(contact.phone) || "No phone"}</p>
            <p className="mt-1 text-sm">
              {roleLabel(contact.source)} · Opted in: {contact.opted_in ? "Yes" : "No"}
            </p>
            <p className="mt-1 text-sm">
              {contact.contact_date ? formatCalendarDate(contact.contact_date) : "No date"} · {contact.first_name}{" "}
              {contact.last_name}
            </p>
            <div className="mt-3">
              <ContactActions
                contact={contact}
                canManage={canManage}
                onDelete={() => onDelete(contact)}
              />
            </div>
          </li>
        ))}
      </ul>
      <Pagination page={page} totalPages={totalPages} onPage={onPage} />
    </div>
  )
}

function ContactActions({
  contact,
  canManage,
  onDelete,
}: {
  contact: ContactListItem
  canManage: boolean
  onDelete: () => void
}) {
  return (
    <div className="flex flex-wrap gap-3">
      <Link to={`/contacts/${contact.id}`} className="font-semibold text-pine underline">
        View
      </Link>
      {canManage ? (
        <Link to={`/contacts/${contact.id}/edit`} className="font-semibold text-pine underline">
          Edit
        </Link>
      ) : null}
      {canManage ? (
        <button type="button" className="font-semibold text-danger underline" onClick={onDelete}>
          Delete
        </button>
      ) : null}
    </div>
  )
}
