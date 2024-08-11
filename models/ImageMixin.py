from odoo import api, fields, models
import requests
import logging
import base64
_logger = logging.getLogger(__name__)


def get_image_from_url(url):
    """
    :return: Returns a base64 encoded string.
    """
    data = ""
    try:
        data = base64.b64encode(requests.get(url.strip()).content).replace(b"\n", b"")
    except Exception as e:
        _logger.warning("Can’t load the image from URL %s" % url)
        logging.exception(e)
    return data