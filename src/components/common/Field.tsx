import type { ReactNode } from "react"

export const fieldClass = "mt-1 w-full rounded-md border border-line bg-paper px-3 py-2"

export function Field({
  id,
  label,
  error,
  children,
}: {
  id: string
  label: string
  error?: string
  children: ReactNode
}) {
  return (
    <div>
      <label className="block text-sm font-semibold" htmlFor={id}>
        {label}
      </label>
      {children}
      {error ? <p className="mt-1 text-sm text-danger">{error}</p> : null}
    </div>
  )
}
