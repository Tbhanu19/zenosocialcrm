import { useState } from "react"

export function usePagedFilters(filterKey: string) {
  const [page, setPage] = useState(1)
  const [syncedKey, setSyncedKey] = useState(filterKey)
  const currentPage = syncedKey === filterKey ? page : 1

  function setCurrentPage(next: number) {
    setSyncedKey(filterKey)
    setPage(next)
  }

  return { page: currentPage, setPage: setCurrentPage }
}
