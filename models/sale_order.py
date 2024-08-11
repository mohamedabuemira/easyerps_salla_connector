from datetime import datetime
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from .ImageMixin import get_image_from_url
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


class SaleOrders(models.Model):
    _inherit = "sale.order"

    salla_id = fields.Integer()
    name = fields.Char()

    urls_customer = fields.Char()
    urls_admin = fields.Char()
    source = fields.Char()
    status = fields.Many2one('sale.order.status')
    payment_status = fields.Selection([('waiting', 'Waiting'),
                                       ('paid', 'Paid'), ], default='waiting')
    payment_method = fields.Many2one('account.payment.method')
    is_pending_payment = fields.Boolean()
    accepted_methods = fields.Many2many('account.payment.method', relation='salla_order_accepted_methods_rel',
                                        string='Accepted Methods')
    is_cod_available = fields.Boolean()
    pickup_branch = fields.Many2one('res.company.branch')
    shipment_branch = fields.Many2one('res.company.branch')
    tags = fields.Many2many('sale.order.tags', relation='salla_order_tags_rel', string='Tags')

    order_shipping_id = fields.Char()
    app_id = fields.Char()
    order_shipping_company = fields.Char()
    shipping_company_logo = fields.Binary()
    receiver_name = fields.Char()
    receiver_email = fields.Char()
    receiver_phone = fields.Char()
    shipper_name = fields.Char()
    shipper_company_name = fields.Char()
    shipper_email = fields.Char()
    shipper_phone = fields.Char()
    pickup_address_country = fields.Char()
    pickup_address_country_code = fields.Char()
    pickup_address_city = fields.Char()
    pickup_address_shipping_address = fields.Char()
    pickup_address_street_number = fields.Char()
    pickup_address_block = fields.Char()
    pickup_address_postal_code = fields.Char()
    address_country = fields.Char()
    address_country_code = fields.Char()
    address_city = fields.Char()
    address_shipping_address = fields.Char()
    address_street_number = fields.Char()
    address_block = fields.Char()
    address_postal_code = fields.Char()
    shipment_id = fields.Char()
    shipment_pickup_id = fields.Char()
    shipment_tracking_link = fields.Char()
    shipment_label_format = fields.Char()
    shipment_label_url = fields.Char()
    policy_options_boxes = fields.Char()

    shipments_id = fields.Char()
    shipments_created_at = fields.Char()
    shipments_type = fields.Char()
    shipments_courier_id = fields.Char()
    shipments_courier_name = fields.Char()
    shipments_courier_logo = fields.Binary()
    shipments_shipping_number = fields.Char('Shipment Number')
    shipments_tracking_number = fields.Char('Tracking Number')
    shipments_pickup_id = fields.Char()
    shipments_trackable = fields.Boolean()
    shipments_tracking_link = fields.Char('Tracking Link')
    shipments_label_format = fields.Char()
    shipments_label_url = fields.Char('Print Label')
    shipments_payment_method = fields.Char()
    shipments_source = fields.Char()
    shipments_total_amount = fields.Char()
    shipments_total_currency = fields.Char()
    shipments_cash_on_delivery_amount = fields.Char()
    shipments_cash_on_delivery_currency = fields.Char()
    shipments_ship_to_type = fields.Char()
    shipments_ship_to_name = fields.Char()
    shipments_ship_to_email = fields.Char()
    shipments_ship_to_phone = fields.Char()
    shipments_ship_to_country = fields.Char()
    shipments_ship_to_country_code = fields.Char()
    shipments_ship_to_city = fields.Char()
    shipments_ship_to_address_line = fields.Char()
    shipments_ship_to_street_number = fields.Char()
    shipments_ship_to_block = fields.Char()
    shipments_ship_to_postal_code = fields.Char()
    shipments_ship_from_type = fields.Char()
    shipments_ship_from_name = fields.Char()
    shipments_ship_from_company_name = fields.Char()
    shipments_ship_from_email = fields.Char()
    shipments_ship_from_phone = fields.Char()
    shipments_ship_from_country = fields.Char()
    shipments_ship_from_city = fields.Char()
    shipments_ship_from_address_line = fields.Char()
    shipments_ship_from_street_number = fields.Char()
    shipments_ship_from_block = fields.Char()
    shipments_ship_from_postal_code = fields.Char()
    shipments_ship_from_branch_id = fields.Many2one('res.company.branch')
    shipments_total_weight_value = fields.Char()
    shipments_total_weight_units = fields.Char()
    shipments_is_international = fields.Boolean()
    shipments_meta_app_id = fields.Char()
    shipments_meta_policy_options_boxes = fields.Char()
    is_policy = fields.Boolean(compute='_compute_is_policy')

    is_salla = fields.Boolean()
    is_salla_checker = fields.Boolean(compute='_compute_is_salla')

    @api.depends('salla_id')
    def _compute_is_salla(self):
        for rec in self:
            isfalse = False
            if rec.salla_id:
                isfalse = True
            rec.is_salla = isfalse
            rec.is_salla_checker = isfalse

    @api.depends('shipment_id')
    def _compute_is_policy(self):
        for rec in self:
            isfalse = False
            if rec.shipment_id != '0':
                isfalse = True
            rec.is_policy = isfalse

    def write_shipment(self, data):
        self.write(self._get_shipments_data(data))

    def action_return_shipment(self):
        message = 'Failed'
        response = self.env.company.odoo_2_x_crud('POST', 'shipments/' + str(self.shipment_id) + '/return')
        if response and response.get('success'):
            self.write(self._get_shipments_data(response.get('data')))
            message = 'Successed'
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

    def action_create_shipment(self):
        if self.salla_id:
            shippment_id = self.env['salla.shippment.update.wizard'].create({
                'order_id': self.id,
                'ship_to_customer': self.partner_id.id,

            })
            view = self.env.ref('easyerps_salla_connector.shippment_update_wizard_view_form')

            result = {
                'name': _("Status Update Wizard"),
                'view_mode': 'form',
                'view_id': view.id,
                'view_type': 'form',
                'res_model': 'salla.shippment.update.wizard',
                'res_id': shippment_id.id,
                'type': 'ir.actions.act_window',
                'target': 'new',
            }
            return result

    def action_update_status(self):
        if self.salla_id:
            status_update_id = self.env['salla.order.status.update.wizard'].create({'order_id': self.id})
            view = self.env.ref('easyerps_salla_connector.sale_status_update_wizard_view_form')

            result = {
                'name': _("Status Update Wizard"),
                'view_mode': 'form',
                'view_id': view.id,
                'view_type': 'form',
                'res_model': 'salla.order.status.update.wizard',
                'res_id': status_update_id.id,
                'type': 'ir.actions.act_window',
                'target': 'new',
            }
            return result

    def update_shipment(self):
        endpoint = 'orders/' + str(self.salla_id)
        company = self.env.context.get('company_id', False)
        company_id = self.env.company
        response = None
        if company:
            company_id = self.env['res.company'].browse(company)
        if company_id:
            response = company_id.odoo_2_x_crud('GET', endpoint, payload=None)
        if response and response.get('data'):
            data = response.get('data')
            result = {
                'app_id': data.get('shipping') and data.get('shipping').get('app_id') or '',
                'order_shipping_company': data.get('shipping') and data.get('shipping').get('company') or '',
                'shipping_company_logo': data.get('shipping') and data.get('shipping').get(
                    'logo') and get_image_from_url(
                    data.get('shipping').get('logo')) or None,
                'receiver_name': data.get('shipping') and data.get('shipping').get('receiver') and data.get(
                    'shipping').get(
                    'receiver').get('name') or '',
                'receiver_email': data.get('shipping') and data.get('shipping').get('receiver') and data.get(
                    'shipping').get('receiver').get('email') or '',
                'receiver_phone': data.get('shipping') and data.get('shipping').get('receiver') and data.get(
                    'shipping').get('receiver').get('phone') or '',
                'shipper_email': data.get('shipping') and data.get('shipping').get('receiver') and data.get(
                    'shipping').get(
                    'receiver').get('email') or '',
                'shipper_phone': data.get('shipping') and data.get('shipping').get('receiver') and data.get(
                    'shipping').get(
                    'receiver').get('phone') or '',
                'shipper_company_name': data.get('shipping') and data.get('shipping').get('receiver') and data.get(
                    'shipping').get('receiver').get('company_name') or '',
                'shipper_name': data.get('shipping') and data.get('shipping').get('shipper') and data.get(
                    'shipping').get(
                    'shipper').get('name') or '',
                'pickup_address_country': data.get('shipping') and data.get('shipping').get(
                    'pickup_address') and data.get(
                    'shipping').get('pickup_address').get('country') or '',
                'pickup_address_country_code': data.get('shipping') and data.get('shipping').get(
                    'pickup_address') and data.get('shipping').get('pickup_address').get('country_code') or '',
                'pickup_address_city': data.get('shipping') and data.get('shipping').get('pickup_address') and data.get(
                    'shipping').get('pickup_address').get('city') or '',
                'pickup_address_shipping_address': data.get('shipping') and data.get('shipping').get(
                    'pickup_address') and data.get('shipping').get('pickup_address').get('shipping_address') or '',
                'pickup_address_street_number': data.get('shipping') and data.get('shipping').get(
                    'pickup_address') and data.get('shipping').get('pickup_address').get('street_number') or '',
                'pickup_address_block': data.get('shipping') and data.get('shipping').get(
                    'pickup_address') and data.get(
                    'shipping').get('pickup_address').get('block') or '',
                'pickup_address_postal_code': data.get('shipping') and data.get('shipping').get(
                    'pickup_address') and data.get('shipping').get('pickup_address').get('postal_code') or '',
                'address_country': data.get('shipping') and data.get('shipping').get('address') and data.get(
                    'shipping').get('address').get('country') or '',
                'address_country_code': data.get('shipping') and data.get('shipping').get('address') and data.get(
                    'shipping').get('address').get('country_code') or '',
                'address_city': data.get('shipping') and data.get('shipping').get('address') and data.get(
                    'shipping').get(
                    'address').get('city') or '',
                'address_shipping_address': data.get('shipping') and data.get('shipping').get('address') and data.get(
                    'shipping').get('address').get('shipping_address') or '',
                'address_street_number': data.get('shipping') and data.get('shipping').get('address') and data.get(
                    'shipping').get('address').get('street_number') or '',
                'address_block': data.get('shipping') and data.get('shipping').get('address') and data.get(
                    'shipping').get(
                    'address').get('block') or '',
                'address_postal_code': data.get('shipping') and data.get('shipping').get('address') and data.get(
                    'shipping').get('address').get('postal_code') or '',
                'shipment_id': data.get('shipping') and data.get('shipping').get('shipment') and data.get(
                    'shipping').get(
                    'shipment').get('id') or '',
                'shipment_pickup_id': data.get('shipping') and data.get('shipping').get('shipment') and data.get(
                    'shipping').get('shipment').get('pickup_id') or '',
                'shipment_tracking_link': data.get('shipping') and data.get('shipping').get('shipment') and data.get(
                    'shipping').get('shipment').get('tracking_link') or '',
                'policy_options_boxes': data.get('shipping') and data.get('shipping').get(
                    'policy_options') and data.get(
                    'shipping').get('policy_options').get('boxes') or '',
            }
            self.with_context(from_salla=True).write(result)
            self.action_get_shipment()

    def action_get_shipment(self):
        if self.salla_id:
            response = self.env.company.odoo_2_x_crud('GET', 'orders/' + str(self.salla_id) + '/shipments')
            if response and response.get('data'):
                self.write(self._get_shipments_data(response.get('data')))

    def action_update_shipment(self):
        if self.salla_id:
            payload = {'shipment_number': self.shipments_shipping_number, 'shipment_type': self.shipments_type}
            response = self.env.company.odoo_2_x_crud(
                'PUT', 'orders/' + str(self.salla_id) + '/update-shipment', payload_json=payload)
            if response and response.get('data'):
                self.write(self._get_shipments_data(response.get('data')))

    def action_cancel_shipment(self):
        if self.salla_id:
            response = self.env.company.odoo_2_x_crud(
                'POST', 'orders/' + str(self.salla_id) + '/cancel-shipment',
                payload_json={'shipment_number': self.shipments_shipping_number, 'shipment_type': self.shipments_type})
            if response and response.get('success') == True:
                self.update_shipment()

    def action_open_tracking_link(self):
        return {
            'name': _("Tracking"),
            'type': 'ir.actions.act_url',
            'url': self.shipment_tracking_link,  # Replace this with tracking link
            'target': 'new',  # you can change target to current, self, new.. etc
        }

    def action_policy_printing(self):
        return {
            'name': _("Tracking"),
            'type': 'ir.actions.act_url',
            'url': 'https://s.salla.sa/orders/print_police/%s?summer=1&#print' % self.salla_id,  # Replace this with tracking link
            'target': 'new',  # you can change target to current, self, new.. etc
        }

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

    def _get_shipments_data(self, data):
        result = {}
        itme_1={}
        for itme in data:
            if not isinstance(itme, dict):
                for itme_1 in data[0]:
                    if not isinstance(itme_1, dict):
                        break
            if itme_1:
                itme = itme_1
            result.update(
                shipments_id=itme.get('id') or '',
                shipments_created_at=itme.get('created_at') or '',
                shipments_type=itme.get('type') or '',
                shipments_courier_id=itme.get('courier_id') or '',
                shipments_courier_name=itme.get('courier_name') or '',
                shipments_courier_logo=itme.get('courier_logo') and get_image_from_url(itme.get('courier_logo')) or '',
                shipments_shipping_number=itme.get('shipping_number') or '',
                shipments_pickup_id=itme.get('pickup_id') or '',
                shipments_trackable=itme.get('trackable') or '',
                shipments_tracking_link=itme.get('tracking_link') or '',
                shipments_label_format=itme.get('label') and itme.get('label').get('format') or '',
                shipments_label_url=itme.get('label') and itme.get('label').get('url') or '',
                shipments_payment_method=itme.get('payment_method') or '',
                shipments_source=itme.get('source') or '',
                shipments_total_amount=itme.get('total') and itme.get('total').get('amount') or '',
                shipments_total_currency=itme.get('total') and itme.get('total').get('currency') or '',
                shipments_cash_on_delivery_amount=itme.get('cash_on_delivery') and itme.get('cash_on_delivery').get(
                    'amount') or '',
                shipments_cash_on_delivery_currency=itme.get('cash_on_delivery') and itme.get('cash_on_delivery').get(
                    'currency') or '',
                shipments_ship_to_type=itme.get('ship_to') and itme.get('ship_to').get('type') or '',
                shipments_ship_to_name=itme.get('ship_to') and itme.get('ship_to').get('name') or '',
                shipments_ship_to_email=itme.get('ship_to') and itme.get('ship_to').get('email') or '',
                shipments_ship_to_phone=itme.get('ship_to') and itme.get('ship_to').get('phone') or '',
                shipments_ship_to_country=itme.get('ship_to') and itme.get('ship_to').get('country') or '',
                shipments_ship_to_country_code=itme.get('ship_to') and itme.get('ship_to').get('country_code') or '',
                shipments_ship_to_city=itme.get('ship_to') and itme.get('ship_to').get('city') or '',
                shipments_ship_to_address_line=itme.get('ship_to') and itme.get('ship_to').get('address_line') or '',
                shipments_ship_to_street_number=itme.get('ship_to') and itme.get('ship_to').get('street_number') or '',
                shipments_ship_to_block=itme.get('ship_to') and itme.get('ship_to').get('block') or '',
                shipments_ship_to_postal_code=itme.get('ship_to') and itme.get('ship_to').get('postal_code') or '',
                shipments_ship_from_type=itme.get('ship_from') and itme.get('ship_from').get('type') or '',
                shipments_ship_from_name=itme.get('ship_from') and itme.get('ship_from').get('name') or '',
                shipments_ship_from_company_name=itme.get('ship_from') and itme.get('ship_from').get(
                    'company_name') or '',
                shipments_ship_from_email=itme.get('ship_from') and itme.get('ship_from').get('email') or '',
                shipments_ship_from_phone=itme.get('ship_from') and itme.get('ship_from').get('phone') or '',
                shipments_ship_from_country=itme.get('ship_from') and itme.get('ship_from').get('country') or '',
                shipments_ship_from_city=itme.get('ship_from') and itme.get('ship_from').get('city') or '',
                shipments_ship_from_address_line=itme.get('ship_from') and itme.get('ship_from').get(
                    'address_line') or '',
                shipments_ship_from_street_number=itme.get('ship_from') and itme.get('ship_from').get(
                    'street_number') or '',
                shipments_ship_from_block=itme.get('ship_from') and itme.get('ship_from').get('block') or '',
                shipments_ship_from_postal_code=itme.get('ship_from') and itme.get('ship_from').get(
                    'postal_code') or '',
                shipments_total_weight_value=itme.get('total_weight') and itme.get('total_weight').get('value') or '',
                shipments_total_weight_units=itme.get('total_weight') and itme.get('total_weight').get('units') or '',
                shipments_is_international=itme.get('is_international') or '',
                shipments_meta_app_id=itme.get('meta') and itme.get('meta').get('app_id') or '',
                shipments_meta_policy_options_boxes=itme.get('meta') and itme.get('meta').get(
                    'policy_options') and itme.get('meta').get('policy_options').get('boxes') or ''

            )
            if itme.get('ship_from').get('branch_id'):
                bar_ids = itme.get('ship_from').get('branch_id')
                branch_ids = self.env['res.company.branch'].search([('salla_id', '=', bar_ids)], limit=1)
                if branch_ids:
                    # result.update(shipments_ship_from_branch_id=[(0, 0, branch_ids)])
                    result['shipments_ship_from_branch_id'] = branch_ids.id
        return result

    def to_unaware_date(self, curdate):
        if curdate:
            my_data = curdate.get('date')
            my_data = my_data.split('.')[0]
            return my_data
        return None

    @api.model
    def get_endpoint(self):
        return 'orders'

    def _prepare_dict_account_payment(self, invoice):

        return {
            "reconciled_invoice_ids": [(6, 0, invoice.ids)],
            "amount": invoice.amount_residual,
            "partner_id": invoice.partner_id.id,
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'journal_id': self.env.company.journal_id.id,
            'ref': invoice.payment_reference if invoice.payment_reference else invoice.name,
            "date": invoice.invoice_date,
        }

    def _register_payment_invoice(self, invoice):
        payment = self.env["account.payment"].create(
            self._prepare_dict_account_payment(invoice)
        )
        payment.action_post()

        domain = [
            ('account_type', 'in', ('asset_receivable', 'liability_payable')),
            ("reconciled", "=", False),
        ]
        payment_lines = payment.line_ids.filtered_domain(domain)
        lines = invoice.line_ids
        for account in payment_lines.account_id:
            (payment_lines + lines).filtered_domain(
                [("account_id", "=", account.id), ("reconciled", "=", False)]
            ).reconcile()
        return payment

    def status_checker(self, order_ref=False):
        order_id = self
        if order_ref:
            order_id = order_ref
        company_id = self.env.company
        for order in order_id:
            if order.salla_id and order.status:
                if company_id.status_to_confirm:
                    if order.status.salla_id == company_id.status_to_confirm.salla_id or order.status.parent_id.salla_id == company_id.status_to_confirm.salla_id:
                        order.action_confirm()
                if company_id.status_to_set_delivery_done:
                    if order.status.salla_id == company_id.status_to_set_delivery_done.salla_id or order.status.parent_id.salla_id == company_id.status_to_set_delivery_done.salla_id:
                        if order.state != 'sale':
                            order.action_confirm()
                        for picking in order.picking_ids:
                            if picking.state == 'cancel' or picking.state == 'done':
                                continue
                            picking.action_assign()
                            picking.action_confirm()
                            for mv in picking.move_ids_without_package:
                                mv.quantity_done = mv.product_uom_qty
                            picking.button_validate()
                if company_id.status_to_create_invoice:
                    if order.status.salla_id == company_id.status_to_create_invoice.salla_id or order.status.parent_id.salla_id == company_id.status_to_create_invoice.salla_id:
                        if order.state != 'sale':
                            order.action_confirm()
                        if not order.invoice_ids:
                            for line in order.mapped('order_line').filtered(
                                    lambda inv_line: inv_line.product_id.type == 'service'):
                                line.with_context(check_move_validity=False).qty_delivered = line.product_uom_qty
                            if order.invoice_status == 'to invoice':
                                order._create_invoices()
                        if company_id.validate_invoice:
                            if order.invoice_ids:
                                for invoice in order.invoice_ids:
                                    if invoice.state == "draft":
                                        invoice.action_post()
                        if company_id.atu_payment_register:
                            for invoice in order.invoice_ids:
                                self._register_payment_invoice(invoice)

    @api.model
    def x_2_odoo(self, data, mode='create'):
        company_id = self.env.company
        if mode == 'status_updated':
            record_id = self.search([('salla_id', '=', data.get('order').get('id'))], limit=1)
            if record_id:
                status = self.env['sale.order.status'].search(
                    [('salla_id', '=', data.get('customized').get('id'))], limit=1)
                if status:
                    record_id.status = status.id
                    self.status_checker()
            return
        if mode == 'refech':
            endpoint = 'orders/' + str(data.get('id'))
            self.odoo_2x_read(endpoint)
            return
        result = {
            'salla_id': data.get('id'),
            'name': str(data.get('reference_id')),
            'urls_customer': data.get('urls') and data.get('urls').get('customer') or '',
            'urls_admin': data.get('urls') and data.get('urls').get('admin') or '',
            'source': data.get('source'),
            'is_pending_payment': data.get('is_pending_payment'),
            'date_order': data.get('date') and self.to_unaware_date(data.get('date')) or None,
            'order_shipping_id': data.get('shipping') and data.get('shipping').get('id') or '',

        }
        if mode == 'abstract':
            if data.get('total') and data.get('total').get('amount'):
                result.update({'amount': data.get('total').get('amount')})
            return clean_nones(result)
        result_upt = {
            'app_id': data.get('shipping') and data.get('shipping').get('app_id') or '',
            'order_shipping_company': data.get('shipping') and data.get('shipping').get('company') or '',
            'shipping_company_logo': data.get('shipping') and data.get('shipping').get('logo') and get_image_from_url(
                data.get('shipping').get('logo')) or None,
            'receiver_name': data.get('shipping') and data.get('shipping').get('receiver') and data.get('shipping').get(
                'receiver').get('name') or '',
            'receiver_email': data.get('shipping') and data.get('shipping').get('receiver') and data.get(
                'shipping').get('receiver').get('email') or '',
            'receiver_phone': data.get('shipping') and data.get('shipping').get('receiver') and data.get(
                'shipping').get('receiver').get('phone') or '',
            'shipper_email': data.get('shipping') and data.get('shipping').get('receiver') and data.get('shipping').get(
                'receiver').get('email') or '',
            'shipper_phone': data.get('shipping') and data.get('shipping').get('receiver') and data.get('shipping').get(
                'receiver').get('phone') or '',
            'shipper_company_name': data.get('shipping') and data.get('shipping').get('receiver') and data.get(
                'shipping').get('receiver').get('company_name') or '',
            'shipper_name': data.get('shipping') and data.get('shipping').get('shipper') and data.get('shipping').get(
                'shipper').get('name') or '',
            'pickup_address_country': data.get('shipping') and data.get('shipping').get('pickup_address') and data.get(
                'shipping').get('pickup_address').get('country') or '',
            'pickup_address_country_code': data.get('shipping') and data.get('shipping').get(
                'pickup_address') and data.get('shipping').get('pickup_address').get('country_code') or '',
            'pickup_address_city': data.get('shipping') and data.get('shipping').get('pickup_address') and data.get(
                'shipping').get('pickup_address').get('city') or '',
            'pickup_address_shipping_address': data.get('shipping') and data.get('shipping').get(
                'pickup_address') and data.get('shipping').get('pickup_address').get('shipping_address') or '',
            'pickup_address_street_number': data.get('shipping') and data.get('shipping').get(
                'pickup_address') and data.get('shipping').get('pickup_address').get('street_number') or '',
            'pickup_address_block': data.get('shipping') and data.get('shipping').get('pickup_address') and data.get(
                'shipping').get('pickup_address').get('block') or '',
            'pickup_address_postal_code': data.get('shipping') and data.get('shipping').get(
                'pickup_address') and data.get('shipping').get('pickup_address').get('postal_code') or '',
            'address_country': data.get('shipping') and data.get('shipping').get('address') and data.get(
                'shipping').get('address').get('country') or '',
            'address_country_code': data.get('shipping') and data.get('shipping').get('address') and data.get(
                'shipping').get('address').get('country_code') or '',
            'address_city': data.get('shipping') and data.get('shipping').get('address') and data.get('shipping').get(
                'address').get('city') or '',
            'address_shipping_address': data.get('shipping') and data.get('shipping').get('address') and data.get(
                'shipping').get('address').get('shipping_address') or '',
            'address_street_number': data.get('shipping') and data.get('shipping').get('address') and data.get(
                'shipping').get('address').get('street_number') or '',
            'address_block': data.get('shipping') and data.get('shipping').get('address') and data.get('shipping').get(
                'address').get('block') or '',
            'address_postal_code': data.get('shipping') and data.get('shipping').get('address') and data.get(
                'shipping').get('address').get('postal_code') or '',
            'shipment_id': data.get('shipping') and data.get('shipping').get('shipment') and data.get('shipping').get(
                'shipment').get('id') or '',
            'shipment_pickup_id': data.get('shipping') and data.get('shipping').get('shipment') and data.get(
                'shipping').get('shipment').get('pickup_id') or '',
            'shipment_tracking_link': data.get('shipping') and data.get('shipping').get('shipment') and data.get(
                'shipping').get('shipment').get('tracking_link') or '',
            'policy_options_boxes': data.get('shipping') and data.get('shipping').get('policy_options') and data.get(
                'shipping').get('policy_options').get('boxes') or '',
        }
        result.update(result_upt)
        if data.get('is_pending_payment'):
            result['payment_status'] = data.get('payment_method')
        else:
            result['payment_status'] = 'paid'
            payment_id = self.env['account.payment.method'].search([('code', '=', data.get('payment_method'))], limit=1)
            result['payment_method'] = payment_id.id
        if data.get('pickup_branch'):
            result['is_cod_available'] = data.get('pickup_branch').get('is_cod_available') or False,
            bar_ids = data.get('pickup_branch').get('id')
            branch_ids = self.env['res.company.branch'].search([('salla_id', '=', bar_ids)], limit=1)
            if branch_ids:
                result['pickup_branch'] = branch_ids.id
            else:
                self.env['res.company.branch'].x_2_odoo(data.get('pickup_branch'))
                branch_ids = self.env['res.company.branch'].search([('salla_id', '=', bar_ids)], limit=1)
                if branch_ids:
                    result['pickup_branch'] = branch_ids.id
            if branch_ids and branch_ids.warehouse_id:
                result.update(warehouse_id=branch_ids.warehouse_id.id)
        if data.get('shipment_branch'):
            bar_ids = [x.get('id') for x in data.get('shipment_branch')]
            branch_ids = self.env['res.company.branch'].search([('salla_id', 'in', bar_ids)], limit=1)
            if branch_ids:
                result['shipment_branch'] = branch_ids.id
            else:
                for bar in data.get('shipment_branch'):
                    self.env['res.company.branch'].x_2_odoo(bar)
                branch_ids = self.env['res.company.branch'].search([('salla_id', 'in', bar_ids)], limit=1)
                if branch_ids:
                    result['shipment_branch'] = branch_ids.id
            if branch_ids and branch_ids.warehouse_id:
                result.update(warehouse_id=branch_ids.warehouse_id.id)
        if data.get('tags'):
            tag_ids = []
            for tag in data.get('tags'):
                tag_id = self.env['sale.order.tags'].search([('salla_id', '=', tag.get('id'))], limit=1)
                if tag_id:
                    tag_ids.append(tag_id.id)
            if tag_ids:
                result.update(tags=[(6, 0, tag_ids)])

        if data.get('shipments') and isinstance(data.get('shipments'), list):
            result.update(self._get_shipments_data(data.get('shipments')))

        if data.get('shipping') and data.get('shipping').get('shipment')  and data.get('shipping').get('shipment').get('label'):
            result['shipment_label_format'] = data.get('shipping').get('shipment').get('label').get('format')
            result['shipment_label_url'] = data.get('shipping').get('shipment').get('label').get('url')

        # if data.get('shipping') and data.get('shipping').get('policy_options'):
        #     for policy_options in data.get('shipping').get('policy_options'):
        #         result['policy_options_boxes'] = policy_options.get('boxes')

        partner_id = self.env['res.partner']
        if data.get('customer') and data.get('customer').get('id'):
            partner_id = self.env['res.partner'].search([('salla_id', '=', data.get('customer').get('id'))], limit=1)
            if not partner_id:
                partner = data.get('customer')
                partner_id = self.env['res.partner'].x_2_odoo(partner)
        result['partner_id'] = partner_id.id

        # status = self.env['sale.order.status']
        if data.get('status') and data.get('status').get('id'):
            if data.get('status').get('customized'):
                status = self.env['sale.order.status'].search(
                    [('salla_id', '=', data.get('status').get('customized').get('id'))], limit=1)
                if not status:
                    status = self.env['sale.order.status'].search(
                        [('original_id', '=', data.get('status').get('customized').get('id'))], limit=1)
            else:
                status = self.env['sale.order.status'].search(
                    [('salla_id', '=', data.get('status').get('id'))], limit=1)
                if not status:
                    status = self.env['sale.order.status'].search(
                        [('original_id', '=', data.get('status').get('id'))], limit=1)
            # if not status:
            #     result = {
            #         "id": data.get('status') and data.get('status').get('customized') and data.get('status').get('customized').get('id'),
            #     }
            #     status = self.env['sale.order.status'].x_2_odoo(result)
            if status:
                result['status'] = status.id

        order_line_data = []
        for item in data.get('items'):
            price_unit = 0
            discount = 0
            tax = None
            ok = False
            if item.get('amounts') and item.get('amounts').get('price_without_tax') and item.get('amounts').get(
                    'price_without_tax').get('amount'):
                price_unit = item.get('amounts').get('price_without_tax').get('amount')
            if item.get('amounts') and item.get('amounts').get('total_discount') and item.get('amounts').get(
                    'total_discount').get('amount'):
                discount = item.get('amounts').get('total_discount').get('amount')
            if item.get('amounts') and item.get('amounts').get('tax') and item.get('amounts').get('tax').get('percent'):
                tax = item.get('amounts').get('tax').get('percent')
            line_data = {'name': item.get('name'),
                         'product_uom_qty': item.get('quantity'),
                         'price_unit': price_unit,
                         'discount': discount,
                         }
            if item.get('id'):
                line_data.update({'salla_id': item.get('id')})
            if price_unit:
                line_data.update(price_unit=price_unit)
            if discount:
                line_data.update(discount=discount)
            if tax:
                tax_id = self.env['account.tax'].search(
                    [('amount', '=', tax),
                     ('amount_type', '=', 'percent'),
                     ('type_tax_use', '=', 'sale')],
                    limit=1)
                if tax_id:
                    line_data.update(tax_id=[(6, 0, tax_id.ids)])
            if item.get('product'):
                product_id = self.env['product.product']
                if item.get('product').get('id'):
                    product_id = self.env['product.product'].search(
                        [('tmpl_salla_id', '=', item.get('product').get('id'))], limit=1)
                if not product_id:
                    product_id = self.env['product.product'].x_2_odoo(item.get('product'))
                if product_id:
                    line_data.update(product_id=product_id.id)
                ok = True
            if item.get('options'):
                option_name = []
                for option in item.get('options'):
                    name = option.get('name') + '- '
                    if option.get('type') in ['radio', 'checkbox'] and option.get('value'):
                        name += option.get('value').get('name')
                    else:
                        if isinstance(option.get('value'), str):
                            name += option.get('value')
                    option_name.append(name)
                line_data.update(name=','.join(option_name))
            if ok:
                order_line_data.append(line_data)
        if data.get('amounts') and data.get('amounts').get('shipping_cost'):
            if data.get('amounts').get('shipping_cost').get('amount') > 0 and company_id.shipping_cost_product_id:
                shipping_cost_amount = data.get('amounts').get('shipping_cost').get('amount')
                values = {
                    'name': _("Shipping Cost"),
                    'product_uom_qty': 1,
                    'product_uom': company_id.shipping_cost_product_id.uom_id.id,
                    'product_id': company_id.shipping_cost_product_id.id,
                    'is_delivery': True,
                    'price_unit': shipping_cost_amount,
                }
                order_line_data.append(values)
        if data.get('amounts') and data.get('amounts').get('cash_on_delivery'):
            if data.get('amounts').get('cash_on_delivery').get('amount') > 0 and company_id.cod_cost_product_id:
                cod_cost_amount = data.get('amounts').get('cash_on_delivery').get('amount')
                values = {
                    'name': _("Cash on Delivery Cost"),
                    'product_uom_qty': 1,
                    'product_uom': company_id.cod_cost_product_id.uom_id.id,
                    'product_id': company_id.cod_cost_product_id.id,
                    'is_delivery': True,
                    'price_unit': cod_cost_amount,
                }
                order_line_data.append(values)

        record_id = self.search([('salla_id', '=', result.get('salla_id'))], limit=1)

        if mode in ['create', 'update']:
            lines = []
            for line in order_line_data:
                lines.append((0, 0, line))
            if len(lines) > 0:
                result['order_line'] = lines
            if record_id:
                if record_id.state == 'draft' or record_id.state == 'sent':
                    if record_id.order_line:
                        for line in record_id.order_line:
                            line.with_context(from_salla=True).unlink()
                else:
                    result['order_line'] = []
                record_id.with_context(from_salla=True).write(result)
            else:
                self.with_context(from_salla=True).create(result)

            self.status_checker(record_id)
        elif mode == 'delete':
            if record_id:
                record_id.with_context(from_salla=True).unlink()

    def odoo_2_x(self):
        geocode = None
        if (self.partner_shipping_id.partner_latitude and self.partner_shipping_id.partner_longitude):
            geocode = str(self.partner_shipping_id.partner_latitude) + ',' + str(
                self.partner_shipping_id.partner_longitude)
        result = {
            "customer_id": self.partner_invoice_id.salla_id,
            "shipping_address": {
                'branch_id': self.shipment_branch.salla_id,
            },
            "payment": {
                'status': self.payment_status ,
                'method':self.payment_method.code if self.payment_status == 'paid' else None,
            },
            "products": [
                {
                    'id': x.product_id.tmpl_salla_id,
                    'quantity': x.product_uom_qty,
                    'name': x.name,
                    'price': x.price_unit
                }
                for x in self.order_line
            ]
        }
        if self.payment_status == 'waiting':
            methods =[]
            for rec in self.accepted_methods:
                methods.append(rec.code)
            if methods:
                result['payment']['accepted_methods'] = methods

        pop_out = []
        for key in result:
            if not result[key]:
                pop_out.append(key)
        for keyout in pop_out:
            result.pop(keyout)
        pop_out = []
        for shipkey in result['shipping_address']:
            if not result['shipping_address'][shipkey]:
                pop_out.append(shipkey)
        for keyout in pop_out:
            result['shipping_address'].pop(keyout)
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
            response = company_id.odoo_2_x_crud('POST', 'orders', payload_json=record)
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
            response = company_id.odoo_2_x_crud('GET', 'orders', payload=None)
        if response and response.get('data'):
            for rec in response.get('data'):
                self.x_2_odoo(rec, mode='refech')

    def odoo_2x_read(self, endpoint):
        company = self.env.context.get('company_id', False)
        company_id = self.env.company
        response = None
        if company:
            company_id = self.env['res.company'].browse(company)
        if company_id:
            response = company_id.odoo_2_x_crud('GET', endpoint, payload=None)
        if response and response.get('data'):
            self.x_2_odoo(response.get('data'))

    def odoo_2x_update(self, endpoint=None):
        if not endpoint:
            endpoint = 'orders/' + str(self.salla_id)
        record = self.odoo_2_x()
        company = self.env.context.get('company_id', False)
        company_id = self.env.company
        response = None
        if company:
            company_id = self.env['res.company'].browse(company)
        if company_id and self.salla_id:
            response = company_id.odoo_2_x_crud('GET', endpoint, payload_json=record)
        return response

    def odoo_2x_delete(self):
        company = self.env.context.get('company_id', False)
        company_id = self.env.company
        response = None
        if company:
            company_id = self.env['res.company'].browse(company)
        if company_id and self.salla_id:
            response = company_id.odoo_2_x_crud('DELETE', 'orders/' + str(self.salla_id), payload=None)
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


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    salla_id = fields.Integer()
