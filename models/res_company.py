import time
import uuid
from datetime import datetime
import requests
from urllib.parse import urlencode, quote_plus
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from .ImageMixin import get_image_from_url
import json

import logging
_logger = logging.getLogger(__name__)


OBJECT_LIST = [
    ('res.country', 'COUNTRIES'),
    # ('res.city', 'CITIES'),
    # ('res.currency', 'CURRENCIES'),
    ('res.company.branch', 'BRANCHES'),
    ('salla.webhooks', 'WEBHOOKS'),
    ('salla.affiliates', 'AFFILIATES'),
    ('salla.advertisement', 'ADVERTISEMENTS'),
    ('salla.coupon', 'COUPONS'),
    ('salla.offers', 'OFFERS'),
    ('account.tax', 'TAXES'),
    ('account.payment.method', 'PAYMENT METHODS'),
    ('product.brand', 'BRANDS'),
    ('product.tags', 'PRODUCT TAGS'),
    ('product.category', 'CATEGORIES'),
    ('product.product', 'PRODUCTS'),
    ('sale.order.tags', 'ORDERS TAGS'),
    ('sale.order.status', 'ORDERS STATUS'),
    ('shipping.company', 'SHIPPING COMPANY'),
    ('shipping.rules', 'SHIPPING RULES'),
    ('shipping.zone', 'SHIPPING ZONE'),
    ('customer.groups', 'CUSTOMER GROUPS'),
    ('res.partner', 'CUSTOMERS'),
    ('sale.order', 'ORDERS'),
]


class AutSyncObjects(models.Model):
    _name = 'auto.syncer.objects'
    _description = 'auto.syncer.objects'
    name = fields.Char(translate=True)
    model_name = fields.Char()


class ResCompany(models.Model):
    _inherit = 'res.company'

    is_salla_shop = fields.Boolean()

    salla_merchant_id = fields.Integer('Merchant ID')
    salla_access_token = fields.Text("Access Token")
    salla_refresh_token = fields.Text("Refresh Token")
    salla_expires = fields.Integer("Expires")
    salla_expires_date = fields.Datetime("Expires Date", compute="_compute_expire_date", store=True)
    salla_scope = fields.Char('Scope')
    salla_auth_url = fields.Char("Auth Url", default="https://accounts.salla.sa/oauth2/auth")
    salla_app_id = fields.Char("App ID")
    salla_client_id = fields.Char("ID")
    salla_client_secret = fields.Char("Secret")
    salla_webhook = fields.Char("Webhook url", compute="_compute_webhook")
    salla_auth_code = fields.Char('Authorization code')

    salla_webhook_secret = fields.Char("WebHook Secret")
    salla_base_url = fields.Char("Salla Base Url", compute="_compute_default_salla")
    salla_state = fields.Char()
    salla_auth_webhook = fields.Char('Auth webhook', compute='_compute_auth_webhook')
    branch_ids = fields.One2many('res.company.branch', 'company_id', 'Branches')
    debug_mode = fields.Boolean()
    salla_object_list = fields.Selection(OBJECT_LIST, 'MODEL')
    salla_store_info = fields.Text('Store INFO')
    store_name = fields.Char()
    store_email = fields.Char()
    store_plan = fields.Char()
    store_domain = fields.Char()
    store_description = fields.Char()
    store_avatar = fields.Binary()
    salla_user_info = fields.Text('Merchant INFO')
    auto_syncers_ids = fields.Many2many('auto.syncer.objects', relation='company_autosyncer_erl', string="Sync")
    easyerps_api_key = fields.Char('Api Key')

    shipping_cost_product_id = fields.Many2one('product.product',
        string="Shipping Cost Product",
        help="This product will be used as Shipping Cost on a sale order.")
    cod_cost_product_id = fields.Many2one('product.product',
        string="Cash on Delivery Cost Product",
        help="This product will be used as Cash on Delivery Cost on a sale order.")

    status_to_confirm = fields.Many2one('sale.order.status')
    status_to_set_delivery_done = fields.Many2one('sale.order.status')
    status_to_create_invoice = fields.Many2one('sale.order.status')
    validate_invoice = fields.Boolean(string='Validate invoice?', )
    atu_payment_register = fields.Boolean('Atu Payment Register',
                                          help="Automatically Payment Register.")
    journal_id = fields.Many2one('account.journal', store=True, readonly=False,
                                 domain="[('company_id', '=', id), ('type', 'in', ('bank', 'cash'))]")
    salla_seo_title = fields.Char()
    salla_seo_keywords = fields.Char()
    salla_seo_description = fields.Char()
    salla_seo_url = fields.Char()
    salla_seo_friendly_urls_status = fields.Boolean(default=True)
    salla_seo_refresh_sitemap = fields.Char()

    select_all_webhook = fields.Boolean(default=True)

    @api.onchange('select_all_webhook')
    def _onchange_all_webhook(self):
        if self.select_all_webhook:
            self.salla_webhook_events_ids.write({'is_active': True})
        else:
            self.salla_webhook_events_ids.write({'is_active': False})

    def action_list_seo(self):
        response = self.odoo_2_x_crud('GET', 'seo')
        if response and response.get('data'):
            data = response.get('data')
            self.write(
                {
                    'salla_seo_title': data.get('title'),
                    'salla_seo_keywords': data.get('keywords'),
                    'salla_seo_description': data.get('description'),
                    'salla_seo_url': data.get('url'),
                    'salla_seo_friendly_urls_status': data.get('friendly_urls_status'),
                    'salla_seo_refresh_sitemap': data.get('refresh_sitemap')
                }
            )

    def action_put_seo(self):
        message = 'Failed'
        payload = {
            'title': self.salla_seo_title,
            'keywords': self.salla_seo_keywords,
            'description': self.salla_seo_description,
            'url': self.salla_seo_url,
            'friendly_urls_status': self.salla_seo_friendly_urls_status,
            'refresh_sitemap': self.salla_seo_refresh_sitemap
        }
        response = self.odoo_2_x_crud('GET', 'seo', payload_json=payload)
        if response and response.get('success'):
            message = 'Succeeded'
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

    def check_sync(self, model_name):
        if self.auto_syncers_ids and self.auto_syncers_ids.filtered(lambda x: x.model_name == model_name):
            return True
        return False

    def action_genrerate_apikey(self):
        self.easyerps_api_key = uuid.uuid4()
    #
    # EVENTS
    #

    # @api.onchange("is_salla_shop")
    # def _onchange_is_salla_shop(self):
    #     if self.is_salla_shop and not self.salla_webhook_events_ids:
    #         event_list_ids = self.env['salla.event.list'].search([])
    #         data = []
    #         for event in event_list_ids:
    #             data.append((0, 0, {'event_id': event.id, 'name': event.description}))
    #         self.salla_webhook_events_ids = data

    def action_build_webhooks(self):
        self._onchange_is_salla_shop()

    @api.depends('is_salla_shop')
    def _compute_auth_webhook(self):
        get_param = self.env['ir.config_parameter'].sudo().get_param
        base_url = get_param('web.base.url')
        for rec in self:
            if rec.id and rec.is_salla_shop:
                rec.salla_auth_webhook = base_url + '/oauth/callback'  # +'/'+str(rec.id)
            else:
                rec.salla_auth_webhook = ""

    @api.depends("is_salla_shop")
    def _compute_webhook(self):
        get_param = self.env['ir.config_parameter'].sudo().get_param
        base_url = get_param('web.base.url')
        for rec in self:
            if rec.id and rec.is_salla_shop:
                rec.salla_webhook = base_url + "/web/sallahook/" + str(rec.id)
            else:
                rec.salla_webhook = ""

    @api.depends('salla_expires')
    def _compute_expire_date(self):
        for rec in self:
            if rec.salla_expires:
                rec.salla_expires_date = datetime.fromtimestamp(rec.salla_expires)
            else:
                rec.salla_expires_date = None

    @api.depends("is_salla_shop")
    def _compute_default_salla(self):
        for rec in self:
            if rec.is_salla_shop:
                rec.salla_base_url = "https://api.salla.dev/admin/v2"
            else:
                rec.salla_base_url = ""
    #
    # PRIVATE
    #

    def _expired(self, timestamp):
        current_time = int(time.time())
        if current_time > int(timestamp):
            return True
        return False

    def _do_request(self, method, endpoint_url, payload=None, headers=None, **kwargs):
        try:
            cookies = kwargs.get('cookies', None)
            payload_json = kwargs.get('payload_json', None)
            files = kwargs.get('files', None)
            response = requests.request(method,
                                        endpoint_url,
                                        data=payload,
                                        json=payload_json,
                                        headers=headers,
                                        timeout=60,
                                        cookies=cookies,
                                        files=files)
            response.raise_for_status()
        except requests.exceptions.ConnectionError:
            _logger.exception("unable to reach endpoint at %s", endpoint_url)
            raise ValidationError(
                "Salla: " +
                _("Could not establish the connection to the API."))
        except requests.exceptions.HTTPError as error:
            raise ValidationError(" Error " + str(response.status_code) +
                                  str(response.text.replace("\\/", "/").encode().decode('unicode-escape')))
        return response
    #
    # HELPERS
    #

    def action_partial_fetch(self):
        if self.salla_object_list:
            objs = self.env[self.salla_object_list]
            if hasattr(objs, 'odoo_2x_read_all'):
                objs.with_context(company_id=self.id).odoo_2x_read_all()

    def action_partial_push(self):
        if self.salla_object_list:
            objs = self.env[self.salla_object_list]
            if hasattr(objs, 'salla_id'):
                objs = self.env[self.salla_object_list].with_context(
                    company_id=self.id).search([('salla_id', '=', False)])
            elif hasattr(objs, 'tmpl_salla_id'):
                objs = self.env[self.salla_object_list].with_context(
                    company_id=self.id).search([('tmpl_salla_id', '=', False)])
            if hasattr(objs, 'odoo_2x_create'):
                for obj in objs:
                    obj.with_context(company_id=self.id).odoo_2x_create()

    def get_merchant_profile(self):
        headers = {
            "Authorization": "Bearer " + self.request_salla_token(),
            "Content-Type": "application/json"
        }
        endpoint_url = "https://accounts.salla.sa/oauth2/user/info"
        response = self._do_request('GET', endpoint_url, None, headers)
        if response:
            response_data = response.json()
            data = {
                'salla_merchant_id': response_data.get('data').get('merchant').get('id'),
                'salla_user_info': json.dumps(response_data.get('data')).replace("\\/", "/").encode().decode('unicode-escape')
            }
            self.write(data)

    def get_store_profile(self):
        headers = {
            "Authorization": "Bearer " + self.request_salla_token(),
            "Content-Type": "application/json"
        }
        endpoint_url = self.salla_base_url + '/store/info'
        response = self._do_request('GET', endpoint_url, None, headers, timeout=90)
        if response:
            response_data = response.json()
            # data = {'salla_store_info': json.dumps(response_data.get('data')).replace(
            #     "\\/", "/").encode().decode('unicode-escape')}
            data = {
                'salla_merchant_id': response_data.get('data').get('id'),
                'store_name': response_data.get('data').get('name'),
                'store_email': response_data.get('data').get('email'),
                'store_avatar': response_data.get('data').get('avatar') and get_image_from_url(
                    response_data.get('data').get('avatar')) or None,
                'store_plan': response_data.get('data').get('plan'),
                'store_domain': response_data.get('data').get('domain'),
                'store_description': response_data.get('data').get('description'),
                    }
            self.write(data)

    def sync_to_salla(self):
        models_str = OBJECT_LIST
        for model_str in models_str:
            objs = self.env[model_str[0]]
            if not hasattr(objs, 'odoo_2x_create'):
                continue
            if hasattr(objs, 'salla_id'):
                objs = self.env[model_str[0]].with_context(company_id=self.id).search([('salla_id', '=', False)])
            elif hasattr(objs, 'tmpl_salla_id'):
                objs = self.env[model_str[0]].with_context(company_id=self.id).search([('tmpl_salla_id', '=', False)])
            for obj in objs:
                obj.with_context(company_id=self.id).odoo_2x_create()
            self.env.cr.commit()

    def sync_all_to_salla(self, models_lists=None):
        models_str = OBJECT_LIST
        for model_str in models_str:
            objs = self.env[model_str[0]]
            if models_lists:
                if model_str[0] in models_lists:
                    if not hasattr(objs, 'odoo_2x_create'):
                        continue
                    if hasattr(objs, 'salla_id'):
                        objs = self.env[model_str[0]].with_context(
                            company_id=self.id).search([('salla_id', '=', False)])
                    elif hasattr(objs, 'tmpl_salla_id'):
                        objs = self.env[model_str[0]].with_context(
                            company_id=self.id).search([('tmpl_salla_id', '=', False)])
                    for obj in objs:
                        obj.with_context(company_id=self.id).odoo_2x_create()
            else:
                if not hasattr(objs, 'odoo_2x_create'):
                    continue
                if hasattr(objs, 'salla_id'):
                    objs = self.env[model_str[0]].with_context(company_id=self.id).search([('salla_id', '=', False)])
                elif hasattr(objs, 'tmpl_salla_id'):
                    objs = self.env[model_str[0]].with_context(
                        company_id=self.id).search([('tmpl_salla_id', '=', False)])
                for obj in objs:
                    obj.with_context(company_id=self.id).odoo_2x_create()
            self.env.cr.commit()

    def sync_from_salla(self):
        models_str = OBJECT_LIST
        for model_str in models_str:
            objs = self.env[model_str[0]]
            if hasattr(objs, 'odoo_2x_read_all'):
                objs.with_context(company_id=self.id).odoo_2x_read_all()

    def sync_selected_from_salla(self, models_list=None):
        models_str = OBJECT_LIST
        for model_str in models_str:
            objs = self.env[model_str[0]]
            if models_list:
                if model_str[0] in models_list:
                    if hasattr(objs, 'odoo_2x_read_all'):
                        objs.with_context(company_id=self.id).odoo_2x_read_all()
            else:
                objs = self.env[model_str[0]]
                if hasattr(objs, 'odoo_2x_read_all'):
                    objs.with_context(company_id=self.id).odoo_2x_read_all()

    def action_reset_salla(self):
        to_reset = {
            "salla_merchant_id": None,
            "salla_access_token": None,
            "salla_refresh_token": None,
            "salla_expires": 0,
            "salla_auth_code": None,
        }
        self.write(to_reset)


    def odoo_2_x_crud(self, method, endpoint, payload=None, payload_json=None, files=None,headers=None):
        if not headers:
            headers = {
                "Content-Type": "application/json"
            }
        headers.update(Authorization="Bearer " + self.request_salla_token())
        endpoint_url = self.salla_base_url + '/' + endpoint
        response = self._do_request(method, endpoint_url, payload, headers, payload_json=payload_json, files=files)
        return response.json()

    # def action_deactivate_webhooks(self):
    #     message = 'Failed'
    #     headers = {
    #         "Authorization": "Bearer " + self.request_salla_token(),
    #         "Content-Type": "application/json"
    #     }
    #     events = self.salla_webhook_events_ids.filtered(lambda x: x.is_active == False and x.salla_id)
    #     for event in events:
    #         endpoint_url = self.salla_base_url+"/webhooks/unsubscribe"
    #         payload = {
    #             "id": event.salla_id,
    #         }
    #         response = self._do_request('POST', endpoint_url, None, headers, payload_json=payload)
    #         response_data = response.json()
    #         if response_data and response_data.get('success'):
    #             message = 'Success'
    #             event.write({'salla_id': None, 'is_active': False})
    #     result_id = self.env['result.dialog'].create({'name': message})
    #     view = self.env.ref('easyerps_salla_connector.view_resultr_wizard')
    #     return {
    #         'name': _("Message"),
    #         'view_mode': 'form',
    #         'view_id': view.id,
    #         'view_type': 'form',
    #         'res_model': 'result.dialog',
    #         'res_id': result_id.id,
    #         'type': 'ir.actions.act_window',
    #         'target': 'new',
    #     }

    # def action_subscribe_webhooks(self):
    #     message = 'Failed'
    #     headers = {
    #         "Authorization": "Bearer " + self.request_salla_token(),
    #         "Content-Type": "application/json"
    #     }
    #     events = self.salla_webhook_events_ids.filtered(lambda x: x.is_active == True)
    #     for event in events:
    #         endpoint_url = self.salla_base_url+"/webhooks/subscribe"
    #         payload = {
    #             "name": event.name,
    #             "event": event.event_id.name,
    #             "url": self.salla_webhook,
    #             "headers": [
    #                 {
    #                     'key': 'authorization',
    #                     'value': self.easyerps_api_key
    #                 }
    #             ]
    #             # "security_strategy": "signature",
    #             # "secret": self.salla_webhook_secret
    #
    #         }
    #         if event.rule:
    #             payload["rule"] = event.rule
    #         response = self._do_request('POST', endpoint_url, None, headers, payload_json=payload)
    #         response_data = response.json()
    #         if response_data and response_data.get('data'):
    #             event.salla_id = response_data.get('data').get('id')
    #             message = 'Success'
    #     result_id = self.env['result.dialog'].create({'name': message})
    #     view = self.env.ref('easyerps_salla_connector.view_resultr_wizard')
    #     return {
    #         'name': _("Message"),
    #         'view_mode': 'form',
    #         'view_id': view.id,
    #         'view_type': 'form',
    #         'res_model': 'result.dialog',
    #         'res_id': result_id.id,
    #         'type': 'ir.actions.act_window',
    #         'target': 'new',
    #     }

    def action_request_salla_token(self):
        self.request_salla_token()

    def action_refresh_salla_token(self):
        self.request_salla_token(force_refresh=True)

    def request_salla_token(self, force_refresh=None):
        endpoint_url = "https://accounts.salla.sa/oauth2/token"
        grant_type = 'authorization_code'
        if self.salla_refresh_token:
            grant_type = "refresh_token"
        if self.salla_access_token and not self._expired(self.salla_expires) and not force_refresh:
            return self.salla_access_token

        payload = {
            "client_id": self.salla_client_id,
            "client_secret": self.salla_client_secret,
            "grant_type": grant_type,
            "redirect_uri": self.salla_auth_webhook  # + "/" + str(self.id),
        }
        if grant_type == 'authorization_code':
            payload.update(code=self.salla_auth_code, scope="offline_access")
        elif self.salla_refresh_token:
            payload.update(refresh_token=self.salla_refresh_token)

        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        endpoint_url += '?' + urlencode(payload, quote_via=quote_plus)
        response = self._do_request('POST', endpoint_url, payload, headers)
        if response.status_code == 200:
            response_data = response.json()
            data = {
                'salla_access_token': response_data.get('access_token'),
                'salla_refresh_token': response_data.get('refresh_token'),
                'salla_scope': response_data.get('scope')
            }
            data['salla_expires'] = response_data.get('expires', False) or response_data.get('expires_in', 0)
            data['salla_expires'] += int(time.time())
            self.write(data)
        return self.salla_access_token

    def process_auth(self, kw, headers):
        event = kw.get('event', False)
        data = kw.get('data', False)
        to_write = {}
        to_write.update(is_salla_shop=True)
        if data.get('merchant'):
            to_write.update(salla_merchant_id=data.get('merchant'))
        if data.get('app_id'):
            to_write.update(salla_app_id=data.get('app_id'))

        if not event:
            self.write(to_write)
            return {'status': 200, 'result': 'OK'}
        if event == "app.installed":
            to_write.update(salla_merchant_id=kw.get('merchant'))
            if data:
                to_write.update(salla_app_id=data.get('id'))
            self.write(to_write)
            return {'status': 200, 'result': 'OK'}
        elif event == 'app.store.authorize':
            if headers:
                strategy = headers.get('X-Salla-Security-Strategy', None)
                if strategy == 'Token':
                    code = headers.get('Authorization', False)
                    if code:
                        to_write.update(salla_auth_code=code)
            if data:
                if data.get('client_id'):
                    to_write.update(salla_client_id=data.get('client_id'))
                if data.get('client_secret'):
                    to_write.update(salla_client_secret=data.get('client_secret'))
                to_write.update(
                    salla_access_token=data.get('access_token'),
                    salla_expires=data.get('expires'),
                    salla_refresh_token=data.get('refresh_token'),
                    salla_scope=data.get('scope')
                )
                if data.get('authorisation'):
                    to_write.update(salla_auth_code=data.get('authorisation'))
                if data.get('merchant'):
                    to_write.update(salla_merchant_id=data.get('merchant'))
                self.write(to_write)
                self.get_store_profile()
                self.action_build_dashboard()
                return {'status': 200, 'result': 'OK'}
        elif event == 'app.store.token':
            if data:
                if data.get('client_id'):
                    to_write.update(salla_client_id=data.get('client_id'))
                if data.get('client_secret'):
                    to_write.update(salla_client_secret=data.get('client_secret'))
                to_write.update(
                    salla_access_token=data.get('access_token'),
                    salla_expires=data.get('expires'),
                    salla_refresh_token=data.get('refresh_token')
                )
                self.write(to_write)
                return {'status': 200, 'result': 'OK'}
        return {'status': 500, 'result': 'Unknown reason'}

    def action_build_dashboard(self):
        for mod in OBJECT_LIST:
            dashboard = self.env['salla.dashboard'].sudo().search(
                [('company_id', '=', self.id), ('model_name', '=', mod[0])])
            if not dashboard:
                self.env['salla.dashboard'].sudo().create({'company_id': self.id, 'model_name': mod[0]})
        dashboard = self.env['salla.dashboard'].sudo().search(
            [('company_id', '=', self.id), ('model_name', '=', 'all')])
        if not dashboard:
            self.env['salla.dashboard'].sudo().create({'company_id': self.id, 'model_name': 'all'})
        self.env['salla.webhook.event.list'].odoo_2x_read_all()
