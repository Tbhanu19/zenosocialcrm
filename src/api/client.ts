const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000"

let accessTokenGetter: () => string | null = () => null
let companyIdGetter: () => string | null = () => null
let unauthorizedHandler: () => void = () => undefined

export function setAccessTokenGetter(getter: () => string | null): void {
  accessTokenGetter = getter
}

export function setCompanyIdGetter(getter: () => string | null): void {
  companyIdGetter = getter
}

export function setUnauthorizedHandler(handler: () => void): void {
  unauthorizedHandler = handler
}

export class ApiError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = "ApiError"
    this.status = status
  }
}

type ApiRequest = RequestInit & {
  skipAuthRecovery?: boolean
}

export async function apiFetch<T>(path: string, init?: ApiRequest): Promise<T> {
  const headers = new Headers(init?.headers)
  if (init?.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json")
  }
  const token = accessTokenGetter()
  if (token && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${token}`)
  }
  const companyId = companyIdGetter()
  if (companyId && !headers.has("X-Company-Id")) {
    headers.set("X-Company-Id", companyId)
  }

  const { skipAuthRecovery, ...request } = init ?? {}
  let response: Response
  try {
    response = await fetch(`${API_URL}${path}`, { ...request, headers })
  } catch {
    throw new ApiError(0, "Network error. Check your connection and try again.")
  }
  if (!response.ok) {
    if (response.status === 401 && !skipAuthRecovery && !path.endsWith("/auth/login")) {
      if (accessTokenGetter()) {
        unauthorizedHandler()
      }
    }
    throw new ApiError(response.status, await readErrorMessage(response))
  }
  if (response.status === 204) {
    return undefined as T
  }
  return (await response.json()) as T
}

async function readErrorMessage(response: Response): Promise<string> {
  const serverMessage = await readServerMessage(response)
  if (response.status === 401) {
    return serverMessage || "Authentication is required."
  }
  if (response.status === 403) {
    return "You do not have permission to perform this action."
  }
  if (response.status === 404) {
    return serverMessage || "The requested resource was not found."
  }
  if (response.status === 422) {
    return serverMessage || "Request validation failed."
  }
  if (response.status === 429) {
    return serverMessage || "Too many attempts. Try again later."
  }
  if (response.status >= 500) {
    return "Something went wrong. Try again."
  }
  return serverMessage || "Request failed."
}

async function readServerMessage(response: Response): Promise<string | null> {
  try {
    const payload: unknown = await response.json()
    if (
      typeof payload === "object" &&
      payload !== null &&
      "error" in payload &&
      typeof payload.error === "object" &&
      payload.error !== null &&
      "message" in payload.error &&
      typeof payload.error.message === "string"
    ) {
      return payload.error.message
    }
  } catch {
    return null
  }
  return null
}
