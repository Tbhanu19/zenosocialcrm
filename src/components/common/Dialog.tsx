import { useEffect, useId, useRef, type ReactNode } from "react"

export function Dialog({
  open,
  title,
  onClose,
  children,
}: {
  open: boolean
  title: string
  onClose: () => void
  children: ReactNode
}) {
  const ref = useRef<HTMLDialogElement>(null)
  const titleId = useId()

  useEffect(() => {
    const dialog = ref.current
    if (!dialog) {
      return
    }
    if (open && !dialog.open) {
      dialog.showModal()
    } else if (!open && dialog.open) {
      dialog.close()
    }
  }, [open])

  return (
    <dialog
      ref={ref}
      aria-labelledby={titleId}
      className="w-[calc(100%-2rem)] max-w-lg rounded-lg border border-line bg-paper p-0 text-ink"
      onClose={onClose}
    >
      <div className="flex items-start justify-between gap-4 border-b border-line px-5 py-4">
        <h2 id={titleId} className="font-display text-2xl">
          {title}
        </h2>
        <button type="button" className="rounded-md px-2 py-1 text-sm" onClick={onClose}>
          Close
        </button>
      </div>
      <div className="px-5 py-4">{children}</div>
    </dialog>
  )
}
