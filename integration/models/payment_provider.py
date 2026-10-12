from odoo import fields, models
class PaymentProvider(models.Model):
    _inherit = 'payment.provider'
    code = fields.Selection(
        selection_add=[("paymob", "Paymob")],
        ondelete={"paymob": "set default"},
    )
    paymob_secret_key = fields.Char(string="Secret Key", groups='base.group_system', copy=False)
    paymob_integration_id = fields.Integer(
        string="Paymob Card Integration ID",
        groups='base.group_system', copy=False
    )
    paymob_public_key = fields.Char(
        string="Paymob Public Key",
        copy=False,
    )
    paymob_hmac_secret = fields.Char(
        string="Paymob HMAC Secret",
        groups="base.group_system",
        copy=False,
    )
    def _get_default_payment_method_codes(self):
        self.ensure_one()
        if self.code != "paymob":
            return super()._get_default_payment_method_codes()
        return {'card'}