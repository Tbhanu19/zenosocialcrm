import { createContext } from "react"
import { setAccessTokenGetter } from "../api/client.ts"

const TOKEN_KEY = "zeno.access_token"

export type AuthContextValue = {
  token: string | null
  isAuthenticated: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => void
}

export const AuthContext = createContext<AuthContextValue | null>(null)

let sessionToken: string | null = sessionStorage.getItem(TOKEN_KEY)
setAccessTokenGetter(() => sessionToken)

export function readSessionToken(): string | null {
  return sessionToken
}

export function writeSessionToken(token: string | null): void {
  sessionToken = token
  if (token) {
    sessionStorage.setItem(TOKEN_KEY, token)
  } else {
    sessionStorage.removeItem(TOKEN_KEY)
  }
}
