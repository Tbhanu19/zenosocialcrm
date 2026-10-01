import type { Page } from "./management.ts"

export type { Page }

export type ContactStatus = "active" | "inactive" | "archived"
export type ContactSource = "manual" | "website" | "import" | "campaign" | "referral" | "other"
export type MessageType = "email" | "sms"
export type MessageStatus = "draft" | "queued" | "sent" | "delivered" | "failed"

export type ContactListItem = {
  id: string
  first_name: string
  last_name: string
  email: string | null
  phone: string | null
  company_name: string | null
  status: ContactStatus
  source: ContactSource
  opted_in: boolean
  contact_date: string | null
  assigned_to_user_id: string | null
  assignee_name: string | null
  created_at: string
}

export type ContactRecord = ContactListItem & {
  address: string | null
  city: string | null
  state: string | null
  zip_code: string | null
  notes: string | null
  updated_at: string
}

export type ContactWrite = {
  first_name: string
  last_name: string
  email: string | null
  phone: string | null
  company_name: string | null
  address: string | null
  city: string | null
  state: string | null
  zip_code: string | null
  source: ContactSource
  status: ContactStatus
  opted_in: boolean
  contact_date: string | null
  notes: string | null
  assigned_to_user_id: string | null
}

export type AssigneeOption = {
  id: string
  first_name: string
  last_name: string
}

export type MessageListItem = {
  id: string
  contact_id: string | null
  contact_name: string | null
  message_type: MessageType
  direction: "outbound" | "inbound"
  subject: string | null
  body: string
  status: MessageStatus
  created_by_user_id: string | null
  creator_name: string | null
  created_at: string
}

export type MessageRecord = MessageListItem & {
  contact_email: string | null
  contact_phone: string | null
  provider: string | null
  provider_message_id: string | null
  error_message: string | null
  sent_at: string | null
  updated_at: string
}

export type MessageWrite = {
  contact_id: string
  message_type: MessageType
  subject: string | null
  body: string
  deliver: boolean
}

export type MessageCreated = {
  message: MessageRecord
  provider_status: string
}

export type MessageDraftUpdate = {
  subject?: string | null
  body?: string
}

export const CONTACT_SOURCES: readonly ContactSource[] = [
  "manual",
  "website",
  "import",
  "campaign",
  "referral",
  "other",
]

export const MESSAGE_STATUSES: readonly MessageStatus[] = [
  "draft",
  "queued",
  "sent",
  "delivered",
  "failed",
]
