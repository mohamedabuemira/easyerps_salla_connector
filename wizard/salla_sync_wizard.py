import json
from odoo import models, fields, api, _
import logging
_logger = logging.getLogger(__name__)

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
    ('all', 'ALL')
]


class ProductFieldsMapping(models.Model):
    _name = 'product.fields.mapping'
    _description = 'Product.fields.mapping'

    name = fields.Char(required=True)
    fields_name = fields.Char(required=True)


class SallaSyncLine(models.TransientModel):
    _name = 'salla.sync.line'
    _description = 'Salla Sync Lines'
    _rec_name = 'name'

    name = fields.Char()
    odoo_link_id = fields.Reference(OBJECT_LIST)
    abstract = fields.Char()
    rawdata = fields.Text()
    sync_id = fields.Many2one('salla.sync')
    selected = fields.Boolean()
    model_name = fields.Char()


class SallaSync(models.TransientModel):
    _name = 'salla.sync'
    _description = 'Temp Salla Sync'

    user_id = fields.Many2one('res.users', default=lambda self: self.env.user)
    current_model = fields.Selection(OBJECT_LIST, required=True)
    current_record_id = fields.Reference(OBJECT_LIST)
    line_ids = fields.One2many('salla.sync.line', 'sync_id', ondelete='cascade')
    line_id = fields.Many2one('salla.sync.line', ondelete='cascade')
    current_date = fields.Datetime(default=fields.Datetime.now)
    record_count = fields.Integer()
    record_to_fetch = fields.Integer(compute='_compute_record_to_fetch')
    select_mode = fields.Selection([('create_update', 'Create and Update'),
                                   ('create', 'Create'),
                                   ('update', 'Update')], default='create_update')
    object_ids = fields.Many2many('auto.syncer.objects', relation='salla_sync_autosynce_rel', string='Objects')
    all_fields = fields.Boolean('All fields', default=True)
    message = fields.Text(compute="process_message")
    select_all = fields.Boolean(default=True)
    mapped_fields_ids = fields.Many2many(
        'product.fields.mapping', relation='sync_salla_product_fields_rel', string='Selected fields')

    @api.onchange('select_all')
    def _onchange_select_all(self):
        records = self.line_ids
        out_records = self.env['salla.sync.line']
        if self.select_mode == 'update':
            records = records.filtered(lambda x: x.odoo_link_id)
            self.line_ids.filtered(lambda x: not x.odoo_link_id).write({'selected': False})
        elif self.select_mode == 'create':
            records = records.filtered(lambda x: not x.odoo_link_id)
            self.line_ids.filtered(lambda x:  x.odoo_link_id).write({'selected': False})

        if self.select_all:
            records.write({'selected': True})
        else:
            records.write({'selected': False})

    @api.onchange('select_mode')
    def _onchange_select_mode(self):
        records = self.line_ids
        out_records = self.env['salla.sync.line']
        if self.select_mode == 'update':
            records = records.filtered(lambda x: x.odoo_link_id)
            self.line_ids.filtered(lambda x: not x.odoo_link_id).write({'selected': False})
        elif self.select_mode == 'create':
            records = records.filtered(lambda x: not x.odoo_link_id)
            self.line_ids.filtered(lambda x:  x.odoo_link_id).write({'selected': False})
        records.write({'selected': True})

    @api.depends('line_ids', 'line_ids.selected', 'select_mode')
    def _compute_record_to_fetch(self):
        for rec in self:
            if rec.line_ids:
                if rec.select_mode == 'create_update':
                    rec.record_to_fetch = len(rec.line_ids.filtered(lambda x: x.selected))
                elif rec.select_mode == 'update':
                    rec.record_to_fetch = len(rec.line_ids.filtered(lambda x: x.odoo_link_id and x.selected))
                elif rec.select_mode == 'create':
                    rec.record_to_fetch = len(rec.line_ids.filtered(lambda x: not x.odoo_link_id and x.selected))
                else:
                    rec.record_to_fetch = len(rec.line_ids.filtered(lambda x: x.selected))

            else:
                rec.record_to_fetch = 0

    def x_2_odoo(self, datas, model_name):
        odoo_model = model_name
        lines = []
        for data in datas:
            result = {
                'rawdata': json.dumps(data),
                'model_name': odoo_model,
                'selected': True
            }
            record_id = self.env[odoo_model]
            abstract = record_id.x_2_odoo(data, mode='abstract')
            result.update(name=str(abstract))
            if hasattr(record_id, 'salla_id'):
                record_id = self.env[odoo_model].search([('salla_id', '=', data.get('id'))], limit=1)
            elif hasattr(record_id, 'tmpl_salla_id'):
                record_id = self.env[odoo_model].search([('tmpl_salla_id', '=', data.get('id'))], limit=1)
            if record_id:
                result.update(odoo_link_id='% s,% s' % (odoo_model, record_id.id))
            lines.append((0, 0, result))
        self.write({'line_ids': lines})

    def odoo_2x_read_all(self, endpoint, model_name, payload=None):
        company = self.env.context.get('company_id', False)
        company_id = self.env.company
        response = None
        if company:
            company_id = self.env['res.company'].browse(company)
        if company_id:
            response = company_id.odoo_2_x_crud('GET', endpoint, payload_json=payload)
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

        if out_data:
            self.x_2_odoo(out_data, model_name)
        self.record_count += len(out_data)

    def odoo_2x_read(self, endpoint, model_name, payload=None):
        company = self.env.context.get('company_id', False)
        company_id = self.env.company
        response = None
        if company:
            company_id = self.env['res.company'].browse(company)
        if company_id:
            response = company_id.odoo_2_x_crud('GET', endpoint, payload_json=payload)
        if response and response.get('data'):
            self.with_company(company_id.id).x_2_odoo([response.get('data')], model_name)

    def action_fetch_selected(self):
        recset = self.line_ids.filtered(lambda x: x.selected)
        if self.select_mode == 'create_update':
            recset = self.line_ids.filtered(lambda x: x.selected)
        elif self.select_mode == 'update':
            recset = self.line_ids.filtered(lambda x: x.odoo_link_id and x.selected)
        elif self.select_mode == 'create':
            recset = self.line_ids.filtered(lambda x: not x.odoo_link_id and x.selected)

        for rec in recset:
            data = json.loads(rec.rawdata)
            
            if rec.model_name:
                if rec.model_name == 'sale.order' and data.get('id'):
                    endpoint = 'orders/' + str(data.get('id'))
                    if rec.odoo_link_id:
                        rec.odoo_link_id.odoo_2x_read(endpoint)
                    else:
                        self.env[rec.model_name].odoo_2x_read(endpoint)
                elif rec.model_name == 'product.product':
                    fields_list = []
                    if not self.all_fields:
                        fields_list = self.mapped_fields_ids.mapped('fields_name')
                    if rec.odoo_link_id:
                        rec.odoo_link_id.x_2_odoo(data, fieldslist=fields_list)
                    else:
                        self.env[rec.model_name].x_2_odoo(data, fieldslist=fields_list)
                else:
                    if rec.odoo_link_id:
                        rec.odoo_link_id.x_2_odoo(data)
                    else:
                        self.env[rec.model_name].x_2_odoo(data)
        result_id = self.env['result.dialog'].create({'name': 'Import Successfull'})
        view = self.env.ref('easyerps_salla_connector.view_resultr_wizard')
        return {
            'name': _("Message"),
            'view_mode': 'form',
            'view_id': view.id,
            'view_type': 'form',
            'res_model': 'result.dialog',
            'res_id': result_id.id,
            'type': 'ir.actions.act_window',
            'target': 'new',
        }

    def merge_selected(self):
        for rec in self.line_ids:
            data = json.loads(rec.rawdata)
            if rec.odoo_link_id:
                if self.current_model == 'sale.order' and data.get('id'):
                    endpoint = 'orders/' + str(data.get('id'))
                    rec.odoo_link_id.odoo_2x_read(endpoint)
                elif self.current_model == 'product.product':
                    fields_list = []
                    if not self.all_fields:
                        fields_list = self.mapped_fields_ids.mapped('fields_name')
                    rec.odoo_link_id.x_2_odoo(data, fieldslist=fields_list)
                else:
                    rec.odoo_link_id.x_2_odoo(data)
        result_id = self.env['result.dialog'].create({'name': 'Merge Successfull'})
        view = self.env.ref('easyerps_salla_connector.view_resultr_wizard')
        return {
            'name': _("Message"),
            'view_mode': 'form',
            'view_id': view.id,
            'view_type': 'form',
            'res_model': 'result.dialog',
            'res_id': result_id.id,
            'type': 'ir.actions.act_window',
            'target': 'new',
        }

    def merge_first_fetch(self):
        for rec in self.line_id:
            data = json.loads(rec.rawdata)
            if self.current_record_id:
                if self.current_model == 'sale.order' and data.get('id'):
                    self.current_record_id.with_context(from_salla=True).write({'salla_id': data.get('id')})
                    endpoint = 'orders/' + str(data.get('id'))
                    self.current_record_id.odoo_2x_read(endpoint)
                elif self.current_model == 'product.product':
                    self.current_record_id.with_context(from_salla=True).write({'tmpl_salla_id': data.get('id')})
                    fields_list = []
                    if not self.all_fields:
                        fields_list = self.mapped_fields_ids.mapped('fields_name')
                    self.current_record_id.x_2_odoo(data, fieldslist=fields_list)
                else:
                    self.current_record_id.with_context(from_salla=True).write({'salla_id': data.get('id')})
                    self.current_record_id.x_2_odoo(data)
        result_id = self.env['result.dialog'].create({'name': 'Merge Successfull'})
        view = self.env.ref('easyerps_salla_connector.view_resultr_wizard')
        return {
            'name': _("Message"),
            'view_mode': 'form',
            'view_id': view.id,
            'view_type': 'form',
            'res_model': 'result.dialog',
            'res_id': result_id.id,
            'type': 'ir.actions.act_window',
            'target': 'new',
        }

    @api.depends('object_ids', 'select_mode')
    def process_message(self):
        for rec in self:
            message = ''
            for obj in rec.object_ids:
                total = len(rec.line_ids.filtered(lambda x: x.model_name == obj.model_name))
                to_update = len(rec.line_ids.filtered(lambda x: x.model_name == obj.model_name and x.odoo_link_id))
                if rec.select_mode in ['create_update', 'update']:
                    message += str(to_update) + ' ' + obj.name + ' to Update\n'
                if rec.select_mode in ['create_update', 'create']:
                    message += str(total - to_update) + ' ' + obj.name + ' to Create\n'
            rec.message = message
