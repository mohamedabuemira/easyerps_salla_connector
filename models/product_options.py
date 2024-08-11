from odoo import models, fields, api, _
from .ImageMixin import get_image_from_url
from odoo.exceptions import ValidationError, UserError


class ProductOptionValues(models.Model):
    _name = 'product.options.values'
    _description = 'product.options.values'

    salla_id = fields.Integer()
    name = fields.Char()
    price = fields.Float()
    quantity = fields.Integer()
    display_value = fields.Char()
    option_id = fields.Many2one('product.options')


class ProductOptions(models.Model):
    _name = 'product.options'
    _description = 'product options'

    salla_id = fields.Integer()
    product_id = fields.Many2one('product.product')
    name = fields.Char()
    display_type = fields.Selection(
        [('text', 'Text'),
         ('image', 'Image'),
         ('color', 'Color')
         ],
        default='text'
    )
    value_ids = fields.One2many('product.options.values', 'option_id', string='Values')

    def unlink(self):
        for rec in self:
            if rec.salla_id:
                self.env.company.odoo_2_x_crud('DELETE', 'products/options/'+str(self.salla_id))
        return super().unlink()

    def action_open_attribute_values(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _("Product Optionss Values"),
            'res_model': 'product.options.values',
            'view_mode': 'tree',
            'domain': [('id', 'in', self.value_ids.ids)],
            'views': [
                (self.env.ref('easyerps_salla_connector.product_options_values_view_tree').id, 'list'),
            ],
            'context':{'create':False}
        }
    def action_get_options(self):
        pass

    @api.model
    def salla_to_odoo_dict(self, data):
        result = {
            'salla_id': data.get('id'),
            'name': data.get('name'),
            'display_type': data.get('display_type'),
        }
        if data.get('values'):
            values = []
            for value in data.get('values'):
                value_id = self.env['product.options.values'].search([('salla_id', '=', value.get('id'))], limit=1)
                if not value_id:
                    value_id = self.env['product.options.values'].create({
                        'salla_id': value.get('id'),
                        'name': value.get('name'),
                        'price': value.get('price') and value.get('price').get('amount') or 0.0,
                        'display_value': value.get('display_value'),
                    })
                else:
                    value_id.write({
                        'salla_id': value.get('id'),
                        'name': value.get('name'),
                        'price': value.get('price') and value.get('price').get('amount') or 0.0,
                        'display_value': value.get('display_value'),
                    })
                values.append(value_id.id)
            if values:
                result.update(value_ids=[(6, 0, values)])

        return result

    @api.model
    def create_from_salla(self, product_id, data):
        in_data = {
            'product_id': product_id.id
        }
        in_data.update(self.salla_to_odoo_dict(data))
        self.create(in_data)

    def write_from_salla(self, data):
        self.write(self.salla_to_odoo_dict(data))
