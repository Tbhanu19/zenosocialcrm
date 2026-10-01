import { useSession } from "../../hooks/useSession.ts"

export function Header({ onOpenSidebar }: { onOpenSidebar: () => void }) {
  const {
    logout,
    currentUser: user,
    availableCompanies: companies,
    activeCompany: currentCompany,
    setActiveCompany,
    isLoading,
  } = useSession()
  const displayName = user ? `${user.first_name} ${user.last_name}` : "Account"

  return (
    <header className="flex h-16 items-center justify-between gap-4 border-b border-line bg-paper px-4 md:px-6">
      <button
        type="button"
        className="rounded-md border border-line px-3 py-1.5 text-sm md:hidden"
        onClick={onOpenSidebar}
      >
        Menu
      </button>
      <div className="flex min-w-0 flex-1 justify-end">
        {isLoading && companies.length === 0 ? (
          <p className="truncate text-sm text-pine">Loading organisations</p>
        ) : (
          <label className="block w-full max-w-xs text-sm">
            <span className="sr-only">Select organisation</span>
            <select
              className="w-full rounded-md border border-line bg-paper px-3 py-2"
              value={currentCompany?.id ?? ""}
              aria-label="Select organisation"
              onChange={(event) => {
                const companyId = event.target.value
                if (companyId) {
                  setActiveCompany(companyId)
                }
              }}
            >
              {currentCompany ? null : <option value="">Select organisation</option>}
              {companies.map((company) => (
                <option key={company.id} value={company.id}>
                  {company.name}
                </option>
              ))}
            </select>
          </label>
        )}
      </div>
      <details className="relative">
        <summary className="cursor-pointer list-none rounded-md border border-line px-3 py-1.5 text-sm">
          <span className="font-semibold">{displayName}</span>
        </summary>
        <div className="absolute right-0 z-20 mt-2 w-56 rounded-md border border-line bg-paper p-3 shadow-sm">
          <p className="text-sm text-pine">{user?.email}</p>
          <button
            type="button"
            className="mt-3 w-full rounded-md bg-ink px-3 py-2 text-sm text-paper"
            onClick={logout}
          >
            Log out
          </button>
        </div>
      </details>
    </header>
  )
}
