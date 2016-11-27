# -*- coding: utf-8 -*-
{
    'name': "society_fund_management",
    'description': """
Mandal Fund-Scheam including Loan Management
============================================
This Module will manage membership scheme where multiple people's contribute amounts and on the bases collected amount. 
The fund scheme offers with various loan plan.
Main Features
-------------
* Define scheme which is collecting recurrent amount of money.
* Allocate Loan with interest confiiguration (Fixed and Floating)
* for more detail you can refer following blog URL:
https://docs.google.com/document/d/e/2PACX-1vR-jM5okXetow4Emdx6Lf7UTQVSUvtqPuKHjefXpw_BSyf-pJTWC3EvcoE0BFiQxACNtoq2HJ4CyV7z/pub
""",
    'author': "VperfectCS",
    'website': "http://www.vperfectcs.com",
    'category': 'Accounting & Finance',
    'version': '0.1',
    'depends': ['base', 'account_voucher', 'account_accountant'],
    'data': [
        # 'security/ir.model.access.csv',
        'models_view.xml',
        'data.xml',
        'loan_sequence.xml',
        'views/paper_data.xml',
        'views/report_partner.xml',
        'views/report_partner_loan_request.xml',
        'views/report_payment_receipts.xml',
        'views/report_front_page.xml',
        'wizard/payment_receipts_view.xml',
    ],

}
