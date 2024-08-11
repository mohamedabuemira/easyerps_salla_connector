from odoo import models, api, fields


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


class City(models.Model):
    _name = 'res.city'
    _description = 'res city'

    name = fields.Char()
    name_en = fields.Char()
    salla_id = fields.Integer()
    country_id = fields.Many2one('res.country')

    @api.model
    def get_endpoint(self):
        return 'cities'

    @api.model
    def x_2_odoo(self, data, mode='create'):
        result = {
            'salla_id': data.get('id'),
            'name': data.get('name'),
            'name_en': data.get('name_en'),
        }
        if mode == 'abstract':
            return clean_nones(result)
        if data.get('country_id'):
            country_id = self.env['res.country'].search([('salla_id', '=', data.get('country_id'))], limit=1)
            if country_id:
                result.update(country_id=country_id.id)
        record_id = self.search([('salla_id', '=', result.get('salla_id'))], limit=1)

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
            "name": self.name,
            "name_en": self.name_en,
        }
        if self.salla_id:
            result['id'] = self.salla_id
        return result

        # API CRUDS

    # @api.model
    # def odoo_2x_read_per_country(self):
    #     company = self.env.context.get('company_id', False)
    #     company_id = self.env.company
    #     response = None
    #     if company:
    #         company_id = self.env['res.company'].browse(company)
    #     if company_id:
    #         country_ids = self.env['res.country'].search(
    #             [('salla_id', '>', 0), ('city_processed', '=', False)], limit=1)
    #         if not country_ids:
    #             cron_id = self.env.sudo().ref('easyerps_salla_connector.fetch_salla_cities_cron')
    #             #cron_id = self.env['ir.cron'].sudo().search([('cron_name', '=', 'Import Salla Cities')])
    #             if cron_id:
    #                 cron_id.sudo().write({'active': False})
    #         # if not country_ids:
    #         #     self.env['res.country'].search([('salla_id', '>', 0)]).write({'city_processed': False})
    #         # country_ids = self.env['res.country'].search(
    #         #     [('salla_id', '>', 0), ('city_processed', '=', False)], limit=1)
    #         for country_id in country_ids:
    #             endpoint = 'countries/' + str(country_id.salla_id) + '/cities'
    #             response = company_id.odoo_2_x_crud(
    #                 'GET', endpoint, payload=None)
    #             out_data = []
    #             page = 1
    #             if response and response.get('pagination') and response.get('data'):
    #                 if response.get('pagination').get('count') < response.get('pagination').get('total'):
    #                     out_data += response.get('data')
    #                     total_pages = response.get('pagination').get('totalPages') - 1
    #                     while (total_pages > 0):
    #                         page += 1
    #                         response = company_id.odoo_2_x_crud('GET', endpoint, payload_json={'page': page})
    #                         if response and response.get('data'):
    #                             out_data += response.get('data')
    #                         total_pages -= 1
    #                 else:
    #                     out_data = response.get('data')
    #             elif response and response.get('data'):
    #                 out_data = response.get('data')
    #             for rec in out_data:
    #                 self.x_2_odoo(rec)
    #         if country_ids:
    #             country_ids.write({'city_processed': True})

    @api.model
    def odoo_2x_read_per_country(self, country):
        company = self.env.context.get('company_id', False)
        company_id = self.env.company
        response = None
        if company:
            company_id = self.env['res.company'].browse(company)
        if company_id:
            country_id = country
            if country_id.salla_id and country_id.salla_id > 0 and not country_id.city_processed:
                endpoint = 'countries/' + str(country_id.salla_id) + '/cities'
                response = company_id.odoo_2_x_crud(
                    'GET', endpoint, payload=None)
                out_data = []
                page = 1
                if response and response.get('pagination') and response.get('data'):
                    if response.get('pagination').get('count') < response.get('pagination').get('total'):
                        out_data += response.get('data')
                        total_pages = response.get('pagination').get('totalPages') - 1
                        while (total_pages > 0):
                            page += 1
                            response = company_id.odoo_2_x_crud('GET', endpoint, payload_json={'page': page})
                            if response and response.get('data'):
                                out_data += response.get('data')
                            total_pages -= 1
                    else:
                        out_data = response.get('data')
                elif response and response.get('data'):
                    out_data = response.get('data')
                for rec in out_data:
                    self.x_2_odoo(rec)
                country_id.write({'city_processed': True})

    @api.model
    def odoo_2x_read_all(self):
        company = self.env.context.get('company_id', False)
        company_id = self.env.company
        response = None
        if company:
            company_id = self.env['res.company'].browse(company)
        if company_id:
            country_ids = self.env['res.country'].search([('salla_id', '>', 0)])
            for country_id in country_ids:
                response = company_id.odoo_2_x_crud(
                    'GET', 'countries/' + str(country_id.salla_id) + '/cities', payload=None)
                if response and response.get('data'):
                    for rec in response.get('data'):
                        self.x_2_odoo(rec)


class ResCountry(models.Model):
    _inherit = 'res.country'

    name_ar = fields.Char()
    salla_id = fields.Integer()
    cities_ids = fields.One2many('res.city', 'country_id')
    city_processed = fields.Boolean(default=False)

    @api.model
    def get_endpoint(self):
        return 'countries'

    @api.model
    def x_2_odoo(self, data, mode='create'):
        result = {
            'salla_id': data.get('id'),
            'name': data.get('name_en'),
            'name_ar': data.get('name'),
            'phone_code': data.get('mobile_code') and data.get('mobile_code').replace('+', '') or '',
            'code': data.get('code')
        }
        if mode == 'abstract':
            return clean_nones(result)
        record_id = self.search(
            ['|', ('code', '=', data.get('code')),
             ('salla_id', '=', result.get('salla_id'))],
            limit=1)

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
            response = company_id.odoo_2_x_crud('GET', 'countries', payload=None)
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
            response = company_id.odoo_2_x_crud('GET', 'countries/' + self.salla_id, payload=None)
        if response and response.get('data'):
            self.x_2_odoo(response.get('data'))
