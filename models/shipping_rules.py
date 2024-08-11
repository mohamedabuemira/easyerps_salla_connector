from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


def clean_nones(value):
    """
    Recursively remove all None values from dictionaries and lists, and returns
    the result as a new dictionary or list.
    """
    if isinstance(value, list):
        return [clean_nones(x) for x in value if x]
    elif isinstance(value, dict):
        return {
            key: clean_nones(val)
            for key, val in value.items()
            if val
        }
    else:
        return value


class ShippingRestrictions(models.Model):
    _name = 'shipping.restrictions'
    _description = 'Ŝhipping Restrictions'
    type = fields.Selection([('cart-price', 'Cart Price'),
                             ('cart-weight', 'Cart Weight'),
                             ('category', 'Category'),
                             ('specific-area', 'Specific Area'),
                             ('customer-group', 'Customer Group')])
    condition = fields.Selection([('==', 'Equal'),
                                  ('!=', 'Not Equal'),
                                  ('>', 'Greater than'),
                                  ('>=', 'Greater or Equal'),
                                  ('<', 'Less Than'),
                                  ('<=', 'Less or Equal')])
    value = fields.Char()

    rule_id = fields.Many2one('shipping.rules')


class ShippingRules(models.Model):
    _name = 'shipping.rules'
    _desription = 'Shipping Rule'

    salla_id = fields.Integer()
    name = fields.Char('Title')
    status = fields.Selection([('active', 'Active'), ('inactive', 'Inactive')], default='active')
    shipping_companies_ids = fields.Many2many(
        'shipping.company', relation='shipping_company_roules_rel', string='Companies')
    restrictions = fields.One2many('shipping.restrictions', 'rule_id', 'Restrictions')



    def action_pull(self):
        self.env['salla.pull.filter.wizard'].search([('user_id', '=', self.env.user.id)]).unlink()
        pull_id = self.env['salla.pull.filter.wizard'].create({'current_model': self._name})
        pullset = []
        pullset.append((0, 0, {'odoo_link_id': '% s,% s' % (self._name, self.id)}))
        pull_id.write({'line_ids': pullset})
        view = self.env.ref('easyerps_salla_connector.view_minimal_pull_salla_filter_wizard')
        result = {
            'name': _("Pull Wizard"),
            'view_mode': 'form',
            'view_id': view.id,
            'view_type': 'form',
            'res_model': 'salla.pull.filter.wizard',
            'res_id': pull_id.id,
            'type': 'ir.actions.act_window',
            'target': 'new',

        }

        if self.salla_id:
            pull_id.write(
                {
                    'value': str(self.salla_id),
                    'endpoint_field_id': self.env.ref('easyerps_salla_connector.salla_endpoint_product_id_filter')
                }
            )
        return result

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
        return 'shipping/rules'

    @api.model
    def x_2_odoo(self, data, mode='create'):
        result = {
            'salla_id': data.get('id'),
            'name': data.get('name'),
            'status': data.get('status')
        }
        if mode == 'abstract':
            return clean_nones(result)
        if mode not in ['from_read','delete']:
            return self.odoo_2x_read('shipping/rules/' + str(data.get('id')))

        if data.get('shipping_companies_ids'):
            company_ids = self.env['shipping.company'].search([('salla_id', 'in', data.get('shipping_companies_ids'))])
            result.update(shipping_companies_ids=[(6, 0, company_ids.ids)])

        record_id = self.search([('salla_id', '=', result.get('salla_id'))], limit=1)
        if record_id:
            self.env['shipping.restrictions'].search([('rule_id', '=', record_id.id)]).unlink()
        if data.get('restrictions'):
            restrictions_ids = []
            for restr in data.get('restrictions'):
                restrictions_ids.append((0, 0, {'type': restr.get('type'),
                                                'condition': restr.get('condition'),
                                                'value': restr.get('value')}))
            result.update(restrictions=restrictions_ids)

        if mode in ['create', 'update','from_read']:
            if record_id:
                record_id.with_context(from_salla=True).write(result)
            else:
                self.with_context(from_salla=True).create(result)
        elif mode == 'delete':
            if record_id:
                record_id.with_context(from_salla=True).unlink()

    def odoo_2_x(self):
        get_param = self.env['ir.config_parameter'].sudo().get_param
        base_url = get_param('web.base.url')
        logo_image_path = f'{base_url}/web/image?model={self._name}&id={self.id}&field=logo'
        banner_image_path = f'{base_url}/web/image?model={self._name}&id={self.id}&field=banner'
        result = {
            "name": self.name,
            "description": self.description,
            "logo": logo_image_path or None,
            "banner": banner_image_path or None,
        }
        if self.salla_id:
            result['id'] = self.salla_id
        return result

    # API CRUDS
    def odoo_2x_create(self):
        record = self.odoo_2_x()
        company = self.env.context.get('company_id', False)
        company_id = self.env.company
        response = None
        if company:
            company_id = self.env['res.company'].browse(company)
        if company_id:
            response = company_id.odoo_2_x_crud('POST', 'shipping/rules', payload_json=record)
        if response and response.get('data'):
            self.with_context(from_salla=True).write({'salla_id': response.get('data').get('id')})

    @api.model
    def odoo_2x_read_all(self):
        company = self.env.context.get('company_id', False)
        company_id = self.env.company
        response = None
        if company:
            company_id = self.env['res.company'].browse(company)
        if company_id:
            response = company_id.odoo_2_x_crud('GET', 'shipping/rules', payload=None)
        if response and response.get('data'):
            for rec in response.get('data'):
                self.x_2_odoo(rec)

    def odoo_2x_read(self, endpoint=None):
        if not endpoint:
            endpoint = 'shipping/rules/' + str(self.salla_id)
        company = self.env.context.get('company_id', False)
        company_id = self.env.company
        response = None
        if company:
            company_id = self.env['res.company'].browse(company)
        if company_id:
            response = company_id.odoo_2_x_crud('GET', endpoint, payload=None)
        if response and response.get('data'):
            self.x_2_odoo(response.get('data'), mode='from_read')

    def odoo_2x_update(self, endpoint=None):
        if not endpoint:
            endpoint = 'shipping/rules/' + str(self.salla_id)
        record = self.odoo_2_x()
        company = self.env.context.get('company_id', False)
        company_id = self.env.company
        response = None
        if company:
            company_id = self.env['res.company'].browse(company)
        if company_id and self.salla_id:
            response = company_id.odoo_2_x_crud('PUT', endpoint, payload_json=record)
        return response

    def odoo_2x_delete(self):
        company = self.env.context.get('company_id', False)
        company_id = self.env.company
        response = None
        if company:
            company_id = self.env['res.company'].browse(company)
        if company_id and self.salla_id:
            for rec in self:
                response = company_id.odoo_2_x_crud('DELETE', 'shipping/rules/' + str(rec.salla_id), payload=None)
        return response

    @api.model
    def create(self, vals):
        result = super().create(vals)
        company_id = self.env.company
        if not self.env.context.get('from_salla', False) and company_id.is_salla_shop:
            try:
                if self.env.company.check_sync(self._name) and self.is_salla:
                    result.odoo_2x_create()
            except Exception as error:
                raise ValidationError(error)
        return result

    def write(self, vals):
        result = super().write(vals)
        company_id = self.env.company
        if not self.env.context.get('from_salla', False) and company_id.is_salla_shop:
            try:
                if self.env.company.check_sync(self._name) and self.is_salla:
                    self.odoo_2x_update()
            except Exception as error:
                raise ValidationError(error)
        return result

    def unlink(self):
        company_id = self.env.company
        if not self.env.context.get('from_salla', False) and company_id.is_salla_shop:
            try:
                if self.env.company.check_sync(self._name) and self.is_salla:
                    self.odoo_2x_delete()
            except Exception as error:
                raise ValidationError(error)
        return super().unlink()
