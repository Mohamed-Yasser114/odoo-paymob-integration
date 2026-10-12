from odoo import models


class AccountPaymentMethod(models.Model):
    _inherit = "account.payment.method"

    def _get_payment_method_information(self):
        res = super()._get_payment_method_information()
        res["paymob"] = {
            "mode": "electronic",
            "type": ("bank",),
        }
        return res