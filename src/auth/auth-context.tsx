import { useQueryClient } from "@tanstack/react-query"
import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react"
import { loginRequest, logoutRequest } from "../api/auth.ts"
import { setCompanyIdGetter, setUnauthorizedHandler } from "../api/client.ts"
import { queryKeys } from "../api/query-keys.ts"
import { AuthContext, readSessionToken, writeSessionToken } from "./auth-session.ts"
import { writeCompanyId } from "./company-session.ts"

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient()
  const [token, setToken] = useState<string | null>(() => readSessionToken())

  const clearLocalSession = useCallback(() => {
    writeSessionToken(null)
    writeCompanyId(null)
    setCompanyIdGetter(() => null)
    setToken(null)
    queryClient.removeQueries({ queryKey: queryKeys.currentUser })
    queryClient.removeQueries({ queryKey: queryKeys.availableCompanies })
  }, [queryClient])

  const logout = useCallback(() => {
    const currentToken = readSessionToken()
    clearLocalSession()
    if (!currentToken) {
      return
    }
    void logoutRequest(currentToken).catch(() => undefined)
  }, [clearLocalSession])

  const login = useCallback(async (email: string, password: string) => {
    const result = await loginRequest(email, password)
    writeCompanyId(null)
    writeSessionToken(result.access_token)
    setToken(result.access_token)
  }, [])

  useEffect(() => {
    setUnauthorizedHandler(clearLocalSession)
  }, [clearLocalSession])

  useEffect(() => {
    if (token) {
      return
    }
    queryClient.removeQueries({ queryKey: queryKeys.currentUser })
    queryClient.removeQueries({ queryKey: queryKeys.availableCompanies })
  }, [queryClient, token])

  const value = useMemo(
    () => ({ token, isAuthenticated: token !== null, login, logout }),
    [login, logout, token],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
