import binascii
from odoo.tools import date_utils
import json
from odoo import fields, http, SUPERUSER_ID, _
from odoo.exceptions import AccessError, MissingError, ValidationError
from odoo.fields import Command
from odoo.http import request, Response
import logging
_logger = logging.getLogger(__name__)


def my_json_response(self, result=None, error=None):
    response = {
        'jsonrpc': '2.0',
        'id': self.jsonrequest.get('id')
    }
    # if error is not None:
    #    response = error
    if result is not None:
        response = result

    mime = 'application/json'
    body = json.dumps(response, default=date_utils.json_default)

    return Response(
        body, status=error and error.pop('http_status', 200) or 200,
        headers=[('Content-Type', mime), ('Content-Length', len(body))]
    )


class SallaController(http.Controller):

    @http.route(['/web/sallahook/<int:cny>'], type='json', auth="public")
    def salla_webhooks(self, cny, **kw):
        # request._json_response = my_json_response.__get__(request, JsonRequest)
        data = request.dispatcher.jsonrequest
        event = data.get("event", False)
        headers = request.httprequest.headers
        # response = JsonRequest(request.httprequest)
        response_headers = {'Content-Type': 'application/json'}
        authorization = data.get('authorization')
        error = None
        result = {}
        retour = {}
        company_id = request.env['res.company'].sudo().search([('id', '=', cny)])
        success = False
        if headers and headers.get('X-Salla-Signature'):
            success = False
        if headers and headers.get('Authorization') and not data.get('authorization'):
            authorization = headers.get('Authorization')
        _logger.info(f'WEBHOOK DATA {data}, HEADERS {headers}')
        if not company_id or not company_id.easyerps_api_key or not authorization:
            message = "Check Api key on client and in Salla Shop"
            deffields = {
                "client_key":"Invalid client Key"
            }
            if not company_id:
                message = "Check Company ID"
                deffields = {
                    "odoo_company_id":"Invalid ID"
                    }
            result = {
                "status": 422,
                "success": False,
                "code": "error",
                "message": message,
                "fields":deffields
            }
            return result  # Response(json.dumps(result), headers=response_headers)
        if company_id.easyerps_api_key != authorization:
            result = {
                "status": 422,
                "success": False,
                "code": "error",
                "message": 'Key Mismatch Check Api key on client and in Salla Shop',
                "fields": {
                    "client_key": 'Key Mismatch Check Api key on client and in Salla Shop',
                }
            }
            return result

        _logger.info(f'Process {data}')
        if event == 'Test':
            return result
        if event in ['app.store.authorize', 'app.installed', 'app.store.token']:

            if company_id:
                _logger.info(f'Company processor {data} headers:{headers}')
                retour = company_id.process_auth(data, headers)
        else:
            processor_id = request.env['salla.webhooks'].sudo().search(
                [('company_id', '=', cny), ('event.event', '=', event)], limit=1)
            if processor_id:
                retour = processor_id.sudo().process(data, headers)
        if retour and retour.get('status', False) != 200:
            error = {
                'code': 100,
                'message': retour.get('result', 'Internal Error'),
            }
            _logger.info(f'ERROR {error}')
        _logger.info(f'RETOURN {retour}')
        return result

    @http.route(['/oauth/callback/'], type='http', auth="public")
    def auth_webhook(self, **kw):
        # request._json_response = my_json_response.__get__(request, JsonRequest)
        state = kw.get('state')
        code = kw.get('code')
        company_id = request.env['res.company'].sudo()
        if state:
            company_id = request.env['res.company'].sudo().search([('salla_state', '=', state)])
        elif code:
            company_id = request.env['res.company'].sudo().search([('salla_auth_code', '=', code)])
        if not code and company_id:
            return request.redirect(company_id.install_salla_app())
        token = ''
        if company_id:
            company_id.sudo().write({'salla_auth_code': code})
            token = company_id.sudo().request_salla_token()
            if token:
                try:
                    company_id.sudo().get_merchant_profile()
                    company_id.sudo().action_subscribe_webhooks()
                except:
                    pass
        return request.redirect("/web")
