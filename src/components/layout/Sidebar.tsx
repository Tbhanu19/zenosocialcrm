import { NavLink } from "react-router-dom"
import { visibleNavItems, type NavItem } from "../../auth/permissions.ts"
import { useCompanyContext } from "../../hooks/useCompanyContext.ts"
import { cn } from "../../lib/utils.ts"

export function Sidebar({ open, onNavigate }: { open: boolean; onNavigate: () => void }) {
  const { navRole } = useCompanyContext()
  const items = visibleNavItems(navRole)
  const sections = groupBySection(items)

  return (
    <aside
      className={cn(
        "fixed inset-y-0 left-0 z-30 flex w-64 flex-col bg-ink text-cream transition-transform md:static md:translate-x-0",
        open ? "translate-x-0" : "-translate-x-full",
      )}
    >
      <div className="flex items-center gap-3 px-5 py-5">
        <span className="grid h-9 w-9 place-items-center rounded-md bg-copper font-display text-lg text-paper">
          Z
        </span>
        <div>
          <p className="font-display text-lg leading-none">Zeno</p>
          <p className="mt-1 text-xs tracking-wide text-cream/70">Social CRM</p>
        </div>
      </div>
      <nav className="flex-1 overflow-y-auto px-3 pb-6" aria-label="Primary">
        {sections.map(([section, sectionItems]) => (
          <div key={section} className="mt-4">
            <p className="px-3 text-[11px] font-semibold tracking-[0.14em] text-cream/50 uppercase">
              {section}
            </p>
            <ul className="mt-1 space-y-1">
              {sectionItems.map((item) => (
                <li key={item.id}>
                  <NavLink
                    to={item.path}
                    end={item.path === "/"}
                    onClick={onNavigate}
                    className={({ isActive }) =>
                      cn(
                        "block rounded-md px-3 py-2 text-sm text-cream/85 hover:bg-white/8",
                        isActive && "bg-white/10 font-semibold text-paper",
                      )
                    }
                  >
                    {item.label}
                  </NavLink>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </nav>
    </aside>
  )
}

function groupBySection(items: NavItem[]): Array<[string, NavItem[]]> {
  const groups = new Map<string, NavItem[]>()
  for (const item of items) {
    const current = groups.get(item.section) ?? []
    current.push(item)
    groups.set(item.section, current)
  }
  return [...groups.entries()]
}
