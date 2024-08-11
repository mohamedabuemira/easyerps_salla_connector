from odoo import models, fields, api

def clean_nones(value):
    """
    Recursively remove all None values from dictionaries and lists, and returns
    the result as a new dictionary or list.
    """
    if isinstance(value, list):
        return [clean_nones(x) for x in value if x ]
    elif isinstance(value, dict):
        return {
            key: clean_nones(val)
            for key, val in value.items()
            if val 
        }
    else:
        return value
class PaymentMethods(models.Model):
    _inherit = "account.payment.method"

    salla_id = fields.Integer()
    slug = fields.Char()

    def action_fetch(self):
        sync_ids = self.env['salla.sync'].search([('user_id', '=', self.env.user.id)])
        if sync_ids:
            self.env['salla.fetch.filter.wizard'].search([('current_sync_id', 'in', sync_ids.ids)]).unlink()
            sync_ids.unlink()

        temp_salla_sync_line = self.env['salla.sync.line'].search([])
        if temp_salla_sync_line:
            temp_salla_sync_line.unlink()

        if self.salla_id > 0:
            current_fetch_sync_id = self.env['salla.sync'].create({'current_model': self._name,
                                                                   'current_record_id': '% s,% s' % (
                                                                   self._name, self.id)})
            fetch_id = self.env['salla.fetch.filter.wizard'].create({'current_sync_id': current_fetch_sync_id.id})
            view = self.env.ref('easyerps_salla_connector.view_minimal_fetch_filter_wizard')
            result = {
                'name': _("Import Wizard"),
                'view_mode': 'form',
                'view_id': view.id,
                'view_type': 'form',
                'res_model': 'salla.fetch.filter.wizard',
                'res_id': fetch_id.id,
                'type': 'ir.actions.act_window',
                'target': 'new',
            }
            if self.salla_id:
                fetch_id.write(
                    {'value': str(self.salla_id),
                     'endpoint_field_id': self.env.ref('easyerps_salla_connector.salla_endpoint_product_id_filter')
                     }
                )
        else:
            current_fetch_sync_id = self.env['salla.sync'].create({'current_model': self._name})
            fetch_id = self.env['salla.fetch.filter.wizard'].create({'current_sync_id': current_fetch_sync_id.id})
            view = self.env.ref('easyerps_salla_connector.view_salla_first_fetch_filter_wizard')

            result = {
                'name': _("Import Wizard"),
                'view_mode': 'form',
                'view_id': view.id,
                'view_type': 'form',
                'res_model': 'salla.fetch.filter.wizard',
                'res_id': fetch_id.id,
                'type': 'ir.actions.act_window',
                'target': 'new',
            }
        return result
    
    @api.model
    def get_endpoint(self):
        return 'payment/methods'
    
    def _get_payment_method_information(self):
        out = super()._get_payment_method_information()
        codes = self.search([]).mapped('code')
        for code in codes:
            out.update({code: {'mode': 'multi', 'domain': [('type', 'in', ('bank', 'cash'))]}})
        return out

    @api.model
    def x_2_odoo(self, data, mode='create'):
        result = {
            'salla_id': data.get('id'),
            'name': data.get('name'),
            'code': data.get('slug'),
            'payment_type': 'inbound'
        }
        if mode == 'abstract':
            return clean_nones(result)
        record_id = self.search([('code', '=', data.get('slug')), ('payment_type', '=', 'inbound')], limit=1)

        if mode in ['create', 'update']:
            if record_id:
                record_id.write({'salla_id': result.get('salla_id')})
            else:
                self.create(result)
        elif mode == 'delete':
            if record_id:
                record_id.unlink()

    def odoo_2_x(self):
        result = {
            "name": self.name,
            "name_en": self.name_en,
            "code": self.code,
            "mobile_code": self.phone_code,
        }
        return result

        # API CRUDS

    @api.model
    def odoo_2x_read_all(self):
        company = self.env.context.get('company_id', False)
        company_id = self.env.company
        response = None
        if company:
            company_id = self.env['res.company'].browse(company)
        if company_id:
            response = company_id.odoo_2_x_crud('GET', 'payment/methods', payload=None)
        if response and response.get('data'):
            for rec in response.get('data'):
                self.x_2_odoo(rec)

    def odoo_2x_read(self):
        company = self.env.context.get('company_id', False)
        company_id = self.env.company
        response = None
        if company:
            company_id = self.env['res.company'].browse(company)
        if company_id and self.salla_id:
            response = company_id.odoo_2_x_crud('GET', 'payment/methods/' + self.salla_id, payload=None)
        if response and response.get('data'):
            self.x_2_odoo(response.get('data'))
