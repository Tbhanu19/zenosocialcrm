"""Outbound delivery boundary.

Routes and message records must not call an email or SMS vendor directly.
No vendor is configured, so delivery reports that it is unavailable instead of
inventing a sent or delivered state.
"""


class ProviderUnavailable(Exception):
    """Raised when no email or SMS provider is configured."""


class DeliveryGateway:
    """Future email and SMS providers plug in here."""

    def send_email(self, *, to_address: str, subject: str, body: str) -> str:
        raise ProviderUnavailable

    def send_sms(self, *, to_number: str, body: str) -> str:
        raise ProviderUnavailable


def get_delivery_gateway() -> DeliveryGateway:
    return DeliveryGateway()
