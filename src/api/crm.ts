import { apiFetch } from "./client.ts"
import type { ContactFilters, MessageFilters } from "./query-keys.ts"
import type {
  AssigneeOption,
  ContactRecord,
  ContactListItem,
  ContactWrite,
  MessageCreated,
  MessageDraftUpdate,
  MessageListItem,
  MessageRecord,
  MessageWrite,
  Page,
} from "../types/crm.ts"

function queryString(entries: Record<string, string | number>): string {
  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(entries)) {
    if (value !== "") {
      params.set(key, String(value))
    }
  }
  const text = params.toString()
  return text ? `?${text}` : ""
}

export function fetchContacts(
  companyId: string,
  filters: ContactFilters,
): Promise<Page<ContactListItem>> {
  return apiFetch(
    `/api/companies/${companyId}/contacts${queryString({
      page: filters.page,
      page_size: filters.pageSize,
      search: filters.search,
      status: filters.status,
      source: filters.source,
      assigned_to: filters.assignedTo,
    })}`,
  )
}

export function fetchContact(companyId: string, contactId: string): Promise<ContactRecord> {
  return apiFetch(`/api/companies/${companyId}/contacts/${contactId}`)
}

export function fetchAssignees(companyId: string): Promise<Page<AssigneeOption>> {
  return apiFetch(`/api/companies/${companyId}/contacts/assignees?page=1&page_size=100`)
}

export function createContact(companyId: string, body: ContactWrite): Promise<ContactRecord> {
  return apiFetch(`/api/companies/${companyId}/contacts`, {
    method: "POST",
    body: JSON.stringify(body),
  })
}

export function updateContact(
  companyId: string,
  contactId: string,
  body: Partial<ContactWrite>,
): Promise<ContactRecord> {
  return apiFetch(`/api/companies/${companyId}/contacts/${contactId}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  })
}

export function deleteContact(companyId: string, contactId: string): Promise<void> {
  return apiFetch(`/api/companies/${companyId}/contacts/${contactId}`, {
    method: "DELETE",
  })
}

export function fetchMessages(
  companyId: string,
  filters: MessageFilters,
): Promise<Page<MessageListItem>> {
  return apiFetch(
    `/api/companies/${companyId}/messages${queryString({
      page: filters.page,
      page_size: filters.pageSize,
      search: filters.search,
      message_type: filters.messageType,
      status: filters.status,
      contact_id: filters.contactId,
    })}`,
  )
}

export function fetchMessage(companyId: string, messageId: string): Promise<MessageRecord> {
  return apiFetch(`/api/companies/${companyId}/messages/${messageId}`)
}

export function createMessage(companyId: string, body: MessageWrite): Promise<MessageCreated> {
  return apiFetch(`/api/companies/${companyId}/messages`, {
    method: "POST",
    body: JSON.stringify(body),
  })
}

export function updateMessage(
  companyId: string,
  messageId: string,
  body: MessageDraftUpdate,
): Promise<MessageRecord> {
  return apiFetch(`/api/companies/${companyId}/messages/${messageId}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  })
}
