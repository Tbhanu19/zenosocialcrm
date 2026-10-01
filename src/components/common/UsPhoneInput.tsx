import type { UseFormRegisterReturn } from "react-hook-form"
import { formatUsPhone } from "../../lib/utils.ts"
import { fieldClass } from "./Field.tsx"

export function UsPhoneInput({
  id,
  registration,
}: {
  id: string
  registration: UseFormRegisterReturn
}) {
  return (
    <input
      id={id}
      className={fieldClass}
      inputMode="tel"
      autoComplete="tel"
      placeholder="(214) 555-0100"
      {...registration}
      onChange={(event) => {
        event.target.value = formatUsPhone(event.target.value)
        void registration.onChange(event)
      }}
    />
  )
}
