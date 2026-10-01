import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import {
  createContact,
  createMessage,
  deleteContact,
  fetchAssignees,
  fetchContact,
  fetchContacts,
  fetchMessage,
  fetchMessages,
  updateContact,
  updateMessage,
} from "../api/crm.ts"
import {
  queryKeys,
  type ContactFilters,
  type MessageFilters,
} from "../api/query-keys.ts"
import type { ContactWrite, MessageDraftUpdate, MessageWrite } from "../types/crm.ts"

export function useContacts(
  companyId: string | null,
  filters: ContactFilters,
  enabled = true,
) {
  return useQuery({
    queryKey: queryKeys.contacts(companyId ?? "", filters),
    queryFn: () => fetchContacts(companyId ?? "", filters),
    enabled: enabled && Boolean(companyId),
  })
}

export function useContact(companyId: string | null, contactId: string) {
  return useQuery({
    queryKey: queryKeys.contact(companyId ?? "", contactId),
    queryFn: () => fetchContact(companyId ?? "", contactId),
    enabled: Boolean(companyId) && Boolean(contactId),
  })
}

export function useAssignees(companyId: string | null, enabled = true) {
  return useQuery({
    queryKey: queryKeys.contactAssignees(companyId ?? ""),
    queryFn: () => fetchAssignees(companyId ?? ""),
    enabled: enabled && Boolean(companyId),
  })
}

export function useCreateContact(companyId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: ContactWrite) => createContact(companyId, body),
    onSuccess: (contact) => {
      void queryClient.invalidateQueries({ queryKey: ["contacts", companyId] })
      void queryClient.invalidateQueries({ queryKey: ["contact", companyId, contact.id] })
    },
  })
}

export function useUpdateContact(companyId: string, contactId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: Partial<ContactWrite>) => updateContact(companyId, contactId, body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["contacts", companyId] })
      void queryClient.invalidateQueries({ queryKey: ["contact", companyId, contactId] })
    },
  })
}

export function useDeleteContact(companyId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (contactId: string) => deleteContact(companyId, contactId),
    onSuccess: (_result, contactId) => {
      void queryClient.invalidateQueries({ queryKey: ["contacts", companyId] })
      void queryClient.invalidateQueries({ queryKey: ["contact", companyId, contactId] })
    },
  })
}

export function useMessages(
  companyId: string | null,
  filters: MessageFilters,
  enabled = true,
) {
  return useQuery({
    queryKey: queryKeys.messages(companyId ?? "", filters),
    queryFn: () => fetchMessages(companyId ?? "", filters),
    enabled: enabled && Boolean(companyId),
  })
}

export function useContactMessages(
  companyId: string | null,
  contactId: string,
  filters: MessageFilters,
) {
  return useQuery({
    queryKey: queryKeys.contactMessages(companyId ?? "", contactId, filters),
    queryFn: () => fetchMessages(companyId ?? "", filters),
    enabled: Boolean(companyId) && Boolean(contactId),
  })
}

export function useMessage(companyId: string | null, messageId: string) {
  return useQuery({
    queryKey: queryKeys.message(companyId ?? "", messageId),
    queryFn: () => fetchMessage(companyId ?? "", messageId),
    enabled: Boolean(companyId) && Boolean(messageId),
  })
}

export function useCreateMessage(companyId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: MessageWrite) => createMessage(companyId, body),
    onSuccess: (result) => {
      void queryClient.invalidateQueries({ queryKey: ["messages", companyId] })
      void queryClient.invalidateQueries({
        queryKey: ["message", companyId, result.message.id],
      })
      if (result.message.contact_id) {
        void queryClient.invalidateQueries({
          queryKey: ["contact-messages", companyId, result.message.contact_id],
        })
      }
    },
  })
}

export function useUpdateMessage(companyId: string, messageId: string, contactId: string | null) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: MessageDraftUpdate) => updateMessage(companyId, messageId, body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["messages", companyId] })
      void queryClient.invalidateQueries({ queryKey: ["message", companyId, messageId] })
      if (contactId) {
        void queryClient.invalidateQueries({
          queryKey: ["contact-messages", companyId, contactId],
        })
      }
    },
  })
}
