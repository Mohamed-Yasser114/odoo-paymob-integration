{
    'name': 'Paymob Payment Integration',
    'version': '19.0.1.0.0',
    'author': 'Mohamed Yasser',
    'depends' : ['base', 'payment', 'account', 'sale'],
    'data': [
        'views/payment_paymob_template.xml',
        'views/payment_provider_form.xml',
        'data/payment_provider_data.xml',
        'data/account_payment_method.xml'
    ],
    'installable': True,
}