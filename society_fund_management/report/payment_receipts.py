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
#   Monthly Fees (Scheme amount), Current scheme,Total scheme Paid, Loan Amount, Loan Intereset, (Penality Total Payment + Monthly Fees (Scheme amount) )
from openerp.report import report_sxw
from openerp.osv import osv
from datetime import datetime
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP



class PaymentReceipts(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(PaymentReceipts, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            'getPartner': self._partner_get,
            'getPaymentLines': self._payment_lines_get,
            'getHeader': self._header_get,
        })
        self.context = context

    def _header_get(self, form):
        return form['header']

    def _partner_get(self, data):
        partner_obj = self.pool.get('res.partner')
        partners = []
        if data['form'].get('partner_id'):
            partner = partner_obj.browse(self.cr, self.uid, data['form']['partner_id'][0])
            partners.append({'account_no':partner.account_no, 'display_name':partner.name,
            'phone':partner.phone, 'mobile':partner.mobile, 'street':partner.street, 'street2':partner.street2,
            'city':partner.city, 'zip':partner.zip, 'state_id':partner.state_id and partner.state_id.name or '',
            'country_id':partner.country_id.name
            })
        return partners

    def _payment_lines_get(self, form):
        account_voucher_obj = self.pool.get('account.voucher')
        partner_obj = self.pool.get('res.partner')
        period_obj = self.pool.get('account.period')
        res = []
        partner = partner_obj.browse(self.cr, self.uid, form['partner_id'][0])

        periods = period_obj.browse(self.cr, self.uid, form['period_ids'])
        voucher_ids = account_voucher_obj.search(self.cr, self.uid, [('partner_id', '=', form['partner_id'][0]), ('period_id', 'in', form['period_ids']), ('journal_id.type', 'in', ('bank', 'cash'))])
        fiscal_year_ids = []
        for f in partner.scheme_id.fiscal_year_ids:
            if f.id not in fiscal_year_ids:fiscal_year_ids.append(f.id)
        fis_period_ids = period_obj.search(self.cr, self.uid, [('fiscalyear_id', 'in', fiscal_year_ids), ('special', '=', False)])
        periods_another = period_obj.browse(self.cr, self.uid, fis_period_ids)
        BlankDict = {#'partner_name': '',
                    'date':'',
                    #'period_id':False,
                    'monthly_amt':'',
                    'count_current_scheme':'',
                    'count_emi_current':'',
                    'loan_amount':'',
                    'loan_emi':'',
                    #'loan_id':False,
                    'loan_remaining':'',
                    'monthly_int': '',
                    'total_panalty': '',
                    'paid_amount': '',
                    'printed': True,
                    'total_payment':'',
                }
        for period in periods_another:
            res.append({
                'partner_name': '',
                'date':'',
                'period_id':period.id,
                'monthly_amt':0.0,
                'count_current_scheme':0,
                'count_emi_current':0,
                'loan_amount': 0.0,
                'loan_emi': 0,
                'loan_id':False,
                'loan_remaining': 0.0,
                'monthly_int': 0.0,
                'total_panalty': 0.0,
                'paid_amount': 0.0,
                'printed': True,
                'total_payment':0.0,
            })
        ChangeLoanAmtList = []
        for period in periods:
            for voucher in account_voucher_obj.browse(self.cr, self.uid, voucher_ids):
                if voucher.period_id.id == period.id:
                    for r in res:
                         if r.has_key('period_id') and r['period_id'] == period.id:
                            r.update({
                                'partner_name': voucher.partner_id.name + ' ' +  '(' + voucher.partner_id.account_no + ')',
                                'date':datetime.strptime(voucher.date, '%Y-%m-%d').strftime('%d/%m/%Y'),
                                'monthly_amt': voucher.monthly_amt,
                                'count_current_scheme': voucher.count_scheme_current if voucher.count_scheme_current > 0 else 1,
                                'count_emi_current': voucher.loan_id and (voucher.count_emi_current if voucher.count_emi_current > 0 else 1) or 0,
                                'loan_amount': voucher.loan_id.loan_amount,
                                'loan_id':voucher.loan_id.id,
                                'loan_emi': voucher.loan_emi,
                                'loan_remaining': (voucher.loan_id.loan_amount - ((voucher.count_emi_current if voucher.count_emi_current > 0 else 1) * voucher.loan_emi)),
                                'monthly_int': voucher.monthly_int,
                                'total_panalty': voucher.total_panalty,
                                'paid_amount': voucher.amount,
                                'printed': False,
                                'total_payment': (voucher.total_payment + voucher.monthly_amt),
                            })
                            ChangeLoanAmtList.append(r)
        for ChangeLoanAmt in ChangeLoanAmtList:
            loan_id = ChangeLoanAmtList[ChangeLoanAmtList.index(ChangeLoanAmt) - 1]['loan_id']
            loan_amount = ChangeLoanAmtList[ChangeLoanAmtList.index(ChangeLoanAmt) - 1]['loan_amount']
            if ChangeLoanAmt['loan_id'] and ChangeLoanAmt['loan_amount']:
                if not loan_id and not loan_amount:
                    for r in res:
                        if r.has_key('period_id') and r['period_id'] == ChangeLoanAmt['period_id'] - 1:
                            r.update({'loan_amount':ChangeLoanAmt['loan_amount']})
                        elif r.has_key('loan_id') and r['loan_id'] == ChangeLoanAmt['loan_id'] or (r.has_key('loan_id') and not r['loan_id'] and not r['loan_amount']):
                            r.update({'loan_amount':0.0})

        counter,blankPosition = 0,0
        for r in res:
            if r['count_emi_current'] == 1 and r['loan_amount']:
                res[res.index(r)-1].update({'loan_amount':r['loan_amount']})
                r.update({'loan_amount':0.0})
            if r.has_key('loan_id') and r['loan_id'] and r['loan_amount']:r.update({'loan_amount':0.0})
            if counter == 0:
                if not form['header'] and counter == blankPosition:
                    print counter,'=0=',blankPosition
                    res.insert(blankPosition,BlankDict)
                elif not form['header'] and counter != blankPosition:
                    for bd in range(3):
                        res.insert(blankPosition,BlankDict)
                elif form['header'] and counter != blankPosition:
                    for bd in range(2):
                        res.insert(blankPosition,BlankDict)
            if counter == 11:counter = -1
            counter+=1
            blankPosition+=1
        return res

class report_payment_receipts(osv.AbstractModel):
    _name = 'report.society_fund_management.report_payment_receipts_fund'
    _inherit = 'report.abstract_report'
    _template = 'society_fund_management.report_payment_receipts_fund'
    _wrapped_report_class = PaymentReceipts

class report_payment_receiptsother(osv.AbstractModel):
    _name = 'report.society_fund_management.report_front_page_member'
    _inherit = 'report.abstract_report'
    _template = 'society_fund_management.report_front_page_member'
    _wrapped_report_class = PaymentReceipts


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
