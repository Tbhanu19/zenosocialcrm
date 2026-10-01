import { createBrowserRouter, Navigate, Outlet } from "react-router-dom"
import { RequireAuth } from "./RequireAuth.tsx"
import { RoleGate } from "../components/navigation/RoleGate.tsx"
import { CompaniesPage } from "../pages/Companies/CompaniesPage.tsx"
import { CompanyDetailPage } from "../pages/Companies/CompanyDetailPage.tsx"
import { CompanyEditPage } from "../pages/Companies/CompanyEditPage.tsx"
import { CreateCompanyPage } from "../pages/Companies/CreateCompanyPage.tsx"
import { ContactDetailPage } from "../pages/Contacts/ContactDetailPage.tsx"
import { ContactFormPage } from "../pages/Contacts/ContactFormPage.tsx"
import { ContactsPage } from "../pages/Contacts/ContactsPage.tsx"
import { AccountPage } from "../pages/Account/AccountPage.tsx"
import { LeadMetricsPage } from "../pages/LeadMetrics/LeadMetricsPage.tsx"
import { LeadMetricsTypesPage } from "../pages/LeadMetricsTypes/LeadMetricsTypesPage.tsx"
import { LeadDetailPage } from "../pages/Leads/LeadDetailPage.tsx"
import { LeadFormPage } from "../pages/Leads/LeadFormPage.tsx"
import { LeadsPage } from "../pages/Leads/LeadsPage.tsx"
import { LoginPage } from "../pages/Login/LoginPage.tsx"
import { MessageComposerPage } from "../pages/Messages/MessageComposerPage.tsx"
import { MessageDetailPage } from "../pages/Messages/MessageDetailPage.tsx"
import { MessagesPage } from "../pages/Messages/MessagesPage.tsx"
import { PipelinePage } from "../pages/Pipeline/PipelinePage.tsx"
import { SalesMetricsPage } from "../pages/SalesMetrics/SalesMetricsPage.tsx"
import { PlaceholderPage } from "../pages/Placeholder/PlaceholderPage.tsx"
import { UsersPage } from "../pages/Users/UsersPage.tsx"

export const router = createBrowserRouter([
  { path: "/login", element: <LoginPage /> },
  {
    path: "/",
    element: <RequireAuth />,
    children: [
      { index: true, element: <Navigate to="/contacts" replace /> },
      {
        path: "organisations",
        element: (
          <RoleGate itemId="companies">
            <Outlet />
          </RoleGate>
        ),
        children: [
          { index: true, element: <CompaniesPage /> },
          { path: "new", element: <CreateCompanyPage /> },
          { path: ":companyId", element: <CompanyDetailPage /> },
          { path: ":companyId/edit", element: <CompanyEditPage /> },
        ],
      },
      { path: "companies", element: <Navigate to="/organisations" replace /> },
      { path: "companies/*", element: <Navigate to="/organisations" replace /> },
      {
        path: "contacts",
        element: (
          <RoleGate itemId="contacts">
            <Outlet />
          </RoleGate>
        ),
        children: [
          { index: true, element: <ContactsPage /> },
          { path: "new", element: <ContactFormPage /> },
          { path: ":contactId", element: <ContactDetailPage /> },
          { path: ":contactId/edit", element: <ContactFormPage /> },
        ],
      },
      {
        path: "messages",
        element: (
          <RoleGate itemId="messages">
            <Outlet />
          </RoleGate>
        ),
        children: [
          { index: true, element: <MessagesPage /> },
          { path: "new", element: <MessageComposerPage /> },
          { path: ":messageId", element: <MessageDetailPage /> },
        ],
      },
      {
        path: "leads",
        element: (
          <RoleGate itemId="leads">
            <Outlet />
          </RoleGate>
        ),
        children: [
          { index: true, element: <LeadsPage /> },
          { path: "new", element: <LeadFormPage /> },
          { path: ":leadId", element: <LeadDetailPage /> },
          { path: ":leadId/edit", element: <LeadFormPage /> },
        ],
      },
      {
        path: "lead-metrics",
        element: (
          <RoleGate itemId="lead-metrics">
            <LeadMetricsPage />
          </RoleGate>
        ),
      },
      {
        path: "lead-metrics-types",
        element: (
          <RoleGate itemId="lead-metrics-types">
            <LeadMetricsTypesPage />
          </RoleGate>
        ),
      },
      {
        path: "pipeline",
        element: (
          <RoleGate itemId="pipeline">
            <Outlet />
          </RoleGate>
        ),
        children: [
          { index: true, element: <PipelinePage /> },
          { path: "settings", element: <Navigate to="/pipeline" replace /> },
        ],
      },
      {
        path: "sales-metrics",
        element: (
          <RoleGate itemId="sales-metrics">
            <SalesMetricsPage />
          </RoleGate>
        ),
      },
      {
        path: "users",
        element: (
          <RoleGate itemId="users">
            <UsersPage />
          </RoleGate>
        ),
      },
      {
        path: "account",
        element: (
          <RoleGate itemId="account">
            <AccountPage />
          </RoleGate>
        ),
      },
      { path: "settings", element: <Navigate to="/account" replace /> },
    ],
  },
  {
    path: "*",
    element: <PlaceholderPage title="Page not found" />,
  },
])

