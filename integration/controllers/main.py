from odoo import http
from odoo.http import request
import json
import hmac
import hashlib

from decimal import Decimal, ROUND_HALF_UP

class PaymobController(http.Controller):
    @http.route(
        "/payment/paymob/webhook",
        type="http",
        auth="public",
        methods=["POST"],
        csrf=False,
    )
    def paymob(self, **kwargs):
        keys = [
            "amount_cents",
            "created_at",
            "currency",
            "error_occured",
            "has_parent_transaction",
            "id",
            "integration_id",
            "is_3d_secure",
            "is_auth",
            "is_capture",
            "is_refunded",
            "is_standalone_payment",
            "is_voided",
            "order.id",
            "owner",
            "pending",
            "source_data.pan",
            "source_data.sub_type",
            "source_data.type",
            "success",
        ]
        try:
            data = json.loads(request.httprequest.get_data())
            obj = data["obj"]
            if not isinstance(obj, dict):
                raise ValueError("Invalid payment object")
            values = []
            for key in keys:
                value = obj
                for part in key.split("."):
                    value = value[part]
                if isinstance(value, bool):
                    value = str(value).lower()
                elif value is None:
                    value = ""
                else:
                    value = str(value)
                values.append(value)
        except (ValueError, TypeError, KeyError, IndexError):
            return request.make_response(
                "Invalid webhook payload", status=400
            )
        message = "".join(values)
        integration_id = obj["integration_id"]

        provider = request.env["payment.provider"].sudo().search([
            ("code", "=", "paymob"),
            ("paymob_integration_id", "=", str(integration_id)),
        ], limit=1)
        if not provider or not provider.paymob_hmac_secret:
            return request.make_response("provider not found", status=400)
        secret = provider.paymob_hmac_secret
        calculated_hmac = hmac.new(
            secret.encode("utf-8"),
            message.encode("utf-8"),
            hashlib.sha512
        ).hexdigest()
        received_hmac = request.httprequest.args.get("hmac", "")
        if not hmac.compare_digest(calculated_hmac, received_hmac):
            return request.make_response("Invalid HMAC", status=403)
        order = obj.get("order")

        if not isinstance(order, dict):
            return request.make_response("Invalid order data", status=400)

        order_id = order.get("id")
        if not order_id:
            return request.make_response("Order ID missing", status=400)
        payment = request.env["payment.transaction"].sudo().search([
            ("paymob_order_id", "=", str(order_id)),
            ("provider_id", "=", provider.id),
        ], limit=1)

        if not payment:
            return request.make_response("Transaction not found", status=404)
        currency = obj.get("currency")
        if not currency:
            return request.make_response("Currency not found", status=400)
        payment_currency = payment.currency_id.name
        if currency != payment_currency:
            return request.make_response("Currency mismatch", status=400)
        amount_cents = obj.get("amount_cents")

        if amount_cents is None:
            return request.make_response("Amount missing", status=400)
        try:
            paymob_amount = int(amount_cents)
        except (TypeError, ValueError):
            return request.make_response("Invalid amount", status=400)

        odoo_amount = int(
            (Decimal(str(payment.amount)) * 100).quantize(
                Decimal("1"), rounding=ROUND_HALF_UP
            )
        )

        if paymob_amount != odoo_amount:
            return request.make_response("Amount mismatch", status=400)
        success = obj.get("success")
        pending = obj.get("pending")
        if not isinstance(success, bool) or not isinstance(pending, bool):
            return request.make_response("Invalid payment status", status=400)
        payment._process("paymob", {"obj": obj})
        return request.make_response("ok", status=200)
