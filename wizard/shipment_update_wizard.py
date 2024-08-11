from odoo import models, fields, api, _


class StatusUpdater(models.TransientModel):
    _name = 'salla.shippment.update.wizard'
    _description = 'Shipment updater'

    order_id = fields.Many2one('sale.order')

    courier_id = fields.Many2one('shipping.company')
    shipment_type = fields.Selection([('shipment', 'Shipment')],default="shipment")
    overwrite_exists_pending = fields.Boolean(default=True)
    policy_options_boxes = fields.Integer()
    payment_method_id = fields.Selection([('cod', 'Cod'),('pre_paid', 'Pre Paid')],default="cod")
    cash_on_delivery_amount = fields.Integer()
    cash_on_delivery_currency = fields.Char()
    ship_to_customer = fields.Many2one('res.partner',domain="[('salla_id', '>', 0)]")
    ship_to_name = fields.Char()
    ship_to_email = fields.Char()
    ship_to_phone = fields.Char()
    ship_to_country = fields.Many2one('res.country')
    ship_to_city = fields.Many2one('res.city')
    ship_to_address_line = fields.Char(string="address",compute="_compute_ship_to_address")
    ship_to_street_number = fields.Char()
    ship_to_block = fields.Char()
    ship_to_postal_code = fields.Char()

    @api.onchange("ship_to_customer")
    def _onchange_ship_to_customer(self):
        if self.ship_to_customer:
            for rec in self:
                rec.ship_to_name = rec.ship_to_customer.name
                rec.ship_to_email = rec.ship_to_customer.email
                rec.ship_to_phone = rec.ship_to_customer.phone
                rec.ship_to_country = rec.ship_to_customer.country_id
                rec.ship_to_city = rec.ship_to_customer.city_id
                rec.ship_to_street_number = rec.ship_to_customer.street
                rec.ship_to_postal_code = rec.ship_to_customer.zip

    @api.depends("ship_to_country",'ship_to_city','ship_to_street_number','ship_to_postal_code' ,'ship_to_block')
    def _compute_ship_to_address(self):
        if self.ship_to_customer:
            for rec in self:
                country = rec.ship_to_country.name if rec.ship_to_country else ""
                city = rec.ship_to_city.name if rec.ship_to_city else ""
                zip = rec.ship_to_postal_code if rec.ship_to_postal_code else ""
                block = rec.ship_to_block if rec.ship_to_block else ""
                street =rec.ship_to_street_number if rec.ship_to_street_number else ""
                rec.ship_to_address_line = country+','+city+','+zip+','+block+','+street

    @api.onchange("ship_to_country")
    def _onchange_ship_to_country(self):
        if self.ship_to_country and not self.ship_to_customer.city_id:
            for rec in self:
                rec.ship_to_city = False
                company = self.env.context.get('company_id', False)
                company_id = self.env.company
                response = None
                if company:
                    company_id = self.env['res.company'].browse(company)
                if company_id:
                    country_id = rec.ship_to_country
                    if country_id.salla_id and country_id.salla_id > 0 and not country_id.city_processed:
                        self.env['res.city'].odoo_2x_read_per_country(country_id)


    ship_from_type = fields.Char()
    ship_from_name = fields.Char()
    ship_from_company_name = fields.Char()
    ship_from_email = fields.Char()
    ship_from_phone = fields.Char()
    ship_from_country = fields.Many2one('res.country')
    ship_from_city = fields.Many2one('res.city')
    ship_from_address_line = fields.Char()
    ship_from_street_number = fields.Char()
    ship_from_block = fields.Char()
    ship_from_postal_code = fields.Char()
    ship_from_branch_id = fields.Many2one('res.company.branch')

    def action_update(self):
        endpoint = 'shipments'
        payload = {
            'order_id': self.order_id,
            'courier_id': self.courier_id,
            'shipment_type': self.shipment_type,
            'overwrite_exists_pending =': self.overwrite_exists_pending,
            'policy_options': {'boxes': self.policy_options_boxes},
            'payment_method': self.payment_method_id.name,
            'cash_on_delivery': {
                'amount': self.cash_on_delivery_amount,
                'currency': self.cash_on_delivery_currency
            },
            'ship_to': {
                'name': self.ship_to_name,
                'email': self.ship_to_email,
                'phone': self.ship_to_phone,
                'country_id': self.ship_to_country and self.ship_to_country.salla_id or None,
                'city_id': self.ship_to_city and self.ship_to_city.salla_id or None,
                'address_line': self.ship_to_address_line,
                'street_number': self.ship_to_street_number,
                'block': self.ship_to_block,
                'postal_code': self.ship_to_postal_code,
            },
            'ship_from': {
                'type': self.ship_from_type,
                'name': self.ship_from_name,
                'email': self.ship_from_email,
                'phone': self.ship_from_phone,
                'country_id': self.ship_from_country and self.ship_from_country.salla_id or None,
                'city_id': self.ship_from_city and self.ship_from_city.salla_id or None,
                'address_line': self.ship_from_address_line,
                'street_number': self.ship_from_street_number,
                'block': self.ship_from_block,
                'postal_code': self.ship_from_postal_code,
                'branch_id': self.ship_from_branch_id and self.ship_from_branch_id.salla_id or None
            },
            'packages': [
                {
                    'name': line.name,
                    'sku': line.product_id.default_code,
                    'price': {
                        'amount': line.price_unit,
                        'currency': self.env.company.currency_id.code,
                    },
                    'quantity': line.product_uom_qty,
                    'weight': {
                        'value': line.product_id.salla_weight,
                        'unit': line.product_id.salla_weight_type
                    }
                }
                for line in self.order_id.order_line
            ]
        }
        response = self.env.company.odoo_2_x_crud('POST', endpoint, payload_json=payload)
        if response and response.get('success') == True:
            message = 'Create Successfull'
            result_id = self.env['result.dialog'].create({'name': message})
            self.order_id.write_shipment(response.get('data'))
        else:
            result_id = self.env['result.dialog'].create({'name': 'Update Failed'})
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
