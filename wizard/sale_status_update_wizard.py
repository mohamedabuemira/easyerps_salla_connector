from odoo import models, fields, api, _


class StatusUpdater(models.TransientModel):
    _name = 'salla.order.status.update.wizard'
    _description = 'Order status updater'

    order_id = fields.Many2one('sale.order')
    status_id = fields.Many2one('sale.order.status')
    slug = fields.Char()
    notes = fields.Text()

    def action_update(self):
        endpoint = 'orders/'+str(self.order_id.salla_id)+'/status'
        payload = {
            'status_id': self.status_id.salla_id,
            # 'slug': self.status_id.slug,
            'note': self.notes
        }

        # if self.status_id.type == 'custom':
            # payload.update(slug=self.status_id.parent_id.slug)
        response = self.env.company.odoo_2_x_crud('POST', endpoint, payload_json=payload)
        if response and response.get('success') == True:
            message = 'Update Successfull'
            if response.get('data') and response.get('data').get('message'):
                message = response.get('data').get('message')
            result_id = self.env['result.dialog'].create({'name': message})
            self.order_id.update_shipment()
            self.order_id.status = self.status_id
            self.order_id.status_checker()
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
