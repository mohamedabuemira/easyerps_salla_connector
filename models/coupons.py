from odoo import models, fields, api, _


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


class paymentlist(models.Model):
    _name = 'payment.method.list'
    _description = 'payment.method.list'

    name = fields.Selection(
        [
            ('all', 'ALL'),
            ('apple_pay', 'APPLE'),
            ('bank', 'BANK'),
            ('cod', 'COD'),
            ('credit_card', 'CREDIT CARD'),
            ('knet', 'KNET'),
            ('mada', 'MADA'),
            ('paypal', 'PAYPAL'),
            ('spotii_pay', 'SPOTII PAY'),
            ('stc_pay', 'STC PAY'),
            ('tabby_installment', 'TABBY INSTALLMENT'),
            ('tamara_installment', 'TAMARA INSTALLMENT')
        ])


class SallaCouponGroups(models.Model):
    _name = 'salla.coupon.groups'
    _description = 'coupon groups'
    name = fields.Char()


class Coupon(models.Model):
    _name = 'salla.coupon'
    _description = 'Salla coupon'

    salla_id = fields.Integer()
    code = fields.Char()
    type = fields.Selection([('percentage', 'Percentage'),
                            ('fixed', 'Fixed')
                             ], default='percentage')
    amount = fields.Float()
    status = fields.Selection([('active', 'Active'), ('inactive', 'Inactive')], default='active')
    start_date = fields.Datetime(default=fields.Datetime().now)
    expiry_date = fields.Datetime()
    applied_in = fields.Selection([('app', 'APP'), ('web', 'WEB'), ('all', 'ALL')], default='all')
    is_group = fields.Boolean()
    group_name = fields.Char()
    group_coupons_count = fields.Integer()
    group_coupons = fields.Many2many('salla.coupon.groups', relation='coup_gr_coup_salla_rel', string="Coupon Groups")
    group_suffix = fields.Char()
    usage_limit = fields.Integer()
    usage_limit_per_user = fields.Integer()
    minimum_amount = fields.Float()
    maximum_amount = fields.Float()
    show_maximum_amount = fields.Boolean()

    free_shipping = fields.Boolean()
    exclude_sale_products = fields.Boolean()

    marketing_active = fields.Boolean()
    marketing_name = fields.Char()
    marketing_type = fields.Selection([('percentage', 'Percentage'),
                                       ('fixed', 'Fixed')
                                       ], default='percentage')
    marketing_amount = fields.Float()
    marketing_hide_total_sales = fields.Boolean()
    marketing_maximum_amount = fields.Float()
    marketing_show_maximum_amount = fields.Boolean()
    marketing_info = fields.Char()
    beneficiary_domain = fields.Char()
    products_include = fields.Many2many(
        'product.product', relation="product_include_coupon_salla_rel", string="Products Include")
    products_exclude = fields.Many2many(
        'product.product', relation="product_exclude_coupon_salla_rel", string="Products Exclude")
    list_include_categories = fields.Many2many('product.category',
                                               relation="included_coupon_product_category_salla_rel",
                                               string="Included Categories")
    list_exclude_categories = fields.Many2many('product.category',
                                               relation="excluded_coupon_product_category_salla_rel",
                                               string="Excluded Categories")
    list_exclude_brands = fields.Many2many(
        'product.brand', relation="excluded_coupon_product_brand_salla_rel", string="Excluded Brands")
    list_include_brands = fields.Many2many(
        'product.brand', relation="included_coupon_product_brand_salla_rel", string="Included Brands")
    list_exclude_groups = fields.Many2many(
        'customer.groups', relation="excluded_coupon_customer_groups_salla_rel", string="Excluded Groups")
    list_include_groups = fields.Many2many(
        'customer.groups', relation="included_coupon_customer_groups_salla_rel", string="List of Included Customer Groups")
    include_payment_methods = fields.Many2many('payment.method.list', relation='include_payment_methods_rel',
                                       string='Payment Methods')
    statistics_num_of_usage = fields.Char()
    statistics_num_of_customers = fields.Char()
    statistics_coupon_sales_amount = fields.Char()

    marketing_visits_count = fields.Char()
    marketing_url = fields.Char()
    marketing_statistics_url = fields.Char()
    # payment_methods = fields.Many2many('payment.method.list', relation='salla_include_payment_methods_rel', string='Payment Methods')

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
        return 'coupons'

    @api.model
    def x_2_odoo(self, data, mode='create'):
        result = {
            'salla_id': data.get('id'),
            'code': data.get('code'),
            'type': data.get('type'),
            'status': data.get('status'),
        }
        if mode == 'abstract':
            return clean_nones(result)
        result_upt = {
            'amount': data.get('amount') and data.get('amount').get('amount'),
            'minimum_amount': data.get('minimum_amount') and data.get('minimum_amount').get('amount'),
            'maximum_amount': data.get('maximum_amount') and data.get('maximum_amount').get('amount'),
            'show_maximum_amount': data.get('show_maximum_amount'),
            'start_date': data.get('start_date'),
            'expiry_date': data.get('start_date'),
            'free_shipping': data.get('free_shipping'),
            'usage_limit': data.get('usage_limit'),
            'usage_limit_per_user': data.get('usage_limit_per_user'),
            'applied_in': data.get('applied_in'),
            'is_group': data.get('is_group'),
            'group_name': data.get('group_name'),
            'group_coupons_count': data.get('group_coupons_count'),
            'group_suffix': data.get('group_coupon_suffix'),
            'exclude_sale_products': data.get('is_sale_products_exclude'),
            'marketing_active': data.get('marketing_active'),
            'marketing_name': data.get('marketing_name'),
            'marketing_type': data.get('marketing_type'),
            'marketing_amount': data.get('marketing_amount') and data.get('marketing_amount').get('amount'),
            'marketing_hide_total_sales': data.get('marketing_hide_total_sales'),
            'marketing_maximum_amount': data.get('marketing_maximum_amount') and data.get('marketing_maximum_amount').get('amount'),
            'marketing_show_maximum_amount': data.get('marketing_show_maximum_amount'),
            'marketing_info': data.get('marketing_info'),
            'beneficiary_domain': data.get('beneficiary_domain'),
            'statistics_num_of_usage': data.get('statistics') and data.get('statistics').get('num_of_usage'),
            'statistics_num_of_customers': data.get('statistics') and data.get('statistics').get('num_of_customers'),
            'statistics_coupon_sales_amount': data.get('statistics') and data.get('statistics').get('coupon_sales')
                                                and data.get('statistics').get('coupon_sales').get('amount'),
            'marketing_visits_count': data.get('marketing_visits_count'),
            'marketing_url': data.get('marketing_visits_count'),
            'marketing_statistics_url': data.get('marketing_visits_count'),

        }
        result.update(result_upt)
        if data.get('include_product_ids'):
            product_ids = []
            for prod_id in data.get('include_product_ids'):
                product_id = self.env['product.product'].search([('tmpl_salla_id', '=', int(prod_id))], limit=1)
                if product_id:
                    product_ids.append(product_id.id)
            if product_ids:
                result.update(products_include=[(6, 0, product_ids)])
        if data.get('exclude_product_ids'):
            product_ids = []
            for prod_id in data.get('exclude_product_ids'):
                product_id = self.env['product.product'].search([('tmpl_salla_id', '=', int(prod_id))], limit=1)
                if product_id:
                    product_ids.append(product_id.id)
            if product_ids:
                result.update(products_exclude=[(6, 0, product_ids)])

        if data.get('include_category_ids'):
            category_ids = []
            for prod_id in data.get('include_category_ids'):
                category_id = self.env['product.category'].search([('salla_id', '=', int(prod_id))], limit=1)
                if category_id:
                    category_ids.append(category_id.id)
            if category_ids:
                result.update(list_include_categories=[(6, 0, category_ids)])
        if data.get('exclude_category_ids'):
            category_ids = []
            for prod_id in data.get('exclude_category_ids'):
                category_id = self.env['product.category'].search([('salla_id', '=', int(prod_id))], limit=1)
                if category_id:
                    category_ids.append(category_id.id)
            if category_ids:
                result.update(list_exclude_categories=[(6, 0, category_ids)])
        if data.get('include_brands_ids'):
            brand_ids = []
            for prod_id in data.get('include_brand_ids'):
                brand_id = self.env['product.brand'].search([('salla_id', '=', int(prod_id))], limit=1)
                if brand_id:
                    brand_ids.append(brand_id.id)
            if brand_ids:
                result.update(list_include_brands=[(6, 0, brand_ids)])
        if data.get('exclude_brands_ids'):
            brand_ids = []
            for prod_id in data.get('exclude_brand_ids'):
                brand_id = self.env['product.brand'].search([('salla_id', '=', int(prod_id))], limit=1)
                if brand_id:
                    brand_ids.append(brand_id.id)
            if brand_ids:
                result.update(list_exclude_brands=[(6, 0, brand_ids)])

        if data.get('include_customer_group_ids'):
            customer_group_ids = []
            for prod_id in data.get('include_customer_group_ids'):
                customer_group_id = self.env['customer.groups'].search([('salla_id', '=', int(prod_id))], limit=1)
                if customer_group_id:
                    customer_group_ids.append(customer_group_id.id)
            if customer_group_ids:
                result.update(list_include_groups=[(6, 0, customer_group_ids)])
        if data.get('exclude_customer_group_ids'):
            customer_group_ids = []
            for prod_id in data.get('exclude_customer_group_ids'):
                customer_group_id = self.env['customer.groups'].search([('salla_id', '=', int(prod_id))], limit=1)
                if customer_group_id:
                    customer_group_ids.append(customer_group_id.id)
            if customer_group_ids:
                result.update(list_exclude_groups=[(6, 0, customer_group_ids)])
        if data.get('include_payment_methods'):
            pay_meths = []
            for pay in data.get('include_payment_methods'):
                pay_id = self.env['payment.method.list'].search([('name', '=', pay)], limit=1)
                if pay_id:
                    pay_meths.append(pay_id.id)
            if pay_meths:
                result.update(include_payment_methods=[(6, 0, pay_meths)])
        if data.get('group_coupons'):
            coupons = []
            for coupon in data.get('group_coupons'):
                coupon_id = self.env['salla.coupon.groups'].search([('name', '=', coupon.get('code'))], limit=1)
                if not coupon_id:
                    coupon_id = self.env['salla.coupon.groups'].create({'name': coupon.get('code')})
                coupons.append(coupon_id.id)
            if coupons:
                result.update(group_coupons=[(6, 0, coupons)])

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
            'type': self.type,
            'amount': self.amount,
            'status': self.status,
            'start_date': fields.Datetime.to_string(self.start_date),
            'expiry_date': fields.Datetime.to_string(self.expiry_date),
            'applied_in': self.applied_in,
            'is_group': self.is_group,
            'usage_limit': self.usage_limit,
            'usage_limit_per_user': self.usage_limit_per_user,
            'minimum_amount ': self.minimum_amount,
            'free_shipping': self.free_shipping,
            'exclude_sale_products': self.exclude_sale_products,
            'marketing_active': self.marketing_active,
        }
        if self.type == 'percentage' :
            result.update({
                'maximum_amount': self.maximum_amount,
                'show_maximum_amount': self.show_maximum_amount,
            })
        if self.products_include :
            result.update({
                'products_include': [str(x.tmpl_salla_id) for x in self.products_include],
            })
        if self.products_exclude :
            result.update({
                'products_exclude': [str(x.tmpl_salla_id) for x in self.products_exclude],
            })
        if self.list_include_categories :
            result.update({
                'list_include_categories': [str(x.salla_id) for x in self.list_include_categories],
            })
        if self.list_exclude_categories :
            result.update({
                'list_exclude_categories': [str(x.salla_id) for x in self.list_exclude_categories],
            })
        if self.list_exclude_brands :
            result.update({
                'list_exclude_brands': [str(x.salla_id) for x in self.list_exclude_brands],
            })
        if self.list_exclude_groups :
            result.update({
                'list_exclude_groups': [str(x.salla_id) for x in self.list_exclude_groups],
            })
        if self.list_include_groups :
            result.update({
                'list_include_groups': [str(x.salla_id) for x in self.list_include_groups],
            })
        if self.include_payment_methods :
            result.update({
                'payment_methods': [str(x.name) for x in self.include_payment_methods],
            })
        if self.beneficiary_domain :
            result.update({
                'beneficiary_domain': self.beneficiary_domain,
            })
        if self.is_group :
            result.update({
                'group_name': self.group_name,
                'group_coupons_count': self.group_coupons_count,
                'group_suffix': self.group_suffix,
            })
        else:
            result.update({
                    'code': self.code,})

        if self.marketing_active :
            result.update({
                'marketing_name': self.marketing_name,
                'marketing_type': self.marketing_type,
                'marketing_amount': self.marketing_amount,
                'marketing_hide_total_sales': self.marketing_hide_total_sales,
                'marketing_info': self.marketing_info,
            })
            if self.marketing_type == 'percentage':
                result.update({
                    'marketing_maximum_amount': self.marketing_maximum_amount,
                    'marketing_show_maximum_amount': self.marketing_show_maximum_amount,
                })
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
            response = company_id.odoo_2_x_crud('POST', 'coupons', payload_json=record)
        if response and response.get('data'):
            self.with_context(from_salla=True).write(
                {'salla_id': response.get('data').get('id'),
                 'statistics_num_of_usage': response.get('data').get('statistics') and response.get('data').get('statistics').get('num_of_usage'),
                 'statistics_num_of_customers': response.get('data').get('statistics') and response.get('data').get('statistics').get(
                     'num_of_customers'),
                 'statistics_coupon_sales_amount': response.get('data').get('statistics') and response.get('data').get('statistics').get('coupon_sales')
                                                   and response.get('data').get('statistics').get('coupon_sales').get('amount'),
                 'marketing_visits_count': response.get('data').get('marketing_visits_count'),
                 'marketing_url': response.get('data').get('marketing_visits_count'),
                 'marketing_statistics_url': response.get('data').get('marketing_visits_count'),
                 })
            if self.is_group:
                if response.get('data').get('group_coupons'):
                    coupons = []
                    for coupon in response.get('data').get('group_coupons'):
                        coupon_id = self.env['salla.coupon.groups'].search([('name', '=', coupon.get('code'))], limit=1)
                        if not coupon_id:
                            coupon_id = self.env['salla.coupon.groups'].create({'name': coupon.get('code')})
                        coupons.append(coupon_id.id)
                    if coupons:
                        self.with_context(from_salla=True).write({'group_coupons': [(6, 0, coupons)]})

    @api.model
    def odoo_2x_read_all(self):
        company = self.env.context.get('company_id', False)
        company_id = self.env.company
        response = None
        if company:
            company_id = self.env['res.company'].browse(company)
        if company_id:
            response = company_id.odoo_2_x_crud('GET', 'coupons', payload=None)
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
            response = company_id.odoo_2_x_crud('GET', 'coupons/' + str(self.salla_id), payload=None)
        if response and response.get('data'):
            self.x_2_odoo(response.get('data'))

    def odoo_2x_update(self, endpoint=None):
        if not endpoint:
            endpoint = 'coupons/' + str(self.salla_id)
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
                response = company_id.odoo_2_x_crud('DELETE', 'coupons/' + str(rec.salla_id), payload=None)
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
