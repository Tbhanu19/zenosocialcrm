"""US phone numbers are stored as (214) 555-0100."""

from typing import Annotated

from pydantic import BeforeValidator

_PHONE_ERROR = "Enter a US phone number, such as (214) 555-0100."


def normalize_us_phone(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(_PHONE_ERROR)
    if not value.strip():
        return None
    digits = "".join(character for character in value if character.isdigit())
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    if len(digits) != 10:
        raise ValueError(_PHONE_ERROR)
    return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"


UsPhone = Annotated[str | None, BeforeValidator(normalize_us_phone)]
