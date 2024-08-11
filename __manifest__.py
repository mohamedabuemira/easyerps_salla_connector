{
    'name': "Odoo Salla Connector",
    'support': "support@easyerps.com",
    'license': "OPL-1",
    # 'price': 130,
    # 'currency': "USD",
    'summary': """
        Odoo Salla Integration
        """,
    'author': "EasyERPS",
    'website': "https://www.easyerps.com/knowledge/article/8",
    'category': 'Sale',
    'version': '16.1.2',
    
    'depends': [
        'sale_management','delivery','stock','base_automation','bus'
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/group.xml',
        'data/salla.event.list.csv',
        'data/branch_cron.xml',
        'data/base_cron.xml',
        'data/partner_cron.xml',
        'data/product_cron.xml',
        'data/product_brand.xml',
        'data/filter_type.xml',
        'data/misc_fields.xml',
        'data/coupon_payment_methods.xml',
        'views/product_template_views.xml',
        'views/product_options_views.xml',
        'views/product_categpry_views.xml',
        'views/account_tax_views.xml',
        'views/branch_views.xml',
        'views/webhooks_views.xml',
        'views/product_brand_views.xml',
        'views/sale_order_views.xml',
        'views/res_company_views.xml',
        'views/res_partner_views.xml',
        'views/tags.xml',
        'views/payment_views.xml',
        'views/shipping_companies_views.xml',
        'views/shipping_rules_views.xml',
        'views/shipping_zones_views.xml',
        'views/customer_groups_views.xml',
        'views/sale_order_status_views.xml',
        'views/affiliate_views.xml',
        'views/advertisement_views.xml',
        'views/coupon_views.xml',
        'views/offers_views.xml',
        'wizard/fetch_filter_wizard_views.xml',
        'wizard/pull_filter_wizard_views.xml',
        'wizard/salla_sync_wizard_views.xml',
        'wizard/result_wizard_views.xml',
        'wizard/sale_status_update_wizard_views.xml',
        'wizard/shipment_update_wizard_views.xml',
        'views/salla_dashborad_views.xml',
        'views/salla_menu.xml'
    ],
    'auto_install': False,
    'application': False,
    'assets': {
        'web.assets_backend':[
            #'easyerps_salla_connector/static/src/js/many_tags_link.js'
            'easyerps_salla_connector/static/src/js/backend_notifier.js'
        ]
    },
    # 'external_dependencies':{'python':['authlib==0.15.1']},
    'images': ['images/main_screenshot.png'],

}