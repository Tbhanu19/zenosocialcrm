import { useState, type ReactNode } from "react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { ApiError } from "../api/client.ts"
import { AuthProvider } from "../auth/auth-context.tsx"

export function AppProviders({ children }: { children: ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 60_000,
            refetchOnWindowFocus: false,
            retry: (failureCount, error) => {
              if (
                error instanceof ApiError &&
                (error.status === 400 ||
                  error.status === 401 ||
                  error.status === 403 ||
                  error.status === 404 ||
                  error.status === 409 ||
                  error.status === 422 ||
                  error.status === 429)
              ) {
                return false
              }
              return failureCount < 1
            },
          },
          mutations: {
            retry: false,
          },
        },
      }),
  )

  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>{children}</AuthProvider>
    </QueryClientProvider>
  )
}
