import { Link, useNavigate } from "react-router-dom"
import { CompanyForm } from "./CompanyForm.tsx"
import { useCreateCompany } from "../../hooks/useManagement.ts"
import type { CreateCompanyBody } from "../../types/management.ts"

export function CreateCompanyPage() {
  const navigate = useNavigate()
  const createCompany = useCreateCompany()

  async function onCreate(body: CreateCompanyBody) {
    const result = await createCompany.mutateAsync(body)
    const notice = result.owner.linked_existing_user
      ? "Existing account linked as owner."
      : "Owner invited. They cannot sign in until an invitation is completed."
    void navigate(`/organisations/${result.company.id}`, { state: { notice } })
  }

  return (
    <section className="mx-auto max-w-3xl">
      <Link to="/organisations" className="text-sm font-semibold text-pine underline">
        Back to organisations
      </Link>
      <h1 className="mt-3 font-display text-4xl">Create organisation</h1>
      <p className="mt-2 text-pine">
        Organisation information and the initial owner are saved together. You can add companies
        inside the organisation next.
      </p>
      <CompanyForm
        mode="create"
        pending={createCompany.isPending}
        error={createCompany.error}
        onCreate={onCreate}
      />
    </section>
  )
}
