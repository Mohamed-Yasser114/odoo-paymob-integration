from decimal import Decimal, ROUND_HALF_UP
from odoo import models, fields
import requests

from odoo.exceptions import ValidationError


class PaymentTransaction(models.Model):
    _inherit = "payment.transaction"
    paymob_order_id = fields.Char(
        readonly=True,
        copy=False,
    )
    def _get_specific_rendering_values(self, processing_values):
        res = super()._get_specific_rendering_values(processing_values)
        if self.provider_code != "paymob":
            return res
        headers = {
            "Authorization": f"Token {self.provider_id.paymob_secret_key}",
            "Content-Type": "application/json",
        }
        url = 'https://accept.paymob.com/v1/intention/'
        amount_cents = int(
            (Decimal(str(self.amount)) * 100).quantize(
                Decimal("1"), rounding=ROUND_HALF_UP
            )
        )
        currency = self.currency_id.name
        base_url = self.provider_id.get_base_url().rstrip("/")
        payload = {
            "amount": amount_cents,
            "currency": currency,
            "special_reference": self.reference,
            "payment_methods": [self.provider_id.paymob_integration_id],
            "notification_url": f"{base_url}payment/paymob/webhook",
            "redirection_url": f"{base_url}/shop",
            "billing_data": {
                "name": self.partner_id.name or "",
                "phone_number": self.partner_id.phone or self.partner_id.mobile or "",
                "email": self.partner_id.email or "",
                "street": self.partner_id.street or "",
                "city": self.partner_id.city or "",
                "country": self.partner_id.country_id.code or "",
                "state": self.partner_id.state_id.name or ""
            }
        }
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException as e:
            raise ValidationError(
                "Unable to communicate with Paymob. Please try again later."
            ) from e

        except ValueError as e:
            raise ValidationError(
                "Paymob returned an invalid response."
            ) from e
        if not isinstance(data, dict):
            raise ValidationError("Invalid response format from Paymob.")
        order_id = data.get("intention_order_id")
        client_secret = data.get("client_secret")

        if not order_id or not client_secret:
            raise ValidationError(
                "Invalid response from Paymob: missing payment information."
            )
        self.paymob_order_id = str(order_id)
        res.update({
            "public_key": self.provider_id.paymob_public_key,
            "client_secret": client_secret,
        })
        return res

    def _extract_amount_data(self, payment_data):
        if self.provider_code != "paymob":
            return super()._extract_amount_data(payment_data)

        obj = payment_data["obj"]

        return {
            "amount": float(Decimal(obj["amount_cents"]) / 100),
            "currency_code": obj["currency"],
        }

    def _apply_updates(self, payment_data):
        if self.provider_code != "paymob":
            return super()._apply_updates(payment_data)
        if self.state == "done":
            return

        obj = payment_data["obj"]

        success = obj.get("success")
        pending = obj.get("pending")

        if obj.get("is_refunded") is True or obj.get("is_voided") is True:
            return

        if success is True and pending is False:
            self._set_done()
            self.action_post_process()

        elif success is False and pending is True:
            self._set_pending()

        elif success is False and pending is False:
            message = (obj.get("data") or {}).get("message")
            self._set_error(message or "Paymob payment failed.")

