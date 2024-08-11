import base64
import io
from odoo import models, fields, api, _,tools
from .ImageMixin import get_image_from_url
from odoo.exceptions import ValidationError, UserError
from odoo.tools.mimetypes import guess_mimetype
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


def shrinkdict(a, b):
    out_dict = {}
    for key, value in a.items():
        if key in b:
            out_dict[key] = value
    return out_dict


class ConsistedProduct(models.Model):
    _name = 'consisted.product'
    _description = 'Consisted Product'

    product_id = fields.Many2one('product.product')
    quantity = fields.Integer()


class ProductTemplate(models.Model):
    _inherit = 'product.product'

    tmpl_salla_id = fields.Integer()
    product_type = fields.Selection(
        [
            ('product', 'Product'),
            ('service', 'Service'),
            ('group_products', 'Group products'),
            ('codes', 'Codes'),
            ('digital', 'Digital'),
            ('food', 'Food'),
            ('donating', 'Donating')], default='product'
    )
    salla_status = fields.Selection(
        [('sale', 'SALE'),
         ('out', 'OUT'),
         ('hidden', 'HIDDEN'),
         ('deleted', 'DELETED')],
        string='Status')
    brand_id = fields.Many2one('product.brand')
    salla_gtin = fields.Char('GTIN')
    salla_mpn = fields.Char('MPN')
    salla_hide_quantity = fields.Boolean('Hide Quantity')
    salla_enable_upload_image = fields.Boolean('Enable Upload Image')
    salla_enable_note = fields.Boolean('Enable Note')
    salla_pinned = fields.Boolean('Pinned')
    salla_active_advance = fields.Boolean('Active Advance')
    salla_subtitle = fields.Char('Subtitle')
    salla_promotion_title = fields.Char('Promotion Title')
    salla_promotion_subtitle = fields.Char('Promotion Subtitle')
    salla_metadata_title = fields.Char('Metagada Title')
    salla_metadata_description = fields.Text('Metadata Description')
    is_salla_product = fields.Boolean()
    is_salla_checker = fields.Boolean(compute='_compute_is_salla')
    calories = fields.Char()
    tags = fields.Many2many('product.tags', relation='product_product_tags_rel', string='Tags')
    consisted_products_ids = fields.Many2many(
        'consisted.product', relation='product_consisted_product_rel', string="Consisted PRoducts")
    salla_sale_price = fields.Float('Sale Price')
    description_sale = fields.Text()
    sale_end_date = fields.Datetime()
    require_shipping = fields.Boolean()
    salla_weight = fields.Float()
    salla_weight_type = fields.Selection([('kg', 'KG'), ('g', 'G'), ('lb', 'Lb'), ('oz', 'oz')],
        default='kg')
    url_admin = fields.Char()
    url_customer = fields.Char()
    with_tax = fields.Boolean()
    show_in_app = fields.Boolean()
    managed_by_branches = fields.Boolean()
    max_items_per_user = fields.Integer()
    maximum_quantity_per_order = fields.Integer()
    options_ids = fields.One2many('product.options', 'product_id')
    salla_main_image_id = fields.Char()
    salla_main_image_url = fields.Char()

    @api.onchange("image_1920")
    def _onchange_salla_image_1920(self):
        self.salla_main_image_url=''

    def get_image_file(self, name):
        imgtext = ".png"
        image = ''
        mimetype=''
        image_data = None
        image = self.image_1920
        if image:
            image_base64 = base64.b64decode(image)
            image_data = io.BytesIO(image_base64)
            mimetype = guess_mimetype(image_base64, default='image/png')
            imgext = '.' + mimetype.split('/')[1]
            if imgext == '.svg+xml':
                imgext = '.svg'
        return {'image_data': image_data, 'image_name': imgtext,'mimetype':mimetype}

    @api.depends('tmpl_salla_id')
    def _compute_is_salla(self):
        for rec in self:
            isfalse = False
            if rec.tmpl_salla_id:
                isfalse = True
            rec.is_salla_product = isfalse
            rec.is_salla_checker = isfalse

    def action_attach_digital_code(self):
        pass

    def action_attach_digital_file(self):
        pass

    def action_delete_digital_file(self):
        pass

    def action_create_options(self):
        message = 'Nothing to create, this product is not synced yet'
        if self.tmpl_salla_id:
            count = 0
            options = self.options_ids.filtered(lambda x:not x.salla_id)
            for option in options:
                payload = {
                    "name": option.name,
                    "display_type": option.display_type,
                    "values": [
                        {
                            "name": value.name,
                            "price": value.price,
                            "quantity": value.quantity,
                            "display_value": value.display_value and value.display_value or value.name
                        }
                        for value in option.value_ids
                    ]
                }
                response = self.env.company.odoo_2_x_crud(
                    'POST', 'products/' + str(self.tmpl_salla_id) + '/options', payload_json=payload)
                if response and response.get('success') == True:
                    option.salla_id = response.get('data').get('id')
                    count += 1
            if count > 0:
                message = f'{count} records created successfuly'

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

    def action_update_options(self):
        message = 'Nothing to update, this product is not synced yet'
        if self.tmpl_salla_id:
            message = 'Nothing to update, this product does not have previous options'
            options = self.options_ids.filtered(lambda x: x.salla_id)
            count = 0
            for option in options:
                payload = {
                    "name": option.name,
                    "display_type": option.display_type,
                    "values": [
                        {
                            "name": value.name,
                            "price": value.price,
                            "quantity": value.quantity,
                            "display_value": value.display_value and value.display_value or value.name
                        }
                        for value in option.value_ids
                    ]
                }
                response = self.env.company.odoo_2_x_crud(
                    'PUT', 'products/options/' + str(option.salla_id), payload_json=payload)
                if response and response.get('success') == True:
                    count += 1
            if count > 0:
                message = f'{count} records updated successfuly'

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

    def action_fecht_by_sku(self):
        if not self.default_code:
            raise UserError(_('This product does not have a SKU/Internal Reference. Please Update'))
        self.odoo_2x_read("products/sku/" + str(self.default_code))

    def action_fecht_by_id(self):
        if not self.tmpl_salla_id:
            raise UserError(_('This product does not have a salla ID Please insert before'))
        self.odoo_2x_read("products/" + str(self.tmpl_salla_id))

    def action_fetch(self):
        sync_ids = self.env['salla.sync'].search([('user_id', '=', self.env.user.id)])
        if sync_ids:
            self.env['salla.fetch.filter.wizard'].search([('current_sync_id', 'in', sync_ids.ids)]).unlink()
            sync_ids.unlink()

        temp_salla_sync_line = self.env['salla.sync.line'].search([])
        if temp_salla_sync_line:
            temp_salla_sync_line.unlink()

        if self.tmpl_salla_id > 0:
            current_fetch_sync_id = self.env['salla.sync'].create({'current_model': self._name,
                                                                   'current_record_id': '% s,% s' % (self._name, self.id)})
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
            if self.tmpl_salla_id:
                fetch_id.write(
                    {'value': str(self.tmpl_salla_id),
                     'endpoint_field_id': self.env.ref('easyerps_salla_connector.salla_endpoint_product_id_filter')
                     }
                )
        else:
            current_fetch_sync_id = self.env['salla.sync'].create({'current_model': self._name,
                                                                   'current_record_id': '% s,% s' % (
                                                                   self._name, self.id)})
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

        if self.tmpl_salla_id:
            pull_id.write(
                {
                    'value': str(self.tmpl_salla_id),
                    'endpoint_field_id': self.env.ref('easyerps_salla_connector.salla_endpoint_product_id_filter')
                }
            )
        return result

    @api.model
    def get_endpoint(self):
        return 'products'

    @api.model
    def x_2_odoo(self, data, mode='create', fieldslist=None):
        result = {
            'name': data.get('name'),
            # 'price': data.get('regular_price') and data.get('regular_price').get('amount') or 0.0,
            'salla_status': data.get('status'),
            'product_type': data.get('type')
        }

        if mode == 'abstract':
            return clean_nones(result)

        result_update = {
            'detailed_type': 'product',
            'list_price': data.get('regular_price') and data.get('regular_price').get('amount') or 0.0,
            'salla_sale_price': data.get('sale_price') and data.get('sale_price').get('amount') or 0.0,
            'standard_price': data.get('cost_price') and float(data.get('cost_price')) or 0.0,
            'default_code': data.get('sku'),
            'salla_gtin': data.get('gtin'),
            'salla_mpn': data.get('mpn'),
            'salla_hide_quantity': data.get('hide_quantity'),
            'salla_enable_upload_image': data.get('enable_upload_image'),
            'salla_pinned': data.get('pinned'),
            'salla_active_advance': data.get('active_advance'),
            'image_1920': data.get('main_image') and get_image_from_url(data.get('main_image')) or None,
            'salla_main_image_url': data.get('main_image') or None,
            'tmpl_salla_id': data.get('id'),
            'description': data.get('description'),
            'description_sale': data.get('description'),
            'sale_end_date': data.get('sale_end_date'),
            'require_shipping': data.get('require_shipping'),
            'salla_weight': data.get('weight'),
            'salla_weight_type': data.get('weight_type'),
            'url_admin': data.get('urls') and data.get('urls').get('admin') or '',
            'url_customer': data.get('urls') and data.get('urls').get('customer') or '',
            'with_tax': data.get('with_tax'),
            'show_in_app': data.get('show_in_app'),
            'managed_by_branches': data.get('managed_by_branches'),
            'max_items_per_user': data.get('max_items_per_user'),
            'maximum_quantity_per_order': data.get('maximum_quantity_per_order')
        }
        result.update(result_update)

        if data.get('images'):
            for img in data.get('images'):
                if img.get('main'):
                    result.update({'salla_main_image_id': img.get('id')})

        if data.get('metadata'):
            result.update({
                'salla_metadata_title': data.get('metadata').get('title'),
                'salla_metadata_description': data.get('metadata').get('description')
            })
        if data.get('promotion'):
            result.update({
                'salla_promotion_title': data.get('promotion').get('title'),
                'salla_subtitle': data.get('promotion').get('sub_title')
            })

        if data.get('enable_note'):
            result.update(salla_enable_note=data.get('enable_note'))
        if not data.get('with_tax') or not data.get('tax') or (data.get('tax') and data.get('tax').get('amount') == 0):
            result.update(taxes_id=None)
        if data.get('tags'):
            tag_ids = []
            for tag in data.get('tags'):
                tag_id = self.env['product.tags'].search([('salla_id', '=', tag.get('id'))], limit=1)
                if tag_id:
                    tag_ids.append(tag_id.id)
            if tag_ids:
                result.update(tags=[(6, 0, tag_ids)])

        if data.get('consisted_products'):
            all_consisted = []
            for consisted in data.get('consisted_products'):
                product_id = self.env['product.product'].search([('tmpl_salla_id', '=', consisted.get(id))], limit=1)
                if product_id:
                    cons_id = self.env['consisted.product'].search(
                        [('product_id', '=', product_id.id), ('quantity', '=', consisted.get('quantity'))], limit=1)
                    if not cons_id:
                        cons_id = self.env['consisted.product'].create(
                            {'product_id': product_id.id, 'quantity': consisted.get('quantity')})
                        all_consisted.append(cons_id.id)
            if all_consisted:
                result.update(consisted_products_ids=[(6, 0, all_consisted)])
        if hasattr(self.env['product.product'], 'available_in_pos'):
            result.update(available_in_pos=True)
        if data.get('brand_id'):
            brand_id = self.env['product.brand'].search([('salla_id', '=', data.get('brand_id'))], limit=1)
            if brand_id:
                result.update(brand_id=brand_id.id)
        if data.get('categories'):
            cat_ids = [x.get('id') for x in data.get('categories')]
            categ_ids = self.env['product.category'].search([('salla_id', 'in', cat_ids)])
            if categ_ids:
                result.update(categ_id=categ_ids[0].id)
            else:
                for cat in data.get('categories'):
                    self.env['product.category'].x_2_odoo(cat)
                categ_ids = self.env['product.category'].search([('salla_id', 'in', cat_ids)])
                if categ_ids:
                    result.update(categ_id=categ_ids[0].id)
        record_id = self.search([('tmpl_salla_id', '=', result.get('tmpl_salla_id'))], limit=1)
        out_result = result.copy()
        if mode in ['create', 'update']:
            if record_id:
                if data.get('options'):
                    for option in data.get('options'):
                        existing_option_id = record_id.options_ids.filtered(lambda x: x.salla_id == option.get('id'))
                        if existing_option_id:
                            existing_option_id.write_from_salla(option)
                        else:
                            self.env['product.options'].create_from_salla(record_id, option)
                else:
                    record_id.options_ids.with_context(from_salla=True).unlink()

                if fieldslist:
                    out_result = shrinkdict(result, fieldslist)
                if not out_result:
                    out_result = result
                record_id.with_context(from_salla=True).write(out_result)
                if not fieldslist or 'quantity' in fieldslist:
                    record_id.update_quantity_on_hand(data.get('quantity', 0))
            else:
                if fieldslist:
                    out_result = shrinkdict(result, fieldslist)
                if not out_result:
                    out_result = result
                record_id = self.with_context(from_salla=True).create(out_result)
                if data.get('options'):
                    for option in data.get('options'):
                        existing_option_id = record_id.options_ids.filtered(lambda x: x.salla_id == option.get('id'))
                        if existing_option_id:
                            existing_option_id.write_from_salla(option)
                        else:
                            self.env['product.options'].create_from_salla(record_id, option)
                else:
                    record_id.options_ids.with_context(from_salla=True).unlink()
                if not fieldslist or 'quantity' in fieldslist:
                    record_id.update_quantity_on_hand(data.get('quantity', 0))
        elif mode == 'delete':
            if record_id:
                record_id.with_context(from_salla=True).unlink()
        return record_id

    def odoo_2_x(self):
        get_param = self.env['ir.config_parameter'].sudo().get_param
        result = {
            'name': self.name,
            'price': self.list_price,
            'product_type': self.product_type
            in ['product', 'service', 'group_products', 'codes', 'digital', 'food'] and self.product_type or 'product',
            'quantity': self.qty_available, 'unlimited_quantity': True
            if self.product_type in ['codes', 'digital', 'service'] else False,
            'description': self.description_sale and self.description_sale or self.description_sale,
            'categories': self.categ_id.salla_id and [self.categ_id.salla_id] or [],
            'sale_price': self.salla_sale_price,
            'cost_price': self.standard_price,
            'weight_type': self.salla_weight_type,
            'weight': self.salla_weight,
            'mpn': self.salla_mpn and self.salla_mpn or '',
            'hide_quantity': self.salla_hide_quantity,
            'enable_upload_image': self.salla_enable_upload_image,
            'enable_note': self.salla_enable_note,
            'pinned': self.salla_pinned,
            'active_advance': self.salla_active_advance,
            'subtitle': self.salla_subtitle and self.salla_subtitle or '',
            'promotion_title': self.salla_promotion_title and self.salla_promotion_title or '',
            'promotion_subtitle': self.salla_promotion_subtitle and self.salla_promotion_subtitle or '',
            'metadata_title': self.salla_metadata_title and self.salla_metadata_title or '',
            'metadata_description': self.salla_metadata_description and self.salla_metadata_description or '',
            'require_shipping': self.require_shipping,
            'with_tax': self.with_tax,
            'show_in_app': self.show_in_app,
            'managed_by_branches': self.managed_by_branches,
            'max_items_per_user': self.max_items_per_user,
            'maximum_quantity_per_order': self.maximum_quantity_per_order,
            'options':
            [{'id': x.salla_id, 'name': x.name,
              'display_type': x.display_type
              in ['text', 'image', 'color'] and x.display_type or 'text',
              'values':
              [{'id': y.salla_id, 'name': y.name, 'price': self._get_price_from_value(x.id),
                'quantity': 1, 'display_value': self._get_price_from_value(x.id), } for y in x.value_ids]}
             for x in self.options_ids], }
        if self.tags:
            result.update(tags=[x.salla_id for x in self.tags])
        if self.sale_end_date:
            result.update(sale_end=fields.Datetime.to_string(self.sale_end_date))

        if self.product_type in ['product', 'group_products', 'codes', 'digital', 'donating'] and self.salla_gtin:
            result.update(gtin=self.salla_gtin)
        if self.calories and self.product_type == 'food':
            result.update(calories=self.calories)
        if self.consisted_products_ids:
            result.update(consisted_products=[
                {'id': x.product_id.tmpl_salla_id,
                 'quantity': x.quantity
                 }
                for x in self.consisted_products_ids
            ]
            )
        if self.default_code:
            result.update({'sku': self.default_code})
        if self.salla_status:
            result.update(status=self.salla_status)
        if self.brand_id and self.brand_id.salla_id:
            result.update(brand_id=self.brand_id.salla_id)
        if self.tmpl_salla_id:
            result['id'] = self.tmpl_salla_id
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
            response = company_id.odoo_2_x_crud('POST', 'products', payload_json=record)
        if response and response.get('data'):
            self.with_context(from_salla=True).write({'tmpl_salla_id': response.get('data').get('id')})
            if response.get('data') and response.get('data').get('options'):
                for option in response.get('data').get('options'):
                    attr_line_ids = self.attribute_line_ids.filtered(
                        lambda x: x.attribute_id.name == option.get('name'))
                    attr_line_id = self.env['product.product.attribute.line']
                    if len(attr_line_ids) > 0:
                        attr_line_id = attr_line_ids[0]
                        attr_line_id.salla_id = option.get('id')
                        attr_id = attr_line_id.attribute_id
                        for val in option.get('values'):
                            valid = self.env['product.attribute.value'].search([('name', '=', val.get('name')),
                                                                                ('attribute_id', '=', attr_id.id)])
                            if valid:
                                valid.salla_id = val.get('id')
            if self.image_1920:
                self.odoo_2x_attach_image()

    @api.model
    def odoo_2x_read_all(self):
        company = self.env.context.get('company_id', False)
        company_id = self.env.company
        response = None
        if company:
            company_id = self.env['res.company'].browse(company)
        if company_id:
            response = company_id.odoo_2_x_crud('GET', 'products', payload=None)
        if response and response.get('data'):
            for rec in response.get('data'):
                self.x_2_odoo(rec)

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
        if not endpoint and self.tmpl_salla_id:
            endpoint = 'products/' + str(self.tmpl_salla_id)

        record = self.odoo_2_x()
        company = self.env.context.get('company_id', False)
        company_id = self.env.company
        response = None
        if company:
            company_id = self.env['res.company'].browse(company)
        if company_id and self.tmpl_salla_id:
            response = company_id.odoo_2_x_crud('PUT', endpoint, payload_json=record)
            if self.image_1920:
                self.odoo_2x_attach_image()
            else:
                self.odoo_2x_delete_image()
        return response

    def odoo_2x_delete(self):
        company = self.env.context.get('company_id', False)
        company_id = self.env.company
        response = None
        if company:
            company_id = self.env['res.company'].browse(company)
        if company_id and self.tmpl_salla_id:
            response = company_id.odoo_2_x_crud('DELETE', 'products/' + str(self.tmpl_salla_id), payload=None)
        return response

    def odoo_image_2_x(self):
        result = {
            "default": "1",
            "sort": "1",
            "files":[
            ('photo',(f'{self.id}{self.get_image_file("image_1920").get("image_name", "png")}',self.get_image_file('image_1920').get('image_data', None),f'{self.get_image_file("image_1920").get("mimetype", "image/png")}' ))or None
            ]
        }
        return result

    def odoo_2x_attach_image(self):
        if self.salla_main_image_id and not self.salla_main_image_url:
            self.odoo_2x_delete_image()
        if not self.salla_main_image_url:
            record = self.odoo_image_2_x()
            rec_files=record.get("files")
            record.pop("files")
            company = self.env.context.get('company_id', False)
            company_id = self.env.company
            response = None
            if company:
                company_id = self.env['res.company'].browse(company)
            if company_id:
                response = company_id.odoo_2_x_crud(
                    'POST', 'products/'+str(self.tmpl_salla_id)+'/images',payload=record,files=rec_files, headers={"Accept":"*/*"})
            if response and response.get('data'):
                self.with_context(from_salla=True).write({
                    'salla_main_image_id':response.get('data').get('id'),
                    'salla_main_image_url': response.get('data').get('image').get('low_resolution').get('url')})

    def odoo_2x_delete_image(self):
        if self.salla_main_image_id and not self.salla_main_image_url:
            company = self.env.context.get('company_id', False)
            company_id = self.env.company
            response = None
            if company:
                company_id = self.env['res.company'].browse(company)
            if company_id and self.tmpl_salla_id:
                response = company_id.odoo_2_x_crud('DELETE', 'products/images/' + str(self.salla_main_image_id), payload=None)
            # if response and response.get('success'):
            #     self.salla_main_image_id = ""

    def _get_price_from_value(self, value_id):
        value = self.env['product.options.values'].search(
            [('option_id', '=', value_id)], limit=1)
        if value:
            return value.price
        return 0.0

    @api.model
    def create(self, vals):
        # picture_public = {'public': True}
        # vals.update(picture_public)
        result = super().create(vals)
        company_id = self.env.company
        for prod in self:
            if not self.env.context.get('from_salla', False) and company_id.is_salla_shop:
                try:
                    if self.env.company.check_sync(prod._name) and prod.is_salla_product:
                        result.odoo_2x_create()
                except Exception as error:
                    raise ValidationError(error)
        return result

    def write(self, vals):
        result = super().write(vals)
        company_id = self.env.company
        for prod in self:
            if not self.env.context.get('from_salla', False) and company_id.is_salla_shop and prod.tmpl_salla_id:
                try:
                    if self.env.company.check_sync(prod._name) and prod.is_salla_product:
                        prod.odoo_2x_update()
                except Exception as error:
                    raise ValidationError(error)
        return result

    def unlink(self):
        company_id = self.env.company
        for prod in self:
            if not self.env.context.get('from_salla', False) and company_id.is_salla_shop:
                try:
                    if self.env.company.check_sync(prod._name) and prod.is_salla_product:
                        prod.odoo_2x_delete()
                except Exception as error:
                    raise ValidationError(error)
        return super().unlink()

    def update_quantity_on_hand(self, quantity):
        advanced_option_groups = [
            'stock.group_stock_multi_locations',
            'stock.group_production_lot',
            'stock.group_tracking_owner',
            'product.group_tracking_lot'
        ]

        default_product_id = self.env.context.get('default_product_id', len(
            self.product_variant_ids) == 1 and self.product_variant_id.id)
        warehouse = self.env['stock.warehouse'].search(
            [('company_id', '=', self.env.company.id)], limit=1
        )
        # Before creating a new quant, the quand `create` method will check if
        # it exists already. If it does, it'll edit its `inventory_quantity`
        # instead of create a new one.
        quant_id = self.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': default_product_id,
            'location_id': warehouse.lot_stock_id.id,
            'inventory_quantity': quantity,
        })
        quant_id._apply_inventory()
        quant_id.inventory_quantity_set = False
        # quant_id.inventory_quantity = quant_id.quantity + quant_id.inventory_diff_quantity
        # quant_id.action_apply_inventory()


class ProductTemplateAttributeLine(models.Model):
    _inherit = 'product.template.attribute.line'

    salla_id = fields.Integer()


class ProductAttributeValue(models.Model):
    _inherit = 'product.attribute.value'

    salla_id = fields.Integer()
    price = fields.Float()
