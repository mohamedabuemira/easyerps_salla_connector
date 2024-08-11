from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from .ImageMixin import get_image_from_url


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


class SallaOffers(models.Model):
    _name = 'salla.offers'
    _description = 'Salla Offers'

    salla_id = fields.Integer()
    name = fields.Char()
    applied_channel = fields.Selection([('browser', 'Browser'),
                                   ('browser_and_application', 'Browser and Application'),], default='browser_and_application')
    applied_to = fields.Selection([('product', 'Product'),
                                   ('order', 'Order'),
                                   ('category', 'Category'),
                                   ('paymentMethod', 'Payment Method')], default='order')
    offer_type = fields.Selection([('buy_x_get_y', 'Buy x get y'),
                                   ('percentage', 'Percentage'),
                                   ('fixed_amount', 'Fixed Amount')], default='buy_x_get_y')
    message = fields.Char()
    status = fields.Selection([('inactive', 'Inactive'), ('active', 'Active')], default='inactive')
    show_discounts_table_message = fields.Boolean()
    show_price_after_discount = fields.Boolean()
    expiry_date = fields.Datetime()
    start_date = fields.Datetime(default=fields.Datetime().now)
    minimum_application = fields.Selection([('purchase_amount', 'Purchase Amount'), ('items_count', 'Items Count')], default='purchase_amount')
    min_purchase_amount = fields.Float()
    min_items_count = fields.Integer()
    buy_type = fields.Selection([('product', 'Product'), ('category', 'Category')], default='product')
    buy_min_amount = fields.Float()
    buy_quantity = fields.Integer()
    buy_products = fields.Many2many('product.product', relation='buy_offers_prod_tepml_rel', string='Buy Products')
    buy_categories = fields.Many2many(
        'product.category', relation='buy_offers_product_category_rel', string='Buy Categories')
    buy_payment_methods = fields.Many2many(
        'account.payment.method', relation='offers_payment_method_rel', string='Payment methods')
    get_type = fields.Selection([('product', 'Product'), ('category', 'Category')], default='product')
    get_discount_type = fields.Selection(
        [('free-product', 'Free Product'),
         ('percentage', 'Percentage')],
        default='percentage')
    get_discount_amount = fields.Float()
    get_quantity = fields.Integer()
    get_products = fields.Many2many('product.product', relation='get_offers_prod_tepml_rel', string='Get Products')
    get_categories = fields.Many2many(
        'product.category', relation='get_offers_product_category_rel', string='Get Categories')

    @api.onchange('offer_type')
    def _onchange_offer_type(self):
        if self.offer_type == 'buy_x_get_y':
            self.applied_to = 'order'

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
            my_data = curdate.split('.')[0]
            return my_data
        return None

    @api.model
    def get_endpoint(self):
        return 'specialoffers'

    @api.model
    def x_2_odoo(self, data, mode='create'):
        result = {
            'salla_id': data.get('id'),
            'name': data.get('name'),
            'applied_channel': data.get('applied_channel') or "browser_and_application",
            'offer_type': data.get('offer_type'),
            'applied_to': data.get('applied_to'),
            'message': data.get('message'),
            'status': data.get('status')
        }
        if mode == 'abstract':
            return clean_nones(result)
        result_upt = {
            'start_date': data.get('start_date') or None,
            'expiry_date': data.get('expiry_date'),
            'show_price_after_discount': data.get('show_price_after_discount'),
            'show_discounts_table_message': data.get('show_discounts_table_message'),
            'buy_type': data.get('buy') and data.get('buy').get('type') or None,
            'buy_quantity': data.get('buy') and data.get('buy').get('quantity') or 1,
            'get_type': data.get('get') and data.get('get').get('type') or None,
            'get_discount_type': data.get('get') and data.get('get').get('discount_type') or None,
            'get_quantity': data.get('get') and data.get('get').get('quantity') or 1,
            'min_purchase_amount':data.get('buy') and data.get('buy').get('min_amount') or 0,
            'min_items_count': data.get('buy') and data.get('buy').get('min_items') or 0,
        }
        result.update(result_upt)

        if data.get('buy'):
            if data.get('buy').get('products'):
                products = []
                for prod_id in data.get('buy').get('products'):
                    product_id = self.env['product.product'].search([('tmpl_salla_id', '=', prod_id.get('id'))], limit=1)
                    if product_id:
                        products.append(product_id.id)
                if products:
                    result.update(buy_products=products)
            if data.get('buy').get('categories'):
                categories = []
                for categ_id in data.get('buy').get('categories'):
                    category_id = self.env['product.category'].search([('salla_id', '=', categ_id.get('id'))], limit=1)
                    if category_id:
                        categories.append(category_id.id)
                if categories:
                    result.update(buy_categories=categories)

        if data.get('get'):
            if data.get('get').get('products'):
                products = []
                for prod_id in data.get('get').get('products'):
                    product_id = self.env['product.product'].search([('tmpl_salla_id', '=', prod_id.get('id'))], limit=1)
                    if product_id:
                        products.append(product_id.id)
                if products:
                    result.update(get_products=products)
            if data.get('get').get('categories'):
                categories = []
                for categ_id in data.get('get').get('categories'):
                    category_id = self.env['product.category'].search([('salla_id', '=', categ_id.get('id'))], limit=1)
                    if category_id:
                        categories.append(category_id.id)
                if categories:
                    result.update(get_categories=categories)

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
            'name': self.name,
            'applied_channel': self.applied_channel,
            'applied_to': self.applied_to,
            'offer_type': self.offer_type,
            'start_date': fields.Datetime.to_string(self.start_date),
            'expiry_date': fields.Datetime.to_string(self.expiry_date),
        }
        if self.offer_type == 'buy_x_get_y':
            result.update({
                'applied_to': self.buy_type,
                'buy': {
                    'type': self.buy_type,
                    'quantity': self.buy_quantity,
                },
                'get': {
                    'type': self.get_type,
                    'discount_type': self.get_discount_type,
                    'quantity': self.get_quantity,
                }
            })
            if self.buy_type == 'product':
                result.get('buy').update({'products': [x.tmpl_salla_id for x in self.buy_products ]})
            else:
                result.get('buy').update({'categories': [x.salla_id for x in self.buy_categories]})

            if self.get_type == 'product':
                result.get('get').update({'products': [x.tmpl_salla_id for x in self.get_products ]})
            else:
                result.get('get').update({'categories': [x.salla_id for x in self.get_categories]})
            if self.get_discount_type == 'percentage':
                result.get('get').update({'discount_amount': self.get_discount_amount })
        else:
            result.update({
                'buy': {
                },
                'get': {
                    'discount_amount': self.get_discount_amount,
                }
            })
            if self.applied_to == 'product':
                result.get('buy').update({'products': [x.tmpl_salla_id for x in self.buy_products ]})
            if self.applied_to == 'category':
                result.get('buy').update({'categories': [x.salla_id for x in self.buy_categories]})
            if self.applied_to == 'paymentMethod':
                result.get('buy').update({'payment_methods': [x.salla_id for x in self.buy_payment_methods]})
            if self.minimum_application == 'purchase_amount':
                result.get('buy').update({'min_amount': self.min_purchase_amount})
            else:
                result.get('buy').update({'min_items': self.min_items_count})

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
            response = company_id.odoo_2_x_crud('POST', 'specialoffers', payload_json=record)
        if response and response.get('data'):
            self.with_context(from_salla=True).write({
                'salla_id': response.get('data').get('id'),
                'message': response.get('data').get('message')
            })

    def action_change_status(self):
        message = 'Failed'
        company_id = self.env.company
        headers = {
            "Authorization": "Bearer " + company_id.request_salla_token(),
            "Content-Type": "application/json"
        }
        endpoint_url = 'https://api.salla.dev/admin/v2/specialoffers/'+str(self.salla_id)+'/status'
        if self.status == 'active':
            payload = {
                "status": "inactive"
            }
        else:
            payload = {
                "status": "active"
            }
        response = company_id._do_request('PUT', endpoint_url, None, headers, payload_json=payload)
        response_data = response.json()
        if response_data and response_data.get('data'):
            message = response_data.get('data').get('message')
            if self.status == 'active':
                self.write({'status': 'inactive'})
            else:
                self.write({'status': 'active'})
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

    @ api.model
    def odoo_2x_read_all(self):
        company = self.env.context.get('company_id', False)
        company_id = self.env.company
        response = None
        if company:
            company_id = self.env['res.company'].browse(company)
        if company_id:
            response = company_id.odoo_2_x_crud('GET', 'specialoffers', payload=None)
        if response and response.get('data'):
            for rec in response.get('data'):
                self.x_2_odoo(rec)

    def odoo_2x_read(self):
        company = self.env.context.get('company_id', False)
        company_id = self.env.company
        response = None
        if company:
            company_id = self.env['res.company'].browse(company)
        if company_id:
            response = company_id.odoo_2_x_crud('GET', 'specialoffers/' + str(self.salla_id), payload=None)
        if response and response.get('data'):
            self.x_2_odoo(response.get('data'))

    def odoo_2x_update(self, endpoint=None):
        if not endpoint:
            endpoint = 'specialoffers/' + str(self.salla_id)
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
                response = company_id.odoo_2_x_crud('DELETE', 'specialoffers/' + str(rec.salla_id), payload=None)
        return response

    @ api.model
    def create(self, vals):
        result = super().create(vals)
        company_id = self.env.company
        if not self.env.context.get('from_salla', False) and company_id.is_salla_shop:
            try:
                if self.env.company.check_sync(self._name):
                    result.odoo_2x_create()
            except Exception as error:
                raise ValidationError(error)
        return result

    def write(self, vals):
        result = super().write(vals)
        company_id = self.env.company
        if not self.env.context.get('from_salla', False) and company_id.is_salla_shop:
            try:
                if self.env.company.check_sync(self._name) :
                    self.odoo_2x_update()
            except Exception as error:
                raise ValidationError(error)
        return result

    def unlink(self):
        company_id = self.env.company
        if not self.env.context.get('from_salla', False) and company_id.is_salla_shop:
            try:
                if self.env.company.check_sync(self._name) :
                    self.odoo_2x_delete()
            except Exception as error:
                raise ValidationError(error)
        return super().unlink()
