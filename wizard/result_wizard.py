from odoo import models,fields,api

class Result(models.TransientModel):
    _name='result.dialog'
    _description='result.dialog'

    name=fields.Char(default='Operation successful')

