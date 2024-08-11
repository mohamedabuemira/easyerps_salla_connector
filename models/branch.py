from odoo import models, api, fields, _
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


class WoringHours(models.Model):
    _name = 'working.hours'
    _description = 'Workin Hours'
    name = fields.Selection(
        [('sunday', 'Sunday'),
         ('monday', 'Monday'),
         ('tuesday', 'Tuesday'),
         ('wednesday', 'Wednesday'),
         ('thursday', 'Thursday'),
         ('friday', 'Friday'),
         ('saturday', 'saturday')
         ], 'Day'
    )
    branch_id = fields.Many2one('res.company.branch')
    from_time = fields.Char()
    to_time = fields.Char()
    enabled = fields.Boolean(default=True)


class Branch(models.Model):
    _name = 'res.company.branch'
    _description = "company branch"

    name = fields.Char()
    company_id = fields.Many2one('res.company')
    parent_id = fields.Many2one('res.company.branch')
    salla_id = fields.Integer()
    status = fields.Selection([('active','Active'),('inactive','Inactive')])
    latitude = fields.Float()
    longitude = fields.Float()
    telephone = fields.Char()
    whatsapp = fields.Char()
    phone = fields.Char()
    country_id = fields.Many2one('res.country')
    city_id = fields.Many2one('res.city')
    preparation_timestr = fields.Char()
    is_open = fields.Boolean()
    opening_time = fields.Char()
    closing_time = fields.Char()
    is_cod_available = fields.Boolean()
    type = fields.Selection([('branch', 'Branch'), ('warehouse', 'Warehouse')], default='branch')
    is_default = fields.Boolean()
    is_salla = fields.Boolean()
    is_salla_checker = fields.Boolean(compute='_compute_is_salla')
    address_description = fields.Char()
    additional_number = fields.Char()
    building_number = fields.Char()
    street = fields.Char()
    local = fields.Char()
    postal_code = fields.Char()
    cod_cost = fields.Float()
    workin_times = fields.One2many('working.hours', 'branch_id')
    warehouse_id=fields.Many2one('stock.warehouse')

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

    def arabic_to_english_days(self, ar):
        mapping = {
            'الأحد': 'sunday',
            'الإثنين': 'monday',
            'الثلاثاء': 'tuesday',
            'الأربعاء': 'wednesday',
            'الخميس': 'thursday',
            'الجمعة': 'friday',
            'السبت': 'saturday'
        }
        if ar in mapping:
            return mapping[ar]
        else:
            return False

    @api.depends('salla_id')
    def _compute_is_salla(self):
        for rec in self:
            isfalse = False
            if rec.salla_id:
                isfalse = True
            rec.is_salla = isfalse
            rec.is_salla_checker = isfalse

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
                                                               'current_record_id': '% s,% s' % (self._name, self.id)})
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

    @api.model
    def get_endpoint(self):
        return 'branches'

    @api.model
    def x_2_odoo(self, data, mode='create'):
        company = self.env.context.get('allowed_company_ids') and self.env.context.get('allowed_company_ids')[0] or None
        result = {
            'salla_id': data.get('id'),
            'name': data.get('name'),
            'cod_cost': data.get('cod_cost'),
            'status': data.get('status'),
            'latitude': data.get('location') and float(data.get('location').get('lat')) or 0.0,
            'longitude': data.get('location') and float(data.get('location').get('lng')) or 0.0,
            'telephone': data.get('contacts') and data.get('contacts').get('telephone'),
            'phone': data.get('contacts') and data.get('contacts').get('phone'),
            'type': data.get('type'),
            'whatsapp': data.get('contacts') and data.get('contacts').get('whatsapp') or None,
            'country_id': data.get('country') and self.env['res.country'].search(
                [('salla_id', '=', data.get('country').get('id'))], limit=1).id or None,
            "preparation_timestr": data.get('preparation_time'),
            'is_open': data.get('is_open'),
            'opening_time': data.get('closest_time') and data.get('closest_time').get('from') or None,
            'closing_time': data.get('closest_time') and data.get('closest_time').get('to') or None,
            'is_cod_available': data.get('is_cod_available', False),
            'is_default': data.get('is_default'),
            'address_description': data.get('address_description'),
            'additional_number': data.get('additional_number'),
            'building_number': data.get('building_number'),
            'street': data.get('street'),
            'local': data.get('local'),
            'postal_code': data.get('postal_code')
        }
        if mode == 'abstract':
            return clean_nones(result)

        record_id = self.search([('salla_id', '=', result.get('salla_id'))], limit=1)
        if data.get('city'):
            city_id = self.env['res.city'].search([('salla_id', '=', data.get('city').get('id'))], limit=1)
            if city_id:
                result['city_id'] = city_id.id
            else:
                country_id = self.env['res.country'].search([('salla_id', '=', data.get('country').get('id'))], limit=1)
                self.env['res.city'].odoo_2x_read_per_country(country_id)
                city_id = self.env['res.city'].search([('salla_id', '=', data.get('city').get('id'))], limit=1)
                if city_id:
                    result['city_id'] = city_id.id


        if company:
            result.update(company_id=company)
        if mode in ['create', 'update']:
            if record_id:
                record_id.with_context(from_salla=True).write(result)
            else:
                record_id = self.with_context(from_salla=True).create(result)

        if data.get('working_hours') and data.get('type') == 'branch':
            work_records = []
            for hours in data.get('working_hours'):
                records = [
                    {
                        'name': self.arabic_to_english_days(hours.get('name')),
                        'from_time': x.get('from'),
                        'to_time': x.get('to'),
                        'enabled': True
                    }
                    for x in hours.get('times')
                ]
                work_records += records
            if record_id:
                self.env['working.hours'].search([('branch_id', '=', record_id.id)]).unlink()
                for rc in work_records:
                    rc.update(branch_id=record_id.id)
                    time_length = len(rc['from_time'])
                    index = 0
                    self.env['working.hours'].create(rc)
        elif mode == 'delete':
            if record_id:
                record_id.with_context(from_salla=True).unlink()

    def odoo_2_x(self):
        result = {
            "name": self.name,
            "status": self.status,
            'cod_cost': self.cod_cost,

            "contacts": {
                "phone": self.phone,
                "whatsapp": self.whatsapp,
                "telephone": self.telephone
            },
            "preparation_time": self.preparation_timestr,
            # "is_open": self.is_open,
            # "closest_time": {
            #     "from": self.opening_time and self.opening_time.to_string() or None,
            #     "to": self.closing_time and self.closing_time.to_string() or None
            # },
            "is_cod_available": self.is_cod_available,
            "is_default": self.is_default,
            "type": self.type,
            'address_description': self.address_description,
            'additional_number': self.additional_number,
            'building_number': self.building_number,
            'street': self.street,
            'local': self.local,
            'postal_code': self.postal_code,
        }
        if self.workin_times and self.type == 'branch':
            rec_wk = {}
            for wk in self.workin_times:
                if not wk.name in rec_wk:
                    rec_wk[wk.name] = {'enabled': wk.enabled and 'on' or 'off',
                                       'from': [], 'to': []}

                rec_wk[wk.name]['from'].append(wk.from_time)
                rec_wk[wk.name]['to'].append(wk.to_time)

            result.update(working_hours=rec_wk)
        if self.latitude and self.longitude:
            result.update(location=f'{self.latitude},{self.longitude}')
        if self.country_id and self.country_id.salla_id:
            result["country_id"] = self.country_id.salla_id
        if self.city_id and self.city_id.salla_id:
            result["city_id"] = self.city_id.salla_id
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
            response = company_id.odoo_2_x_crud('POST', 'branches', payload_json=record)
        if response and response.get('data'):
            self.with_context(from_salla=True).write({'salla_id': response.get('data').get('id')})

    @ api.model
    def odoo_2x_read_all(self):
        company = self.env.context.get('company_id', False)
        company_id = self.env.company
        response = None
        if company:
            company_id = self.env['res.company'].browse(company)
        if company_id:
            response = company_id.odoo_2_x_crud('GET', 'branches', payload=None)
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
            response = company_id.odoo_2_x_crud('GET', 'branches/' + self.salla_id, payload=None)
        if response and response.get('data'):
            self.with_company(company_id.id).x_2_odoo(response.get('data'))

    def odoo_2x_update(self, endpoint=None):
        if not endpoint:
            endpoint = 'branches/' + str(self.salla_id)
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
                response = company_id.odoo_2_x_crud('DELETE', 'branches/' + str(rec.salla_id), payload=None)
        return response

    @ api.model
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
