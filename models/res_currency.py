from odoo import models,fields,api,_
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
    
class ResCurrency(models.Model):
    _inherit='res.currency'


    salla_id=fields.Integer()
    @api.model
    def get_endpoint(self):
        return 'currencies'

    @api.model
    def x_2_odoo(self, data, mode='create'):
        result = {
            'salla_id': data.get('id'),
            'name':data.get('code'),
            'full_name':data.get('name'),
            'symbol':data.get('symbol'),
            'active':True
        }
        if mode == 'abstract':
            return clean_nones(result)
        record_id = self.search(
            [('name', '=', data.get('code'))],
            limit=1)
        if not record_id:
            record_id = self.search(
            [('active','=',False),('name', '=', data.get('code'))],
            limit=1)
        if not record_id:
            record_id = self.search(
            [('salla_id', '=', result.get('salla_id'))],
            limit=1)
        if record_id:
            record_id.active=True

        if mode in ['create', 'update']:
            if record_id:
                record_id.write({'salla_id': result.get('salla_id')})
            else:
                self.create(result)
        elif mode == 'delete':
            if record_id:
                record_id.unlink()

    def odoo_2_x(self):
        result = {
            "name": self.name,
            "name_en": self.name_en,
            "code": self.code,
            "mobile_code": self.phone_code,
        }
        return result

        # API CRUDS

    @api.model
    def odoo_2x_read_all(self):
        company = self.env.context.get('company_id', False)
        company_id = self.env.company
        response = None
        if company:
            company_id = self.env['res.company'].browse(company)
        if company_id:
            response = company_id.odoo_2_x_crud('GET', 'currencies', payload=None)
        if response and response.get('data'):
            for rec in response.get('data'):
                self.x_2_odoo(rec)

    def odoo_2x_read(self):
        company = self.env.context.get('company_id', False)
        company_id = self.env.company
        response = None
        if company:
            company_id = self.env['res.company'].browse(company)
        if company_id and self.salla_id:
            response = company_id.odoo_2_x_crud('GET', 'currencies/' + self.salla_id, payload=None)
        if response and response.get('data'):
            self.x_2_odoo(response.get('data'))


