from odoo import models, fields, api, _
from odoo.exceptions import UserError

FILTERS = [('category', 'Category'),
           ('keyword', 'Keyword'),
           ('page', 'Page'),
           ('per_page', 'Per Page'),
           ('status', 'Status')]
OBJECT_LIST = [
    ('res.country', 'COUNTRIES'),
    # ('res.city', 'CITIES'),
    # ('res.currency', 'CURRENCIES'),
    ('res.company.branch', 'BRANCHES'),
    ('salla.webhooks', 'WEBHOOKS'),
    ('salla.affiliates', 'AFFILIATES'),
    ('salla.advertisement', 'ADVERTISEMENTS'),
    ('salla.coupon', 'COUPONS'),
    ('salla.offers', 'OFFERS'),
    ('account.tax', 'TAXES'),
    ('account.payment.method', 'PAYMENT METHODS'),
    ('product.brand', 'BRANDS'),
    ('product.tags', 'PRODUCT TAGS'),
    ('product.category', 'CATEGORIES'),
    ('product.product', 'PRODUCTS'),
    ('sale.order.tags', 'ORDERS TAGS'),
    ('sale.order.status', 'ORDERS STATUS'),
    ('shipping.company', 'SHIPPING COMPANY'),
    ('shipping.rules', 'SHIPPING RULES'),
    ('shipping.zone', 'SHIPPING ZONE'),
    ('customer.groups', 'CUSTOMER GROUPS'),
    ('res.partner', 'CUSTOMERS'),
    ('sale.order', 'ORDERS'),
]


class SallaEndpointFields(models.Model):
    _name = 'salla.endpoint.fields'
    _description = 'salla.endpoint.fields'

    name = fields.Char(required=True)
    model_name = fields.Char(required=True)


class FilterSelector(models.Model):
    _name = 'salla.filter.selector'
    _description = 'Filter Selector'

    name = fields.Char(required=True)
    field_type = fields.Selection([('integer', 'Innteger'),
                                   ('bool', 'Boolean'),
                                   ('string', 'String'),
                                   ('array', 'Array')], require=True)
    current_model = fields.Char(required=True)


class FecthFilter(models.TransientModel):
    _name = 'salla.fetch.filter'
    _description = 'Salla Import Filter'

    name = fields.Many2one('salla.filter.selector', 'Filter', required=True)
    value = fields.Char()


class FecthFilterWizard(models.TransientModel):
    _name = 'salla.fetch.filter.wizard'
    _description = 'Salla Import Filter Wizard'

    current_sync_id = fields.Many2one('salla.sync', required=True)
    current_model = fields.Selection(related='current_sync_id.current_model')
    filter_ids = fields.Many2many('salla.fetch.filter', 'wizar_salla_fetch_filter_rel',
                                  string="Fiters", ondelete='cascade')
    object_ids = fields.Many2many('auto.syncer.objects', relation='salla_fetch_autosynce_rel', string='Objects')
    endpoint_field_id = fields.Many2one('salla.endpoint.fields')
    value = fields.Char()
    select_mode = fields.Selection([('create_update', 'Create and Update'),
                                   ('update', 'Update')], default='create_update')
    country_id=fields.Many2one('res.country')

    def fetch_from_salla(self):
        filter = {}
        for fl in self.filter_ids:
            value = fl.value
            if fl.name.field_type == 'integer':
                try:
                    value = int(value)
                except Exception:
                    try:
                        value = float(value)
                    except Exception:
                        raise UserError(f'{fl.name.name}:Must be a number')
            elif fl.name.field_type == 'bool':
                if value:
                    value = True
                else:
                    value = False
            elif fl.name.field_type == 'array':
                value = value.replace('[', '').replace(']', '').split(',')
                temp_val = []
                for vals in value:
                    try:
                        temp_val.append(int(vals))
                    except Exception:
                        raise UserError(f'{fl.name.name}:All elt in the array must be integers')

            filter.update({fl.name.name: value})
        if self.current_model != 'all':
            self.process_fetch(self.current_model, filter)

            view = self.env.ref('easyerps_salla_connector.view_salla_sync_wizard')
            return {
                'name': _("Import Sync"),
                'view_mode': 'form',
                'view_id': view.id,
                'view_type': 'form',
                'res_model': 'salla.sync',
                'res_id': self.current_sync_id.id,
                'type': 'ir.actions.act_window',
                'target': 'new',
            }
        elif self.object_ids:
            for obj in self.object_ids:
                self.process_fetch(obj.model_name, filter)
            self.current_sync_id.write({'object_ids': [(6, 0, self.object_ids.ids)],'select_mode':self.select_mode})
            #self.process_message()
            view = self.env.ref('easyerps_salla_connector.view_minima_sync_wizard')
            return {
                'name': _("Import Sync"),
                'view_mode': 'form',
                'view_id': view.id,
                'view_type': 'form',
                'res_model': 'salla.sync',
                'res_id': self.current_sync_id.id,
                'type': 'ir.actions.act_window',
                'target': 'new',
            }
            #models_list = self.object_ids.mapped('model_name')
            # self.env.company.sync_selected_from_salla(models_list)

    def process_fetch(self, model_name, filter):
        if model_name == 'res.city':
            country_ids = self.env['res.country'].search([('salla_id', '>', 0)])
            #salla_ids = country_ids.mapped('salla_id')
            if self.country_id and self.country_id.salla_id:
                self.current_sync_id.odoo_2x_read_all(f'countries/{self.country_id.salla_id}/cities', model_name, payload=filter)
        elif model_name=='res.currency':
            self.current_sync_id.odoo_2x_read_all('currencies/available', model_name, payload=filter)
        else:
            self.current_sync_id.odoo_2x_read_all(self.env[model_name].get_endpoint(), model_name, payload=filter)

    def process_message(self):
        if self.current_sync_id:
            self.current_sync_id.process_message()

    def minimal_fetch(self):
        endpoint = self.env[self.current_model].get_endpoint()+'/'
        if self.endpoint_field_id.name == 'ID':
            endpoint += self.value
        else:
            endpoint += str(self.endpoint_field_id.name)+'/'+self.value
        self.current_sync_id.odoo_2x_read(endpoint=endpoint, model_name=self.current_model)
        view = self.env.ref('easyerps_salla_connector.view_salla_merge_sync_wizard')
        return {
            'name': _("Import Sync"),
            'view_mode': 'form',
            'view_id': view.id,
            'view_type': 'form',
            'res_model': 'salla.sync',
            'res_id': self.current_sync_id.id,
            'type': 'ir.actions.act_window',
            'target': 'new',
        }

    def salla_first_fetch(self):
        filter = {}
        for fl in self.filter_ids:
            value = fl.value
            if fl.name.field_type == 'integer':
                try:
                    value = int(value)
                except Exception:
                    try:
                        value = float(value)
                    except Exception:
                        raise UserError(f'{fl.name.name}:Must be a number')
            elif fl.name.field_type == 'bool':
                if value:
                    value = True
                else:
                    value = False
            elif fl.name.field_type == 'array':
                value = value.replace('[', '').replace(']', '').split(',')
                temp_val = []
                for vals in value:
                    try:
                        temp_val.append(int(vals))
                    except Exception:
                        raise UserError(f'{fl.name.name}:All elt in the array must be integers')

            filter.update({fl.name.name: value})
        self.process_fetch(self.current_model, filter)

        view = self.env.ref('easyerps_salla_connector.view_salla_first_merge_sync_wizard')
        return {
            'name': _("Import Sync"),
            'view_mode': 'form',
            'view_id': view.id,
            'view_type': 'form',
            'res_model': 'salla.sync',
            'res_id': self.current_sync_id.id,
            'type': 'ir.actions.act_window',
            'target': 'new',
        }

