import base64
import io
import json
from odoo import models, fields, api, _, tools
from odoo.tools.mimetypes import guess_mimetype
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
        return [clean_nones(x) for x in value if x ]
    elif isinstance(value, dict):
        return {
            key: clean_nones(val)
            for key, val in value.items()
            if val 
        }
    else:
        return value
class ProductBrand(models.Model):
    _name = 'product.brand'
    _description = 'Product Brand'

    name = fields.Char('Brand name')
    description = fields.Text('Brand description')
    banner = fields.Binary()
    logo = fields.Binary()
    banner_url = fields.Char()
    logo_url = fields.Char()
    ar_char = fields.Char()
    en_char = fields.Char()
    salla_id = fields.Integer()

    is_salla = fields.Boolean()
    is_salla_checker = fields.Boolean(compute='_compute_is_salla')

    def get_image_file(self, name):
        imgtext = ".png"
        image = ''
        mimetype=''
        image_data = None
        if name == "logo":
            image = self.logo #tools.image_process(self.logo, size=(500, 0))
        elif name == "banner":
            image = self.banner# tools.image_process(self.banner, size=(500, 0))
        if image:
            image_base64 = base64.b64decode(image)
            image_data = io.BytesIO(image_base64)
            mimetype = guess_mimetype(image_base64, default='image/png')
            imgext = '.' + mimetype.split('/')[1]
            if imgext == '.svg+xml':
                imgext = '.svg'
        return {'image_data': image_data, 'image_name': imgtext,'mimetype':mimetype}


    @api.depends('salla_id')
    def _compute_is_salla(self):
        for rec in self:
            isfalse = False
            if rec.salla_id:
                isfalse = True
            rec.is_salla = isfalse
            rec.is_salla_checker = isfalse


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
        return 'brands'
    
    @api.model
    def x_2_odoo(self, data, mode='create'):
        result = {
            'salla_id': data.get('id'),
            'name': data.get('name'),
            'description': data.get('description'),
            'banner_url': data.get('banner'),
            'logo_url': data.get('logo'),
            'ar_char': data.get('ar_char'),
            'en_char': data.get('en_char'),
            'banner':data.get('banner') and get_image_from_url(data.get('banner')) or None,
            'logo':data.get('logo') and get_image_from_url(data.get('logo')) or None,
        }
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

    def odoo_2_x(self):
        get_param = self.env['ir.config_parameter'].sudo().get_param
        result = {
            "name": self.name,
            "description": self.description,
            "files":[
            ('logo',(f'{self.name}{self.get_image_file("logo").get("image_name", "png")}',self.get_image_file('logo').get('image_data', None),f'{self.get_image_file("logo").get("mimetype", "image/png")}' ))or None,
            ('banner',(f'{self.id}{self.get_image_file("banner").get("image_name", "png")}',self.get_image_file('banner').get('image_data', None),f'{self.get_image_file("banner").get("mimetype", "image/png")}') )or None
            ]

        }

        if self.salla_id:
            result['id'] = self.salla_id
        return result

    # API CRUDS
    def odoo_2x_create(self):
        record = self.odoo_2_x()
        rec_files=record.get("files")
        record.pop("files")
        company = self.env.context.get('company_id', False)
        company_id = self.env.company
        response = None
        if company:
            company_id = self.env['res.company'].browse(company)
        if company_id:
            response = company_id.odoo_2_x_crud(
                'POST', 'brands',payload=record,files=rec_files, headers={"Accept":"*/*"})
        if response and response.get('data'):
            self.with_context(from_salla=True).write({'salla_id':response.get('data').get('id')})

    @api.model
    def odoo_2x_read_all(self):
        company = self.env.context.get('company_id', False)
        company_id = self.env.company
        response = None
        if company:
            company_id = self.env['res.company'].browse(company)
        if company_id:
            response = company_id.odoo_2_x_crud( 'GET', 'brands', payload=None)
        if response and response.get('data'):
            for rec in response.get('data'):
                self.x_2_odoo(rec)

    def odoo_2x_read(self):
        company = self.env.context.get('company_id', False)
        company_id = self.env.company
        response = None
        if company:
            company_id = self.env['res.company'].browse(company)
        if company_id :
            response = company_id.odoo_2_x_crud( 'GET', 'brands/' + str(self.salla_id), payload=None)
        if response and response.get('data'):
            self.x_2_odoo(response.get('data'))

    def odoo_2x_update(self,endpoint=None):
        if not endpoint:
            endpoint = 'brands/' + str(self.salla_id)
        record = self.odoo_2_x()
        rec_files = record.get("files")
        record.pop("files")
        company = self.env.context.get('company_id', False)
        company_id = self.env.company
        response = None
        if company:
            company_id = self.env['res.company'].browse(company)
        if company_id and self.salla_id:
            response = company_id.odoo_2_x_crud(
                'PUT', endpoint,payload=record,files=rec_files, headers={"Accept":"*/*"})
        return response

    def odoo_2x_delete(self):
        company = self.env.context.get('company_id', False)
        company_id = self.env.company
        response = None
        if company:
            company_id = self.env['res.company'].browse(company)
        if company_id and self.salla_id:
            for rec in self:
                response = company_id.odoo_2_x_crud( 'DELETE', 'brands/' + str(rec.salla_id), payload=None)
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