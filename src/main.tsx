import { StrictMode } from "react"
import { createRoot } from "react-dom/client"
import { RouterProvider } from "react-router-dom"
import { AppProviders } from "./app/providers.tsx"
import { router } from "./app/router.tsx"
import { AppErrorBoundary } from "./components/common/AppErrorBoundary.tsx"
import "./index.css"

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <AppErrorBoundary>
      <AppProviders>
        <RouterProvider router={router} />
      </AppProviders>
    </AppErrorBoundary>
  </StrictMode>,
)
