from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging
_logger = logging.getLogger(__name__)

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


class SalesStatus(models.Model):
    _name = 'sale.order.status'
    _description = 'sales Order Status'

    salla_id = fields.Integer()
    parent_id = fields.Many2one('sale.order.status')
    original_id = fields.Integer()
    children_ids = fields.One2many('sale.order.status', 'parent_id')
    name = fields.Char()
    type = fields.Selection([('original', 'Original'), ('custom', 'Custom')], default='custom')
    slug = fields.Char()
    message = fields.Char()
    color = fields.Char()
    icon = fields.Char()
    sort = fields.Integer()
    is_active = fields.Boolean()

   

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
        return 'orders/statuses'

    @api.model
    def x_2_odoo(self, data, mode='create'):
        result = {
            'salla_id': data.get('id'),
            'name': data.get('name') or '',
            'type': data.get('type') or '',
            'slug': data.get('slug') or '',
            'message': data.get('message') or '',
            'original_id': data.get('original') and data.get('original').get('id') or '',
            

        }

        if mode == 'abstract':
            return clean_nones(result)

        if mode not in ['from_read','delete']:
            return self.odoo_2x_read('orders/statuses/' + str(data.get('id')))

        
        res_update = {
            'color':data.get('color'),
            'icon': data.get('icon'),
            'sort': data.get('sort'),
            'is_active': data.get('is_active'),
        }
        if data.get('parent') and data.get('parent').get('id'):
            parent_id = self.env['sale.order.status'].search(
                [('salla_id', '=', data.get('parent').get('id'))], limit=1)
            if parent_id:
                res_update.update(parent_id=parent_id.id)
        else:
            type = 'original'
            res_update.update(type=type)
        result.update(res_update)

        record_id = self.search([('salla_id', '=', result.get('salla_id'))], limit=1)

        if mode in ['create', 'update','from_read']:
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
            "type": self.type,
            "slug": self.slug,
            "message": self.message,
            "is_active":self.is_active,
        }
        if self.color:
            result.update(color=self.color)
        if self.icon:
            result.update(icon=self.icon)
        if self.sort:
            result.update(sort=self.sort)
        if self.parent_id and self.parent_id.salla_id:
            result.update(parent_id=self.parent_id.salla_id)
        
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
            response = company_id.odoo_2_x_crud('POST', 'orders/statuses', payload_json=record)
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
            response = company_id.odoo_2_x_crud('GET', 'orders/statuses', payload=None)
        if response and response.get('data'):
            for rec in response.get('data'):
                self.x_2_odoo(rec)

    def odoo_2x_read(self, endpoint=None):
        if not endpoint:
            endpoint = 'orders/statuses/' + str(self.salla_id)
        company = self.env.context.get('company_id', False)
        company_id = self.env.company
        response = None
        if company:
            company_id = self.env['res.company'].browse(company)
        if company_id :
            response = company_id.odoo_2_x_crud('GET', endpoint, payload=None)
        if response and response.get('data'):
            self.x_2_odoo(response.get('data'), mode='from_read')

    def odoo_2x_update(self, endpoint=None):
        if not endpoint:
            endpoint = 'orders/statuses/' + str(self.salla_id)
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
                response = company_id.odoo_2_x_crud('DELETE', 'orders/statuses/' + str(rec.salla_id), payload=None)
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
