import { zodResolver } from "@hookform/resolvers/zod"
import { useState } from "react"
import { useForm } from "react-hook-form"
import { Navigate } from "react-router-dom"
import { z } from "zod"
import { ApiError } from "../../api/client.ts"
import { LoadingState } from "../../components/common/LoadingState.tsx"
import { useAuth } from "../../hooks/useAuth.ts"
import { useCurrentUser } from "../../hooks/useCurrentUser.ts"

const loginSchema = z.object({
  email: z.string().email("Enter a valid email."),
  password: z.string().min(1, "Password is required."),
})

type LoginValues = z.infer<typeof loginSchema>

function loginErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 0) {
      return "Network error. Check your connection and try again."
    }
    if (error.status === 401) {
      return "Invalid email or password."
    }
    return error.message
  }
  return "Sign-in failed."
}

export function LoginPage() {
  const { token, login } = useAuth()
  const userQuery = useCurrentUser()
  const [formError, setFormError] = useState<string | null>(null)
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: "", password: "" },
  })

  if (token && userQuery.isPending) {
    return (
      <main className="grid min-h-screen place-items-center">
        <LoadingState label="Checking your session" />
      </main>
    )
  }

  if (token && userQuery.data) {
    return <Navigate to="/contacts" replace />
  }

  return (
    <main className="grid min-h-screen md:grid-cols-2">
      <section className="hidden bg-ink px-10 py-12 text-cream md:flex md:flex-col md:justify-between">
        <div className="flex items-center gap-3">
          <span className="grid h-10 w-10 place-items-center rounded-md bg-copper font-display text-xl text-paper">
            Z
          </span>
          <p className="font-display text-2xl">Zeno</p>
        </div>
        <div>
          <h1 className="max-w-sm font-display text-5xl leading-tight">One workspace for every company you run.</h1>
          <p className="mt-4 max-w-sm text-cream/75">
            Access stays with the company that granted it. Switch companies from the header when you have more than one.
          </p>
        </div>
        <p className="text-sm text-cream/50">ZenoSocialCRM</p>
      </section>
      <section className="flex items-center justify-center px-6 py-12">
        <form
          className="w-full max-w-sm"
          onSubmit={handleSubmit(async (values) => {
            setFormError(null)
            try {
              await login(values.email, values.password)
            } catch (error) {
              setFormError(loginErrorMessage(error))
            }
          })}
          noValidate
        >
          <h2 className="font-display text-3xl">Sign in</h2>
          <p className="mt-2 text-pine">Use the account issued for your company.</p>
          <label className="mt-6 block text-sm font-semibold" htmlFor="email">
            Email
          </label>
          <input
            id="email"
            type="email"
            autoComplete="email"
            className="mt-1 w-full rounded-md border border-line bg-paper px-3 py-2"
            {...register("email")}
          />
          {errors.email ? <p className="mt-1 text-sm text-danger">{errors.email.message}</p> : null}
          <label className="mt-4 block text-sm font-semibold" htmlFor="password">
            Password
          </label>
          <input
            id="password"
            type="password"
            autoComplete="current-password"
            className="mt-1 w-full rounded-md border border-line bg-paper px-3 py-2"
            {...register("password")}
          />
          {errors.password ? (
            <p className="mt-1 text-sm text-danger">{errors.password.message}</p>
          ) : null}
          {formError ? (
            <p className="mt-4 text-sm text-danger" role="alert">
              {formError}
            </p>
          ) : null}
          <button
            type="submit"
            disabled={isSubmitting}
            className="mt-6 w-full rounded-md bg-copper px-3 py-2 font-semibold text-paper disabled:opacity-60"
          >
            {isSubmitting ? "Signing in" : "Sign in"}
          </button>
        </form>
      </section>
    </main>
  )
}
