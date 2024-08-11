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
    ('sale.order', 'ORDERS'),
    ('all', 'ALL')
]


class SallaDashboad(models.Model):
    _name = 'salla.dashboard'
    _description = 'Salla Dashboard'
    _rec_name = 'model_name'
    company_id = fields.Many2one('res.company')

    model_name = fields.Selection(OBJECT_LIST, required=True)
    #current_fetch_sync_id = fields.Many2one('salla.sync', ondelete='cascade')

    def action_pull(self):
        active_ids = None
        object_ids = self.env['auto.syncer.objects']
        if self.model_name != 'all':
            active_ids = self.env[self.model_name].search([])
        else:
            object_ids = self.env['auto.syncer.objects'].search([])

        self.env['salla.pull.filter.wizard'].search([('user_id', '=', self.env.user.id)]).unlink()
        pull_id = self.env['salla.pull.filter.wizard'].create({'current_model': self.model_name})
        to_update = {}
        if object_ids:
            to_update.update({'object_ids': [(6, 0, object_ids.ids)]})
        pullset = []
        if active_ids:
            for activ in active_ids:
                pullset.append((0, 0, {'odoo_link_id': '% s,% s' % (self.model_name, activ.id)}))
        if pullset:
            to_update.update({'line_ids': pullset})
        if to_update:
            pull_id.write(to_update)
        view = self.env.ref('easyerps_salla_connector.view_pull_salla_filter_wizard')
        if self.model_name == 'all':
            view = self.env.ref('easyerps_salla_connector.view_pull_all_salla_filter_wizard')
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
        if object_ids:
            result.update(context={'default_object_ids': [6, 0, object_ids.ids]})
        return result

    def action_fetch(self):
        sync_ids = self.env['salla.sync'].search([('user_id', '=', self.env.user.id)])
        if sync_ids:
            self.env['salla.fetch.filter.wizard'].search([('current_sync_id', 'in', sync_ids.ids)]).unlink()
            sync_ids.unlink()
        temp_salla_sync_line = self.env['salla.sync.line'].search([])
        if temp_salla_sync_line:
            temp_salla_sync_line.unlink()

        object_ids = self.env['auto.syncer.objects']
        if self.model_name == 'all':
            object_ids = self.env['auto.syncer.objects'].search([])

        current_fetch_sync_id = self.env['salla.sync'].create({'current_model': self.model_name})
        fetch_id = self.env['salla.fetch.filter.wizard'].create({'current_sync_id': current_fetch_sync_id.id})
        if object_ids:
            fetch_id.write({'object_ids': [(6, 0, object_ids.ids)]})
        view = self.env.ref('easyerps_salla_connector.view_fetch_filter_wizard')

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
