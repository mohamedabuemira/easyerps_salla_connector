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


class AdvertisementType(models.Model):
    _name = 'salla.adv.type'
    _description = 'salla advertisement type'

    salla_id = fields.Integer()
    name = fields.Selection([('category', 'Category'),
                             ('page', 'Page'),
                             ('product', 'Product'),
                             ('offers', 'Offers'),
                             ('without_url', 'without Url'),
                             ('external_link', 'External Link')], default='product')
    link = fields.Char()


class SallaAAdvertisement(models.Model):
    _name = 'salla.advertisement'
    _description = 'salla Advertisement'

    salla_id = fields.Integer()
    name = fields.Char('Title')
    description = fields.Text()
    type = fields.Selection([('category', 'Category'),
                             ('page', 'Page'),
                             ('product', 'Product'),
                             ('offers', 'Offers'),
                             ('without_url', 'without Url'),
                             ('external_link', 'External Link')], default='without_url')
    product_id = fields.Many2one('product.product', domain="[('tmpl_salla_id', '>', 0)]")
    category_id = fields.Many2one('product.category', domain="[('salla_id', '>', 0)]")
    page_id = fields.Char()
    link = fields.Char()
    icon = fields.Char()
    font_color = fields.Char()
    background_color = fields.Char()
    expire_date = fields.Datetime()
    pages = fields.Char()

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

    def to_unaware_date(self, curdate):
        if curdate:
            my_data = curdate.get('date')
            my_data = my_data.split('.')[0]
            return my_data
        return None

    @api.model
    def get_endpoint(self):
        return 'advertisements'

    @api.model
    def x_2_odoo(self, data, mode='create'):
        result = {
            'salla_id': data.get('id'),
            'name': data.get('title'),
            'description': data.get('description'),
            'type': data.get('type').get('name'),
        }

        if mode == 'abstract':
            return clean_nones(result)
        if data.get('type'):
            if data.get('type').get('name') == 'product':
                itme_id = self.env['product.product'].search(
                    [('tmpl_salla_id', '=', data.get('type').get('id'))], limit=1)
                result.update(product_id=itme_id.id)
            elif data.get('type').get('name') == 'category':
                itme_id = self.env['product.category'].search([('salla_id', '=', data.get('type').get('id'))], limit=1)
                result.update(category_id=itme_id.id)
            elif data.get('type').get('name') == 'page':
                itme_id = data.get('type').get('id')
                result.update(page_id=itme_id)
            if data.get('type').get('link'):
                if data.get('type').get('name') == 'external_link':
                    link = data.get('type').get('link')
                    result.update(link=link)

        if data.get('style'):
            result.update({
                'icon': data.get('style').get('icon'),
                'font_color': data.get('style').get('font_color'),
                'background_color': data.get('style').get('background_color'),
            })
        if data.get('expire_date'):
            result.update(expire_date=self.to_unaware_date(data.get('expire_date')))
        if data.get('pages'):
            result.update(pages=','.join(data.get('pages')))
        # if mode not in ['from_read','delete']:
        #    return self.odoo_2x_read('advertisements/' + str(data.get('id')))
        record_id = self.search([('salla_id', '=', result.get('salla_id'))], limit=1)

        if mode in ['create', 'update', 'from_read']:
            if record_id:
                record_id.with_context(from_salla=True).write(result)
            else:
                self.with_context(from_salla=True).create(result)
        elif mode == 'delete':
            if record_id:
                record_id.with_context(from_salla=True).unlink()

    def odoo_2_x(self):
        result = {
            "title": self.name,
            "description": self.description,
            "type": {
                'name': self.type,
            },
            "expire_date": fields.Datetime.to_string(self.expire_date),
            "pages": self.pages.split(',')
        }
        if self.type == 'category':
            result.get('type').update(id=self.category_id.salla_id)
        elif self.type == 'product':
            result.get('type').update(id=self.product_id.tmpl_salla_id)
        elif self.type == 'page':
            result.get('type').update(id=self.page_id)
        elif self.type == 'external_link':
            result.get('type').update(link=self.link)
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
            response = company_id.odoo_2_x_crud('POST', 'advertisements', payload_json=record)
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
            response = company_id.odoo_2_x_crud('GET', 'advertisements', payload=None)
        if response and response.get('data'):
            for rec in response.get('data'):
                self.x_2_odoo(rec)

    def odoo_2x_read(self, endpoint=None):
        if not endpoint:
            endpoint = 'advertisements/' + str(self.salla_id)
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
            endpoint = 'advertisements/' + str(self.salla_id)
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
                response = company_id.odoo_2_x_crud('DELETE', 'advertisements/' + str(rec.salla_id), payload=None)
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
