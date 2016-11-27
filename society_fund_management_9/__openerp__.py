# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
{
    'name': "society_fund_management_9",
    'description': """
Mandal Fund-Scheam including Loan Management
============================================
This Module will manage membership scheme where multiple people's contribute amounts and on the bases collected amount. 
The fund scheme offers with various loan plan.
Main Features
-------------
* Define scheme which is collecting recurrent amount of money.
* Allocate Loan with interest confiiguration (Fixed and Floating)
* for more detail you can refer following blog URL:https://docs.google.com/document/d/1COrlITqKvw83cXS9q2txQzuJi8GLH-00QNcJkJGPEgs/pub
""",
    'author': "VperfectCS",
    'website': "http://www.vperfectcs.com",
    'category': 'Accounting & Finance',
    'version': '0.1',
    'depends': ['base', 'account_accountant','analytic'],
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
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: