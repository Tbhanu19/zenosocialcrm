import { useQuery } from "@tanstack/react-query"
import { fetchAvailableCompanies } from "../api/companies.ts"
import { queryKeys } from "../api/query-keys.ts"
import { useAuth } from "./useAuth.ts"

export function useAvailableCompanies() {
  const { token } = useAuth()
  return useQuery({
    queryKey: queryKeys.availableCompanies,
    queryFn: fetchAvailableCompanies,
    enabled: Boolean(token),
    staleTime: 60 * 1000,
  })
}
