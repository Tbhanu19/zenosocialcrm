import { useState } from "react"
import { zodResolver } from "@hookform/resolvers/zod"
import { useForm } from "react-hook-form"
import { z } from "zod"
import { ApiError } from "../../api/client.ts"
import { assignableRoles, isUserRole, UserRole } from "../../auth/permissions.ts"
import { Dialog } from "../../components/common/Dialog.tsx"
import { EmptyState } from "../../components/common/EmptyState.tsx"
import { ErrorState } from "../../components/common/ErrorState.tsx"
import { Field, fieldClass } from "../../components/common/Field.tsx"
import { UsPhoneInput } from "../../components/common/UsPhoneInput.tsx"
import { LoadingState } from "../../components/common/LoadingState.tsx"
import { Pagination } from "../../components/common/Pagination.tsx"
import { useDebouncedValue } from "../../hooks/useDebouncedValue.ts"
import {
  useAdminUsers,
  useCompanyUsers,
  useCreateCompanyUser,
  useUpdateCompanyUser,
} from "../../hooks/useManagement.ts"
import { usePagedFilters } from "../../hooks/usePagedFilters.ts"
import { useSession } from "../../hooks/useSession.ts"
import { blankToNull, displayUsPhone, formatDate, formatUsPhone, isUsPhone, roleLabel } from "../../lib/utils.ts"
import type { AdminUserRow, CompanyMember, MemberUpdate, MembershipStatus } from "../../types/management.ts"

const PAGE_SIZE = 20

const memberSchema = z.object({
  first_name: z.string().trim().min(1, "First name is required.").max(100),
  last_name: z.string().trim().min(1, "Last name is required.").max(100),
  email: z.string().trim().email("Enter a valid email."),
  phone: z.string().refine(isUsPhone, "Enter a US phone number, such as (214) 555-0100."),
  role: z.string().min(1, "Role is required."),
  membership_status: z.enum(["active", "inactive"]),
})

type MemberFormValues = z.infer<typeof memberSchema>

export function UsersPage() {
  const session = useSession()
  const [searchInput, setSearchInput] = useState("")
  const [role, setRole] = useState("")
  const [status, setStatus] = useState("")
  const [scope, setScope] = useState<"company" | "all">("company")
  const [dialog, setDialog] = useState<"add" | "edit" | "view" | null>(null)
  const [selected, setSelected] = useState<AdminUserRow | CompanyMember | null>(null)
  const search = useDebouncedValue(searchInput, 400).trim()
  const companyId = session.activeCompany?.id ?? null
  const allCompanies = session.navRole === "super_admin" && scope === "all"
  const filters = usePagedFilters(`${search}|${role}|${status}|${scope}|${companyId ?? ""}`)
  const listFilters = {
    page: filters.page,
    pageSize: PAGE_SIZE,
    search,
    role,
    status,
  }
  const companyQuery = useCompanyUsers(companyId, listFilters, !allCompanies)
  const adminQuery = useAdminUsers(listFilters, allCompanies)
  const activeQuery = allCompanies ? adminQuery : companyQuery
  const roles = assignableRoles(session.navRole)
  const filterRoles = [
    UserRole.OWNER,
    UserRole.COMPANY_MANAGER,
    UserRole.MARKETING_MANAGER,
    UserRole.EMPLOYEE,
  ]
  const createUser = useCreateCompanyUser(companyId ?? "")
  const updateUser = useUpdateCompanyUser()

  function open(next: "add" | "edit" | "view", member: AdminUserRow | CompanyMember | null) {
    setSelected(member)
    setDialog(next)
  }

  return (
    <section>
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-sm font-semibold tracking-[0.12em] text-copper uppercase">
            User Management
          </p>
          <h1 className="mt-2 font-display text-4xl">Employees</h1>
          <p className="mt-2 text-pine">
            {allCompanies
              ? "People across every company."
              : `People in ${session.activeCompany?.name ?? "the selected company"}.`}
          </p>
        </div>
        {!allCompanies && companyId ? (
          <button
            type="button"
            className="rounded-md bg-copper px-4 py-2 font-semibold text-paper"
            onClick={() => open("add", null)}
          >
            Add employee
          </button>
        ) : null}
      </div>
      <div className="mt-6 grid gap-3 md:grid-cols-4">
        <input
          className={fieldClass}
          value={searchInput}
          onChange={(event) => setSearchInput(event.target.value)}
          placeholder="Search employees"
          aria-label="Search employees"
        />
        <select className={fieldClass} aria-label="Role" value={role} onChange={(event) => setRole(event.target.value)}>
          <option value="">All roles</option>
          {filterRoles.map((item) => (
            <option key={item} value={item}>
              {roleLabel(item)}
            </option>
          ))}
        </select>
        <select
          className={fieldClass}
          aria-label="Status"
          value={status}
          onChange={(event) => setStatus(event.target.value)}
        >
          <option value="">All statuses</option>
          <option value="active">Active</option>
          <option value="inactive">Inactive</option>
          <option value="invited">Invited</option>
        </select>
        {session.navRole === "super_admin" ? (
          <select
            className={fieldClass}
            aria-label="Directory"
            value={scope}
            onChange={(event) => setScope(event.target.value === "all" ? "all" : "company")}
          >
            <option value="company">This company</option>
            <option value="all">All companies</option>
          </select>
        ) : null}
      </div>
      {!allCompanies && !companyId ? (
        <div className="mt-6">
          <EmptyState
            title="No company selected"
            message="Choose a company in the header to manage its people."
          />
        </div>
      ) : (
        <UserResults
          isPending={activeQuery.isPending}
          isError={activeQuery.isError}
          error={activeQuery.error}
          items={activeQuery.data?.items}
          total={activeQuery.data?.total ?? 0}
          page={activeQuery.data?.page ?? filters.page}
          totalPages={activeQuery.data?.total_pages ?? 0}
          filtered={Boolean(search || role || status)}
          showCompany={allCompanies}
          currentUserId={session.currentUser?.id ?? null}
          assignable={roles}
          onPage={filters.setPage}
          onView={(member) => open("view", member)}
          onEdit={(member) => open("edit", member)}
          statusPending={updateUser.isPending}
          onStatus={(member, membershipStatus) => {
            const targetCompany = "company_id" in member ? member.company_id : companyId
            if (!targetCompany) {
              return
            }
            updateUser.mutate({
              companyId: targetCompany,
              userId: member.id,
              body: { membership_status: membershipStatus },
            })
          }}
        />
      )}
      <Dialog
        open={dialog === "add"}
        title="Add employee"
        onClose={() => setDialog(null)}
      >
        {dialog === "add" && companyId ? (
          <MemberForm
            roles={roles}
            pending={createUser.isPending}
            error={createUser.error}
            onSubmit={async (values) => {
              if (!isUserRole(values.role)) {
                return
              }
              await createUser.mutateAsync({
                first_name: values.first_name.trim(),
                last_name: values.last_name.trim(),
                email: values.email.trim(),
                phone: blankToNull(values.phone),
                role: values.role,
                membership_status: values.membership_status,
              })
              setDialog(null)
            }}
          />
        ) : null}
      </Dialog>
      {dialog !== "edit" && updateUser.isError ? (
        <p className="mt-4 text-sm text-danger" role="alert">
          {updateUser.error instanceof ApiError
            ? updateUser.error.message
            : "The user could not be updated."}
        </p>
      ) : null}
      <Dialog open={dialog === "edit"} title="Edit employee" onClose={() => setDialog(null)}>
        {dialog === "edit" && selected ? (
          <MemberForm
            member={selected}
            roles={roles}
            lockAccess={selected.id === session.currentUser?.id}
            pending={updateUser.isPending}
            error={updateUser.error}
            onSubmit={async (values) => {
              const body: MemberUpdate = {
                first_name: values.first_name.trim(),
                last_name: values.last_name.trim(),
                phone: blankToNull(values.phone),
              }
              if (selected.id !== session.currentUser?.id) {
                if (!isUserRole(values.role)) {
                  return
                }
                body.role = values.role
                body.membership_status = values.membership_status
              }
              const targetCompany = "company_id" in selected ? selected.company_id : companyId
              if (!targetCompany) {
                return
              }
              await updateUser.mutateAsync({ companyId: targetCompany, userId: selected.id, body })
              setDialog(null)
            }}
          />
        ) : null}
      </Dialog>
      <Dialog open={dialog === "view"} title="Employee" onClose={() => setDialog(null)}>
        {selected ? <MemberDetails member={selected} /> : null}
      </Dialog>
    </section>
  )
}

function UserResults({
  isPending,
  isError,
  error,
  items,
  total,
  page,
  totalPages,
  filtered,
  showCompany,
  currentUserId,
  assignable,
  statusPending,
  onPage,
  onView,
  onEdit,
  onStatus,
}: {
  isPending: boolean
  isError: boolean
  error: unknown
  items: Array<CompanyMember | AdminUserRow> | undefined
  total: number
  page: number
  totalPages: number
  filtered: boolean
  showCompany: boolean
  currentUserId: string | null
  assignable: UserRole[]
  statusPending: boolean
  onPage: (page: number) => void
  onView: (member: CompanyMember | AdminUserRow) => void
  onEdit: (member: CompanyMember | AdminUserRow) => void
  onStatus: (member: CompanyMember | AdminUserRow, status: MembershipStatus) => void
}) {
  if (isPending) {
    return <LoadingState label="Loading users" />
  }
  if (isError) {
    return (
      <div className="mt-6">
        <ErrorState message={error instanceof ApiError ? error.message : "Users could not be loaded."} />
      </div>
    )
  }
  if (!items || items.length === 0) {
    return (
      <div className="mt-6">
        <EmptyState
          title={filtered ? "No users match your search." : "No users found."}
          message={filtered ? "Try a different name, email, role, or status." : "Add an employee to this company."}
        />
      </div>
    )
  }

  return (
    <div className="mt-6">
      <p className="text-sm text-pine">{total} users</p>
      <div className="mt-3 hidden overflow-x-auto rounded-lg border border-line bg-paper md:block">
        <table className="w-full text-left text-sm">
          <caption className="sr-only">Employees</caption>
          <thead className="border-b border-line text-moss">
            <tr>
              <th scope="col" className="px-4 py-3 font-semibold">Name</th>
              <th scope="col" className="px-4 py-3 font-semibold">Email</th>
              {showCompany ? <th scope="col" className="px-4 py-3 font-semibold">Company</th> : null}
              <th scope="col" className="px-4 py-3 font-semibold">Role</th>
              <th scope="col" className="px-4 py-3 font-semibold">Status</th>
              <th scope="col" className="px-4 py-3 font-semibold">Created</th>
              <th scope="col" className="px-4 py-3 font-semibold">Actions</th>
            </tr>
          </thead>
          <tbody>
            {items.map((member) => (
              <tr key={rowKey(member)} className="border-t border-line">
                <td className="px-4 py-3 font-semibold">{member.first_name} {member.last_name}</td>
                <td className="px-4 py-3">{member.email}</td>
                {showCompany ? <td className="px-4 py-3">{"company_name" in member ? member.company_name : "—"}</td> : null}
                <td className="px-4 py-3">{roleLabel(member.role)}</td>
                <td className="px-4 py-3">{memberStatus(member)}</td>
                <td className="px-4 py-3">{formatDate(member.created_at)}</td>
                <td className="px-4 py-3">
                  <MemberActions
                    member={member}
                    currentUserId={currentUserId}
                    assignable={assignable}
                    pending={statusPending}
                    onView={onView}
                    onEdit={onEdit}
                    onStatus={onStatus}
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <ul className="mt-3 space-y-3 md:hidden">
        {items.map((member) => (
          <li key={rowKey(member)} className="rounded-lg border border-line bg-paper p-4">
            <p className="font-semibold">{member.first_name} {member.last_name}</p>
            <p className="mt-1 text-sm">{member.email}</p>
            {"company_name" in member && showCompany ? <p className="mt-1 text-sm">{member.company_name}</p> : null}
            <p className="mt-1 text-sm">{roleLabel(member.role)} · {memberStatus(member)}</p>
            <p className="mt-1 text-sm">Created {formatDate(member.created_at)}</p>
            <div className="mt-3">
              <MemberActions
                member={member}
                currentUserId={currentUserId}
                assignable={assignable}
                pending={statusPending}
                onView={onView}
                onEdit={onEdit}
                onStatus={onStatus}
              />
            </div>
          </li>
        ))}
      </ul>
      <Pagination page={page} totalPages={totalPages} onPage={onPage} />
    </div>
  )
}

function MemberActions({
  member,
  currentUserId,
  assignable,
  pending,
  onView,
  onEdit,
  onStatus,
}: {
  member: CompanyMember | AdminUserRow
  currentUserId: string | null
  assignable: UserRole[]
  pending: boolean
  onView: (member: CompanyMember | AdminUserRow) => void
  onEdit: (member: CompanyMember | AdminUserRow) => void
  onStatus: (member: CompanyMember | AdminUserRow, status: MembershipStatus) => void
}) {
  const canChangeAccess = member.id !== currentUserId && assignable.includes(member.role)
  const canEdit = canChangeAccess || member.id === currentUserId
  return (
    <div className="flex flex-wrap gap-3">
      <button type="button" className="font-semibold text-pine underline" onClick={() => onView(member)}>
        View
      </button>
      {canEdit ? (
        <button type="button" className="font-semibold text-pine underline" disabled={pending} onClick={() => onEdit(member)}>
          Edit
        </button>
      ) : null}
      {canChangeAccess && member.membership_status === "inactive" ? (
        <button type="button" className="font-semibold text-pine underline disabled:opacity-50" disabled={pending} onClick={() => onStatus(member, "active")}>
          {pending ? "Saving" : "Activate"}
        </button>
      ) : null}
      {canChangeAccess && member.membership_status === "active" ? (
        <button type="button" className="font-semibold text-pine underline disabled:opacity-50" disabled={pending} onClick={() => onStatus(member, "inactive")}>
          {pending ? "Saving" : "Deactivate"}
        </button>
      ) : null}
    </div>
  )
}

function MemberForm({
  member,
  roles,
  lockAccess = false,
  pending,
  error,
  onSubmit,
}: {
  member?: CompanyMember
  roles: UserRole[]
  lockAccess?: boolean
  pending: boolean
  error: unknown
  onSubmit: (values: MemberFormValues) => Promise<void>
}) {
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<MemberFormValues>({
    resolver: zodResolver(memberSchema),
    defaultValues: {
      first_name: member?.first_name ?? "",
      last_name: member?.last_name ?? "",
      email: member?.email ?? "",
      phone: formatUsPhone(member?.phone ?? ""),
      role: member?.role ?? (roles.includes(UserRole.EMPLOYEE) ? UserRole.EMPLOYEE : (roles[0] ?? UserRole.EMPLOYEE)),
      membership_status: member?.membership_status ?? "active",
    },
  })
  const busy = pending || isSubmitting
  const formError = error instanceof ApiError ? error.message : error ? "The user could not be saved." : null
  const roleChoices = member && !roles.includes(member.role) ? [member.role, ...roles] : roles

  return (
    <form className="grid gap-4" noValidate onSubmit={handleSubmit(onSubmit)}>
      <Field id="member-first" label="First name" error={errors.first_name?.message}>
        <input id="member-first" className={fieldClass} {...register("first_name")} />
      </Field>
      <Field id="member-last" label="Last name" error={errors.last_name?.message}>
        <input id="member-last" className={fieldClass} {...register("last_name")} />
      </Field>
      <Field id="member-email" label="Email" error={errors.email?.message}>
        <input
          id="member-email"
          type="email"
          readOnly={Boolean(member)}
          className={fieldClass}
          {...register("email")}
        />
      </Field>
      {member ? <p className="text-sm text-pine">Email is the sign-in identifier and cannot be changed here.</p> : null}
      <Field id="member-phone" label="Phone" error={errors.phone?.message}>
        <UsPhoneInput id="member-phone" registration={register("phone")} />
      </Field>
      <Field id="member-role" label="Role" error={errors.role?.message}>
        {lockAccess ? (
          <p id="member-role" className="mt-1">{member ? roleLabel(member.role) : ""}</p>
        ) : (
          <select id="member-role" className={fieldClass} {...register("role")}>
            {roleChoices.map((item) => (
              <option key={item} value={item}>
                {roleLabel(item)}
              </option>
            ))}
          </select>
        )}
      </Field>
      {lockAccess ? <input type="hidden" {...register("role")} /> : null}
      <Field id="member-status" label="Status" error={errors.membership_status?.message}>
        {lockAccess ? (
          <p id="member-status" className="mt-1">
            {member?.membership_status === "inactive" ? "Inactive" : "Active"}
          </p>
        ) : (
          <select id="member-status" className={fieldClass} {...register("membership_status")}>
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
          </select>
        )}
      </Field>
      {lockAccess ? <input type="hidden" {...register("membership_status")} /> : null}
      {!member ? (
        <p className="text-sm text-pine">
          A new person is invited and cannot sign in until an invitation is completed.
        </p>
      ) : null}
      {formError ? <p className="text-sm text-danger" role="alert">{formError}</p> : null}
      <button
        type="submit"
        disabled={busy}
        className="rounded-md bg-copper px-4 py-2 font-semibold text-paper disabled:opacity-60"
      >
        {busy ? "Saving" : member ? "Save changes" : "Add employee"}
      </button>
    </form>
  )
}

function MemberDetails({ member }: { member: CompanyMember | AdminUserRow }) {
  return (
    <dl className="grid gap-3 text-sm">
      <div>
        <dt className="font-semibold text-moss">Name</dt>
        <dd>{member.first_name} {member.last_name}</dd>
      </div>
      <div>
        <dt className="font-semibold text-moss">Email</dt>
        <dd>{member.email}</dd>
      </div>
      <div>
        <dt className="font-semibold text-moss">Phone</dt>
        <dd>{displayUsPhone(member.phone) || "—"}</dd>
      </div>
      <div>
        <dt className="font-semibold text-moss">Role</dt>
        <dd>{roleLabel(member.role)}</dd>
      </div>
      <div>
        <dt className="font-semibold text-moss">Membership</dt>
        <dd>{member.membership_status === "active" ? "Active" : "Inactive"}</dd>
      </div>
      <div>
        <dt className="font-semibold text-moss">Account</dt>
        <dd>{memberStatus(member)}</dd>
      </div>
      {"company_name" in member ? (
        <div>
          <dt className="font-semibold text-moss">Company</dt>
          <dd>{member.company_name}</dd>
        </div>
      ) : null}
    </dl>
  )
}

function memberStatus(member: CompanyMember): string {
  if (member.membership_status === "inactive") {
    return "Inactive"
  }
  if (member.user_status === "invited") {
    return "Invited"
  }
  if (member.user_status === "inactive") {
    return "Inactive"
  }
  return "Active"
}

function rowKey(member: CompanyMember | AdminUserRow): string {
  return "company_id" in member ? `${member.company_id}:${member.id}` : member.id
}
