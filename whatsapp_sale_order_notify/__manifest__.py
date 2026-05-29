{
    'name': 'WhatsApp Notification on Sale Order Confirmation',
    'version': '1.0',
    'category': 'Sales',
    'summary': 'Send WhatsApp message when Sale Order is confirmed',
    'depends': ['sale',"base"],
    "author":'Aneesh Kumar',
    'data': [
    'views/views_sale_orders.xml',
    'views/views_res_config_settings.xml',
   
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
