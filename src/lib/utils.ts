export function cn(...parts: Array<string | false | null | undefined>): string {
  return parts.filter(Boolean).join(" ")
}

export function formatCalendarDate(value: string | null): string {
  if (!value) {
    return "—"
  }
  const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(value)
  if (!match) {
    return value
  }
  const date = new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3]))
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium" }).format(date)
}

export function formatDate(value: string): string {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return value
  }
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium" }).format(date)
}

/** Format up to 10 US digits as (214) 555-0100. A leading 1 is ignored. */
export function formatUsPhone(value: string): string {
  let digits = value.replace(/\D/g, "")
  if (digits.length === 11 && digits.startsWith("1")) {
    digits = digits.slice(1)
  }
  digits = digits.slice(0, 10)
  if (digits.length === 0) {
    return ""
  }
  if (digits.length < 4) {
    return `(${digits}`
  }
  if (digits.length < 7) {
    return `(${digits.slice(0, 3)}) ${digits.slice(3)}`
  }
  return `(${digits.slice(0, 3)}) ${digits.slice(3, 6)}-${digits.slice(6)}`
}

export function isUsPhone(value: string): boolean {
  const trimmed = value.trim()
  return trimmed === "" || (formatUsPhone(trimmed) === trimmed && trimmed.length === 14)
}

/** Show a stored number as (214) 555-0100 when it has 10 US digits. */
export function displayUsPhone(value: string | null | undefined): string {
  if (!value?.trim()) {
    return ""
  }
  const formatted = formatUsPhone(value)
  return formatted.length === 14 ? formatted : value
}

export function blankToNull(value: string): string | null {
  const trimmed = value.trim()
  return trimmed ? trimmed : null
}

export function roleLabel(role: string): string {
  return role
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ")
}
