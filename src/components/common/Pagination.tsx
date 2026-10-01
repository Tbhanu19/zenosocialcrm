export function Pagination({
  page,
  totalPages,
  onPage,
}: {
  page: number
  totalPages: number
  onPage: (page: number) => void
}) {
  if (totalPages <= 1) {
    return null
  }

  return (
    <nav className="mt-4 flex items-center justify-between gap-3" aria-label="Pagination">
      <button
        type="button"
        className="rounded-md border border-line bg-paper px-3 py-2 text-sm disabled:opacity-50"
        disabled={page <= 1}
        onClick={() => onPage(page - 1)}
      >
        Previous
      </button>
      <p className="text-sm text-pine">
        Page {page} of {totalPages}
      </p>
      <button
        type="button"
        className="rounded-md border border-line bg-paper px-3 py-2 text-sm disabled:opacity-50"
        disabled={page >= totalPages}
        onClick={() => onPage(page + 1)}
      >
        Next
      </button>
    </nav>
  )
}
