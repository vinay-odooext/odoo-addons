# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2014-2015 ONNET SOLUTIONS SDN BHD.
#    Copyright (C) 2014-2015 OpenERP SA (<http://on.net.my/>)
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
    "name": "Sale Order Line Merged DO",
    "version": "1.0",
    "author": "VperfectCS",
    'category': 'Sale',
    "website": "http://www.vperfectcs.com",
    "description": """
Sale Order Lines Customization
==============================

This module allows you to manage your multiple different sale order lines merged with common Delivery order.

Main Features
-------------
* Confimed Quatation first.
* Merged multiple sale order lines groupby common customer and UOM.
* This will create common Delivery order for all those different sale orders.
""",
    'depends': ['sale_stock'],
    'data': [
        'wizard/merge_sol_do_view.xml',
        'views/sale_view.xml',
        'views/sale_workflow.xml',
    ],
    'installable': True,
}
