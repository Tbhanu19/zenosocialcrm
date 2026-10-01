import { Link, useNavigate, useParams } from "react-router-dom"
import { CompanyForm } from "./CompanyForm.tsx"
import { ApiError } from "../../api/client.ts"
import { ErrorState } from "../../components/common/ErrorState.tsx"
import { LoadingState } from "../../components/common/LoadingState.tsx"
import { useAdminCompany, useUpdateCompany } from "../../hooks/useManagement.ts"
import type { CompanyWrite } from "../../types/management.ts"

export function CompanyEditPage() {
  const { companyId = "" } = useParams()
  const navigate = useNavigate()
  const companyQuery = useAdminCompany(companyId)
  const updateCompany = useUpdateCompany(companyId)

  if (companyQuery.isPending) {
    return <LoadingState label="Loading organisation" />
  }
  if (companyQuery.isError || !companyQuery.data) {
    return (
      <ErrorState
        message={
          companyQuery.error instanceof ApiError
            ? companyQuery.error.message
            : "Organisation could not be loaded."
        }
      />
    )
  }

  async function onUpdate(body: CompanyWrite) {
    await updateCompany.mutateAsync(body)
    void navigate(`/organisations/${companyId}`)
  }

  return (
    <section className="mx-auto max-w-3xl">
      <Link to={`/organisations/${companyId}`} className="text-sm font-semibold text-pine underline">
        Back to organisation
      </Link>
      <h1 className="mt-3 font-display text-4xl">Edit {companyQuery.data.name}</h1>
      <CompanyForm
        mode="edit"
        company={companyQuery.data}
        pending={updateCompany.isPending}
        error={updateCompany.error}
        onUpdate={onUpdate}
      />
    </section>
  )
}
