from odoo import models, fields, api, _

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
    ('sale.order', 'ORDERS')
]


class PullFilterSallaLine(models.TransientModel):
    _name = 'salla.pull.filter.line'
    _description = 'Pull filter line'

    sync_id = fields.Many2one('salla.pull.filter.wizard')
    select = fields.Boolean()
    odoo_link_id = fields.Reference(OBJECT_LIST, required=True)
    is_synced = fields.Boolean(compute='compute_is_synced', store=True)

    @api.depends('odoo_link_id')
    def compute_is_synced(self):
        for rec in self:
            synced = False
            if hasattr(rec.odoo_link_id, 'salla_id'):
                if rec.odoo_link_id.salla_id:
                    synced = True
            elif hasattr(rec.odoo_link_id, 'tmpl_salla_id'):
                if rec.odoo_link_id.tmpl_salla_id:
                    synced = True
            rec.is_synced = synced


class PullFilterSalla(models.TransientModel):
    _name = 'salla.pull.filter.wizard'
    _description = 'Salla pull Filter Wizard'

    user_id = fields.Many2one('res.users', default=lambda self: self.env.user)
    current_model = fields.Char()
    line_ids = fields.One2many('salla.pull.filter.line', 'sync_id', ondelete='cascade')
    total_records_count = fields.Integer('Total Records', compute='_compute_counts')
    synced_records_count = fields.Integer('Synced Records', compute='_compute_counts')
    to_update_records_count = fields.Integer('To Update', compute='_compute_counts')
    to_create_records_count = fields.Integer('To Create', compute='_compute_counts')
    object_ids = fields.Many2many('auto.syncer.objects', relation='salla_pull_autosynce_rel', string='Objects')
    endpoint_field_id = fields.Many2one('salla.endpoint.fields')

    value = fields.Char()
    message = fields.Text(compute='_compute_message')
    select_mode = fields.Selection([('create_update', 'Create and Update'),
                                    ('create', 'Create'),
                                   ('update', 'Update')], default='create_update')
    select_all = fields.Boolean(default=True)

    @api.onchange('select_all', 'select_mode')
    def _onchange_select_all(self):
        records = self.line_ids
        out_records = self.env['salla.pull.filter.line']
        if self.select_mode == 'update':
            records = records.filtered(lambda x: x.is_synced)
            self.line_ids.filtered(lambda x: not x.is_synced).write({'select': False})

        if self.select_all:
            records.write({'select': True})
        else:
            records.write({'select': False})

    @api.depends('object_ids', 'select_mode')
    def _compute_message(self):
        for rec in self:
            message = ''
            for obj in rec.object_ids:
                total = 0
                to_update = 0
                records = self.env[obj.model_name]
                if hasattr(records, 'salla_id'):
                    total = len(records.search([]))

                    to_update = len(records.search([('salla_id', '>', 0)]))
                elif hasattr(records, 'tmpl_salla_id'):
                    total = len(records.search([]))
                    to_update = len(records.search([('tmpl_salla_id', '>', 0)]))
                message += str(to_update) + ' ' + obj.name + ' to Update\n'
                if rec.select_mode in ['create_update', 'create']:
                    message += str(total - to_update) + ' ' + obj.name + ' to Create\n'
            self.message = message

    @api.depends('line_ids', 'line_ids.select', 'select_mode')
    def _compute_counts(self):
        for rec in self:
            total = 0
            to_update = 0
            to_create = 0
            synced = 0
            if rec.line_ids:
                total = len(rec.line_ids)
                to_update = len(rec.line_ids.filtered(lambda x: x.select and x.is_synced))
                if rec.select_mode in ['create_update', 'create']:
                    to_create = len(rec.line_ids.filtered(lambda x: x.select and not x.is_synced))
                synced = len(rec.line_ids.filtered(lambda x: x.is_synced))
            rec.total_records_count = total
            rec.to_update_records_count = to_update
            rec.to_create_records_count = to_create
            rec.synced_records_count = synced

    def action_pull_selected(self):
        if self.current_model != 'all':
            recset = self.line_ids.filtered(lambda x: x.select)
            if self.select_mode == 'update':
                recset = self.line_ids.filtered(lambda x: x.select and x.is_synced)
            elif self.select_mode == 'create':
                recset = self.line_ids.filtered(lambda x: x.select and not x.is_synced)
            for rec in recset:
                to_update = False
                to_create = False
                if hasattr(rec.odoo_link_id, 'salla_id') and rec.odoo_link_id.salla_id:
                    to_update = True
                elif hasattr(rec.odoo_link_id, 'tmpl_salla_id') and rec.odoo_link_id.tmpl_salla_id:
                    to_update = True
                else:
                    to_create = True
                if hasattr(rec.odoo_link_id, 'odoo_2x_create'):
                    if to_create == True and self.select_mode in ['create_update', 'create']:
                        rec.odoo_link_id.odoo_2x_create()
                if hasattr(rec.odoo_link_id, 'odoo_2x_update') and to_update:
                    rec.odoo_link_id.odoo_2x_update()
        elif self.object_ids:
            for obj in self.object_ids:
                records = self.env[obj.model_name]
                if self.select_mode == 'update':
                    if hasattr(records, 'odoo_2x_update'):
                        if hasattr(records, 'salla_id'):
                            records = self.env[obj.model_name].search([('salla_id', '>', 0)])
                        elif hasattr(records, 'tmpl_salla_id'):
                            records = self.env[obj.model_name].search([('tmpl_salla_id', '>', 0)])
                        for rec in records:
                            records.odoo_2x_update()
                elif self.select_mode == 'create':
                    if hasattr(records, 'odoo_2x_create'):
                        records = self.env[obj.model_name]
                        if hasattr(records, 'salla_id'):
                            records = self.env[obj.model_name].search([('salla_id', '=', False)])
                        elif hasattr(records, 'tmpl_salla_id'):
                            records = self.env[obj.model_name].search([('tmpl_salla_id', '=', False)])
                        for rec in records:
                            records.odoo_2x_create()
                elif self.select_mode == 'create_update':
                    if hasattr(records, 'odoo_2x_update'):
                        records = self.env[obj.model_name]
                        if hasattr(records, 'salla_id'):
                            records = self.env[obj.model_name].search([('salla_id', '>', 0)])
                        elif hasattr(records, 'tmpl_salla_id'):
                            records = self.env[obj.model_name].search([('tmpl_salla_id', '>', 0)])
                        for rec in records:
                            records.odoo_2x_update()
                    records = self.env[obj.model_name]
                    if hasattr(records, 'odoo_2x_create'):
                        records = self.env[obj.model_name]
                        if hasattr(records, 'salla_id'):
                            records = self.env[obj.model_name].search([('salla_id', '=', False)])
                        elif hasattr(records, 'tmpl_salla_id'):
                            records = self.env[obj.model_name].search([('tmpl_salla_id', '=', False)])
                        for rec in records:
                            records.odoo_2x_create()

            models_list = self.object_ids.mappeds('model_name')
            self.env.company.sync_all_to_salla(models_list)

        result_id = self.env['result.dialog'].create({'name': 'Pull Successfull'})
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

    def minimal_pull(self):
        endpoint = self.env[self.current_model].get_endpoint() + '/'
        if self.endpoint_field_id.name == 'ID' and self.value:
            endpoint += self.value
        elif self.value:
            endpoint += str(self.endpoint_field_id.name) + '/' + self.value
        if self.value:
            self.line_ids[0].odoo_link_id.odoo_2x_update(endpoint=endpoint)
        else:
            self.line_ids[0].odoo_link_id.odoo_2x_create()

        result_id = self.env['result.dialog'].create({'name': 'Pull Successfull'})
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
