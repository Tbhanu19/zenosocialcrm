import { useQuery } from "@tanstack/react-query"
import { fetchCurrentUser } from "../api/auth.ts"
import { queryKeys } from "../api/query-keys.ts"
import { useAuth } from "./useAuth.ts"

export function useCurrentUser() {
  const { token } = useAuth()
  return useQuery({
    queryKey: queryKeys.currentUser,
    queryFn: fetchCurrentUser,
    enabled: Boolean(token),
    staleTime: 5 * 60 * 1000,
  })
}
