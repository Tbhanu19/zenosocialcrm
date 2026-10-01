import { Link, useNavigate, useParams } from "react-router-dom"
import { canManageContacts } from "../../auth/permissions.ts"
import { ApiError } from "../../api/client.ts"
import { EmptyState } from "../../components/common/EmptyState.tsx"
import { ErrorState } from "../../components/common/ErrorState.tsx"
import { LoadingState } from "../../components/common/LoadingState.tsx"
import { useAssignees, useContact, useCreateContact, useUpdateContact } from "../../hooks/useCrm.ts"
import { useSession } from "../../hooks/useSession.ts"
import { ContactForm } from "./ContactForm.tsx"

export function ContactFormPage() {
  const { contactId = "" } = useParams()
  const navigate = useNavigate()
  const session = useSession()
  const companyId = session.activeCompany?.id ?? null
  const editing = Boolean(contactId)
  const canManage = canManageContacts(session.navRole)
  const contactQuery = useContact(canManage ? companyId : null, contactId)
  const assigneesQuery = useAssignees(companyId, canManage)
  const createContact = useCreateContact(companyId ?? "")
  const updateContact = useUpdateContact(companyId ?? "", contactId)

  if (!companyId) {
    return <EmptyState title="No company selected" message="Choose a company before editing contacts." />
  }
  if (!canManage) {
    return (
      <EmptyState
        title="Contacts are view only"
        message="Your role can view contacts. An owner or manager can change them."
      />
    )
  }
  if (editing && contactQuery.isPending) {
    return <LoadingState label="Loading contact" />
  }
  if (editing && (contactQuery.isError || !contactQuery.data)) {
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

  const pending = createContact.isPending || updateContact.isPending
  const error = editing ? updateContact.error : createContact.error

  return (
    <section className="mx-auto max-w-3xl">
      <Link
        to={editing ? `/contacts/${contactId}` : "/contacts"}
        className="text-sm font-semibold text-pine underline"
      >
        {editing ? "Back to contact" : "Back to contacts"}
      </Link>
      <h1 className="mt-3 font-display text-4xl">{editing ? "Edit contact" : "Add contact"}</h1>
      <p className="mt-2 text-pine">Saved for {session.activeCompany?.name}.</p>
      <ContactForm
        mode={editing ? "edit" : "create"}
        contact={contactQuery.data}
        assignees={assigneesQuery.data?.items ?? []}
        assigneeTotal={assigneesQuery.data?.total ?? 0}
        pending={pending}
        error={error}
        onSubmit={async (body) => {
          if (editing) {
            await updateContact.mutateAsync(body)
            void navigate(`/contacts/${contactId}`, { state: { notice: "Contact saved." } })
            return
          }
          const created = await createContact.mutateAsync(body)
          void navigate(`/contacts/${created.id}`, { state: { notice: "Contact added." } })
        }}
      />
    </section>
  )
}
