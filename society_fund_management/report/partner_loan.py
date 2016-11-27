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

import time

from openerp.report import report_sxw
from openerp.osv import osv


class PartnerLoan(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(PartnerLoan, self).__init__(cr, uid, name, context=context)
        ids = context.get('active_ids')
        partner_obj = self.pool['res.partner']
        docs = partner_obj.browse(cr, uid, ids, context)

        addresses = self.pool['res.partner']._address_display(cr, uid, ids, None, None)
        self.localcontext.update({
            'docs': docs,
            'time': time,
            'getLoanLines': self._loan_lines_get,
            'addresses': addresses
        })
        self.context = context

    def _loan_lines_get(self, loan):
        lines = []
        lines.append({
            'name': loan.name,
            'loan_date': loan.date,
            'period_name': loan.period_id.name,
            'loan_duration': loan.loan_duration,
            'loan_amount': loan.loan_amount,
            'loan_int': loan.loan_int,
            'total_amount': loan.total_amount,
            'residual': loan.balance_paid,
        })
        return lines

class report_partner_loan(osv.AbstractModel):
    _name = 'report.society_fund_management.report_loan_partner'
    _inherit = 'report.abstract_report'
    _template = 'society_fund_management.report_loan_partner'
    _wrapped_report_class = PartnerLoan

class report_parner_loan_request(osv.AbstractModel):
    _name = 'report.society_fund_management.report_loan_request_form'
    _inherit = 'report.abstract_report'
    _template = 'society_fund_management.report_loan_request_form'
    _wrapped_report_class = PartnerLoan
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
