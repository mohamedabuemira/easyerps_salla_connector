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


class ShippingZones(models.Model):
    _name = 'shipping.zone'
    _description = 'Shipping Zone'

    salla_id = fields.Integer()
    name = fields.Char()
    company_id = fields.Many2one('shipping.company')
    all_country_id = fields.Boolean('All Country')
    country_id = fields.Many2one('res.country')
    all_city_id = fields.Boolean('All City')
    city_id = fields.Many2one('res.city')
    cities_excluded_ids = fields.Many2many('res.city', relation='shipping_zone_res_city_rel', string="Excluded Cities")
    fees_amount = fields.Float('Amount')
    currency_id = fields.Many2one('res.currency')
    fees_type = fields.Selection([('fixed', 'Fixed'),('rate', 'Rate') ],string='Fees Type', default="fixed")
    up_to_weight = fields.Integer(string='Maximum Allowed Weight')
    amount_per_unit = fields.Integer(string='Amount Per Unit')
    per_unit = fields.Integer(string='Per Unit Value')
    duration = fields.Char('Duration(days)')
    cod_fees = fields.Float('Cash on Delivery (COD) Fee')
    cod_activated = fields.Boolean('Whether or not Cash On Delivery')

    @api.onchange("country_id")
    def _onchange_country_id(self):
        if self.country_id:
            for rec in self:
                rec.city_id = False
                company = self.env.context.get('company_id', False)
                company_id = self.env.company
                response = None
                if company:
                    company_id = self.env['res.company'].browse(company)
                if company_id:
                    if rec.country_id.salla_id and rec.country_id.salla_id > 0 and not rec.country_id.city_processed:
                        self.env['res.city'].odoo_2x_read_per_country(rec.country_id)

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
        return 'shipping/zones'

    @api.model
    def x_2_odoo(self, data, mode='create'):
        result = {
            'salla_id': data.get('id'),
            'name': data.get('zone_code'),
            'duration':data.get('duration')
        }
        if mode == 'abstract':
            return clean_nones(result)
        record_id = self.search([('salla_id', '=', result.get('salla_id'))], limit=1)
        if data.get('cash_on_delivery'):
            result.update({
                'cod_fees':data.get('cash_on_delivery').get('fees'),
                'cod_activated':data.get('cash_on_delivery').get('status')
            })
        if data.get('company'):
            ship_cny_id = self.env['shipping.company'].search(
                [('salla_id', '=', data.get('company').get('id'))], limit=1)
            if ship_cny_id:
                result.update(company_id=ship_cny_id.id)
        if data.get('country'):
            if data.get('country').get('id') == -1:
                result.update(all_country_id=True)
            else:
                country_id = self.env['res.country'].search([('salla_id', '=', data.get('country').get('id'))], limit=1)
                if country_id:
                    result.update(country_id=country_id.id)
        if data.get('city'):
            if data.get('city').get('id') == -1:
                result.update(all_city_id=True)
            else:
                city_id = self.env['res.city'].search([('salla_id', '=', data.get('city').get('id'))], limit=1)
                if city_id:
                    result.update(city_id=city_id.id)

        if data.get('cities_excluded'):
            excl_ids = []
            for excl in data.get('cities_excluded'):
                excl_ids.append(excl.get('id'))
            cities = self.env['res.city'].search([('salla_id', 'in', excl_ids)])
            if cities:
                result.update(cities_excluded_ids=[(6, 0, cities.ids)])
        if data.get('fees'):
            fees = data.get('fees')
            currency_id = self.env['res.currency'].search([('name', '=', fees.get('currency'))], limit=1)
            result.update({
                'fees_amount': fees.get('amount'),
                'currency_id': currency_id and currency_id.id or None,
                'fees_type': fees.get('type'),
                'up_to_weight': fees.get('up_to_weight'),
                'amount_per_unit': fees.get('amount_per_unit'),
                'per_unit': fees.get('per_unit'),
                
            })

        if mode in ['create', 'update']:
            if record_id:
                record_id.with_context(from_salla=True).write(result)
            else:
                self.with_context(from_salla=True).create(result)
        elif mode == 'delete':
            if record_id:
                record_id.with_context(from_salla=True).unlink()

    def odoo_2_x(self):

        result = {
            'company': self.company_id and self.company_id.salla_id or None,
            'shipping':{
                'country': not self.all_country_id and self.country_id and self.country_id.salla_id or -1 ,
                'city': not self.all_city_id and self.city_id and self.city_id.salla_id or -1,
                'cities_excluded': self.cities_excluded_ids and self.cities_excluded_ids.mapped('salla_id') or [],
                'duration': self.duration,
                'cash_on_delivery': {
                    'fees': self.cod_fees,
                    'status': self.cod_activated,
                },
                'fees': {
                    'type': self.fees_type,
                    'amount': self.fees_amount,
                    'up_to_weight': self.up_to_weight,
                    'amount_per_unit': self.amount_per_unit,
                    'per_unit': self.per_unit
                }
            }
        }

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
            response = company_id.odoo_2_x_crud('POST', 'shipping/zones', payload_json=record)
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
            response = company_id.odoo_2_x_crud('GET', 'shipping/zones', payload=None)
        if response and response.get('data'):
            for rec in response.get('data'):
                self.x_2_odoo(rec)

    def odoo_2x_read(self):
        company = self.env.context.get('company_id', False)
        company_id = self.env.company
        response = None
        if company:
            company_id = self.env['res.company'].browse(company)
        if company_id :
            response = company_id.odoo_2_x_crud('GET', 'shipping/zones/' + str(self.salla_id), payload=None)
        if response and response.get('data'):
            self.x_2_odoo(response.get('data'))

    def odoo_2x_update(self, endpoint=None):
        if not endpoint:
            endpoint = 'shipping/zones/' + str(self.salla_id)
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
                response = company_id.odoo_2_x_crud('DELETE', 'shipping/zones/' + str(rec.salla_id), payload=None)
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

