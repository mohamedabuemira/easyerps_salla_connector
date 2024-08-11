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


class SallaWebhooks(models.Model):
    _name = "salla.webhooks"
    _description = "Salla Webhooks"

    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    is_active = fields.Boolean('Activated')
    notification = fields.Boolean()
    rule = fields.Char("Rule")
    name = fields.Char()
    event = fields.Many2one('salla.webhook.event.list')
    webhook_url = fields.Char()
    salla_id = fields.Integer()

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
        return 'webhooks'

    @api.model
    def x_2_odoo(self, data, mode='create'):
        result = {
            'salla_id': data.get('id'),
            'name': data.get('name'),
            'webhook_url': data.get('url'),
            'is_active': True,
        }
        if data.get('event'):
            event_id = data.get('event')
            event = self.env['salla.webhook.event.list'].search([('event', '=', event_id)], limit=1)
            if event:
                result['event'] = event.id
        if mode == 'abstract':
            return clean_nones(result)
        record_id = self.search([('salla_id', '=', result.get('salla_id'))], limit=1)

        if mode in ['create', 'update']:
            if record_id:
                record_id.with_context(from_salla=True).write(result)
            else:
                self.with_context(from_salla=True).create(result)
        elif mode == 'delete':
            if record_id:
                record_id.with_context(from_salla=True).unlink()

    def action_subscribe_webhooks(self):
        message = 'Failed'
        company_id = self.env.company
        headers = {
            "Authorization": "Bearer " + company_id.request_salla_token(),
            "Content-Type": "application/json"
        }
        endpoint_url = company_id.salla_base_url+"/webhooks/subscribe"
        payload = {
            "name": self.name,
            "event": self.event.event,
            "url": self.webhook_url or company_id.salla_webhook,
            "headers": [
                {
                    'key': 'authorization',
                    'value': company_id.easyerps_api_key
                }
            ]
        }
        if self.rule:
            payload["rule"] = self.rule
        response = company_id._do_request('POST', endpoint_url, None, headers, payload_json=payload)
        response_data = response.json()
        if response_data and response_data.get('data'):
            self.salla_id = response_data.get('data').get('id')
            self.webhook_url = response_data.get('data').get('url')
            message = 'Success'
            self.write({'is_active': True})
        result_id = self.env['result.dialog'].create({'name': message})
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

    def action_deactivate_webhooks(self):
        message = 'Failed'
        company_id = self.env.company
        headers = {
            "Authorization": "Bearer " + company_id.request_salla_token(),
            "Content-Type": "application/json"
        }
        endpoint_url = company_id.salla_base_url+"/webhooks/unsubscribe"
        payload = {
            "id": self.salla_id,
        }
        response = company_id._do_request('DELETE', endpoint_url, None, headers, payload_json=payload)
        response_data = response.json()
        if response_data and response_data.get('success'):
            message = response_data.get('data')
            self.write({'is_active': False})
        result_id = self.env['result.dialog'].create({'name': message})
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

    def process(self, payload, headers):
        model = None
        mode = 'create'
        if self.event.event in ["store.branch.updated", "store.branch.setDefault", "store.branch.activated"]:
            model = 'res.company.branch'
        elif self.event.event == "store.branch.deleted":
            model = 'res.company.branch'
            mode = 'delete'
        elif self.event.event == "storetax.created":
            pass
        elif self.event.event == "coupon.applied":
            pass
        elif self.event.event in ["shipping.zone.created", "shipping.zone.updated"]:
            pass
        elif self.event.event in ["shipping.company.created", "shipping.company.updated"]:
            pass
        elif self.event.event == "shipping.company.deleted":
            pass
        elif self.event.event in ["brand.created", "brand.updated"]:
            model = 'product.brand'
        elif self.event.event == "brand.deleted":
            model = 'product.brand'
            mode = 'delete'
        elif self.event.event == "category.created":
            model = 'product.category'
        elif self.event.event == "category.updated":
            model = 'product.category'
        elif self.event.event == "specialoffer.created":
            pass
        elif self.event.event == "specialoffer.updated":
            pass
        elif self.event.event == "product.created":
            model = 'product.product'
        elif self.event.event == "product.updated":
            model = 'product.product'
        elif self.event.event == "product.deleted":
            model = 'product.product'
            mode = 'delete'
        elif self.event.event == "product.available":
            pass
        elif self.event.event == "product.quantity.low":
            pass
        elif self.event.event == "review.added":
            pass
        elif self.event.event == "customer.created":
            model = 'res.partner'
        elif self.event.event == "customer.updated":
            model = 'res.partner'
        elif self.event.event == "customer.login":
            pass
        elif self.event.event == "customer.otp.request":
            pass
        elif self.event.event == "order.created":
            model = 'sale.order'
        elif self.event.event == "order.updated":
            model = 'sale.order'
        elif self.event.event == "order.status.updated":
            mode = 'status_updated'
            model = 'sale.order'
        elif self.event.event == "order.cancelled":
            model = 'sale.order'
        elif self.event.event == "order.refunded":
            model = 'sale.order'
        elif self.event.event == "order.deleted":
            model = 'sale.order'
            mode = 'delete'
        elif self.event.event == "order.products.updated":
            pass
        elif self.event.event == "order.payment.updated":
            pass
        elif self.event.event == "order.coupon.updated":
            pass
        elif self.event.event == "order.total.price.updated":
            pass
        elif self.event.event == "order.shipment.creating":
            pass
        elif self.event.event == "order.shipment.created":
            pass
        elif self.event.event == "order.shipment.cancelled":
            pass
        elif self.event.event == "order.shipment.return.creating":
            pass
        elif self.event.event == "order.shipment.return.created":
            pass
        elif self.event.event == "order.shipment.return.cancelled":
            pass
        elif self.event.event == "order.shipping.address.updated":
            pass
        elif self.event.event == "abandoned.cart":
            pass
        else:
            pass
        if self.notification:
            notifications = [['broadcast','salla_webhook',{'name':payload.get('event')}]]
            if notifications:
                self.env["bus.bus"]._sendmany(notifications)
        if model:
            self.env[model].with_context(from_salla=True).x_2_odoo(payload.get('data'), mode)


class WebhookEventList(models.Model):
    _name = "salla.webhook.event.list"
    _description = "Salla Webhook Event List"
    name = fields.Char()
    event = fields.Char()
    salla_id = fields.Char()

    @api.model
    def get_endpoint(self):
        return 'events'

    @api.model
    def x_2_odoo(self, data, mode='create'):
        result = {
            'name': data.get('label'),
            'event': data.get('event'),
            'salla_id': data.get('id'),
        }
        if mode == 'abstract':
            return clean_nones(result)

        record_id = self.search([('event', '=', result.get('event'))], limit=1)
        if mode in ['create', 'update']:
            if not record_id:
                self.with_context(from_salla=True).create(result)
        elif mode == 'delete':
            if record_id:
                record_id.with_context(from_salla=True).unlink()

    @api.model
    def odoo_2x_read_all(self):
        company = self.env.context.get('company_id', False)
        company_id = self.env.company
        response = None
        if company:
            company_id = self.env['res.company'].browse(company)
        if company_id:
            response = company_id.odoo_2_x_crud(
                'GET', 'webhooks/events', payload=None)
            if response and response.get('data'):
                for rec in response.get('data'):
                    self.x_2_odoo(rec)


class EventList(models.Model):
    _name = "salla.event.list"
    _description = "Salla Event List"
    name = fields.Char()
    model_name = fields.Char()
    description = fields.Char()


# class WebhookCompanyEvent(models.Model):
#     _name = "salla.webhook.event"
#     _description = "Salla Webhook Event"
#
#     company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
#     name = fields.Char(required=True)
#     event_id = fields.Many2one('salla.event.list', required=True)
#     model_name = fields.Char(related="event_id.model_name")
#     is_active = fields.Boolean('Activated', default=True)
#     notification=fields.Boolean()
#     rule = fields.Char("Rule")
#     salla_id = fields.Integer()

