export type UserStatus = "active" | "inactive" | "invited"

export type CurrentUser = {
  id: string
  email: string
  first_name: string
  last_name: string
  phone: string | null
  status: UserStatus
  is_super_admin: boolean
  created_at: string
  updated_at: string
}
