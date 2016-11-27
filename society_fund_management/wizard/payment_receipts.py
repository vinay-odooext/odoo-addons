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

from openerp import api, fields, models
from openerp.exceptions import except_orm, Warning, RedirectWarning

class PaymentReceipts(models.TransientModel):
    _name = 'payment.receipts'
    _description = 'Payment Receipts'

    partner_id = fields.Many2one('res.partner', string='Partner', domain = [('customer','=',1),('supplier','=',1),('is_company','=',1)], required=True)
    period_ids = fields.Many2many('account.period', 'payment_period_rel', 'payment_id', 'period_id', string="Periods")
    header = fields.Boolean('Header', help="Check this If you want to table header.")
    front_page = fields.Boolean('Front Page Print', help="Check this If you want to Print passbook front Page.")

    @api.multi
    def print_fund(self):
        data = self.read()[0]
        datas = {
             'ids': [],
             'model': 'payment.receipts',
             'form': data
            }
        if data['front_page']:
            return self.env['report'].get_action(self, 'society_fund_management.report_front_page_member', data=datas)
        if not data['period_ids']:
            raise except_orm(('Period Missing'),('You have to assign period for payment receipt printing.'))
        return self.env['report'].get_action(self, 'society_fund_management.report_payment_receipts_fund', data=datas)
