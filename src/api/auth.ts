import { apiFetch } from "./client.ts"
import type { CurrentUser } from "../types/user.ts"

export type LoginResult = {
  access_token: string
  token_type: string
}

export function loginRequest(email: string, password: string): Promise<LoginResult> {
  return apiFetch<LoginResult>("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  })
}

export function fetchCurrentUser(): Promise<CurrentUser> {
  return apiFetch<CurrentUser>("/api/auth/me")
}

export type ProfileUpdate = {
  first_name: string
  last_name: string
  email: string
  phone: string | null
}

export function updateCurrentUser(body: ProfileUpdate): Promise<CurrentUser> {
  return apiFetch<CurrentUser>("/api/auth/me", {
    method: "PATCH",
    body: JSON.stringify(body),
  })
}

export function logoutRequest(token: string): Promise<void> {
  return apiFetch<void>("/api/auth/logout", {
    method: "POST",
    skipAuthRecovery: true,
    headers: { Authorization: `Bearer ${token}` },
  })
}
