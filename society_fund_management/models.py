# -*- coding: utf-8 -*-
import time
from dateutil.relativedelta import relativedelta
from datetime import datetime

from openerp import models, fields, api
from openerp.exceptions import except_orm, Warning, RedirectWarning
from openerp.tools.translate import _

class res_partner(models.Model):
    _name = 'res.partner'
    _inherit = 'res.partner'
    _description = 'Lavasa Fund Registration'

    scheme_id = fields.Many2one('fund.scheme', string='Fund scheme', copy=False)
    loan_lines = fields.One2many('fund.loan', 'partner_id', string='Alloted Loan', copy=False)
    account_no = fields.Char(string='Account No', copy=False, readonly=True, index=True, default='New')
    is_company = fields.Boolean('Is a Company', help="Check if the contact is a company, otherwise it is a person", default=True)
    customer  = fields.Boolean('Customer', help="Check this box if this contact is a customer.", default=True)
    supplier = fields.Boolean('Supplier', help="Check this box if this contact is a supplier. If it's not checked, purchase people will not see it when encoding a purchase order.", default=True)


    @api.model
    def create(self, vals):
        if vals.get('account_no', 'New') == 'New':
            vals['account_no'] = self.env['ir.sequence'].next_by_code('res.partner.member') or 'New'
        result = super(res_partner, self).create(vals)
        return result

    @api.multi
    def name_get(self):
        result = []
        for record in self:
            if record.name and record.account_no:
                result.append((record.id,'[' + record.account_no + '] ' + record.name))
            if record.name and not record.account_no:
                result.append((record.id, record.name))
        return result

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        recs = self.browse()
        if name:
            recs = self.search(['|',('name', '=', name),('account_no','=',name)] + args, limit=limit)
        if not recs:
            recs = self.search([('name', operator, name)] + args, limit=limit)
        return recs.name_get()


class fund_scheme(models.Model):
    _name = 'fund.scheme'
    _description = 'Fund scheme'

    name = fields.Char(string='Welfare Plan', required=True)
   # fiscal_year_id = fields.Many2one('account.fiscalyear', string='Welfare Plan Year', ondelete='cascade', index=True, required=True)
    fiscal_year_ids = fields.Many2many('account.fiscalyear', 'account_scheme_rel', 'fiscal_year_id', 'scheme_id', string="Welfare Plan Years", copy=False,required=True)
    due_day = fields.Float(string='Monthly Due Day', digits=(16, 2), default=10.0, required=True)
    duration = fields.Integer(string='Scheme Duration', default=12, required=True)
    mem_fees = fields.Float(string='Membership Fees', digits=(16, 2), default=3600.0, required=True)
    month_amt = fields.Float(string='Monthly Fees', digits=(16, 2), store=True, compute='_compute_amount')

    @api.depends('mem_fees', 'duration')
    def _compute_amount(self):
        for record in self:
            record.month_amt = round(record.mem_fees / record.duration,2)

class account_fiscalyear(models.Model):
    _name = 'account.fiscalyear'
    _inherit = 'account.fiscalyear'
    _description = "Fiscal Year"

    scheme_id = fields.Many2one('fund.scheme', string='Scheme', index=True)

class account_move_line(models.Model):
    _name = 'account.move.line'
    _inherit = 'account.move.line'
    _description = "Journal Items"

    loan_id = fields.Many2one('fund.loan', string='Loan', index=True)

class fund_loan(models.Model):
    _name = 'fund.loan'
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _description = 'Fund Loan'

    def _default_loan_journal_methods(self):
        return self.env.ref('society_fund_management.account_loan_journal')

    def _default_loan_account_methods(self):
        return self.env.ref('society_fund_management.account_loan_account')

    name = fields.Char(string='Number', required=True, copy=False, readonly=True, index=True, default='New')
    partner_id = fields.Many2one('res.partner', string='Member', ondelete='cascade', index=True, required=True)
    guarantor_ids = fields.Many2many('res.partner', 'loan_guaranter_rel', 'partner_id', 'loan_id', string="Guarantors", copy=False)
    journal_id = fields.Many2one('account.journal', 'Loan Journal', required=True, default=lambda self: self._default_loan_journal_methods())
    period_id = fields.Many2one('account.period', 'Confirm Month', required=True)
    account_id = fields.Many2one('account.account', 'Loan Account', required=True, domain="[('type','=','other')]", default=lambda self: self._default_loan_account_methods())
    move_id = fields.Many2one('account.move', string='Journal Entry', readonly=True, copy=False, help="Link to the automatically generated Journal Items.")
    int_type = fields.Selection([('floating','Floating Rate'), ('fixed','Fixed Percentage')], string='Interest Type', default='fixed', help="The computation method for interest amount calculation.")
    date = fields.Date(string='Date', copy=False, required=True)
    loan_duration = fields.Integer(string='Duration', default=10)
    loan_amount = fields.Float(string='Loan Amount', digits=(16, 2), default=50000.0)
    loan_int = fields.Float(string='Monthly Interest(%)', digits=(16, 2), store=True, compute='_compute_emi')
    yearly_loan_int = fields.Float(string='Annual Interest(%)', digits=(16, 2), default=9.6)
    total_amount = fields.Float(string='Total', digits=(16, 2), store=True, readonly=True, compute='_compute_emi')
    loan_emi = fields.Float(string='L.EMI (Without Interest)', digits=(16, 2), store=True, compute='_compute_emi')
    int_amt = fields.Float(string='Int. Amt.', digits=(16, 2), store=True, compute='_compute_emi')
    count_emi_paid = fields.Integer(string='Total EMI Paid', store=True, compute='_count_emi_status')
    count_emi_current = fields.Integer(string='Current EMI', store=True, compute='_count_emi_status')
    balance_paid = fields.Float(string='Paid', store=True, compute='_balance_status')
    remaining_amount = fields.Float(string='Remaining', digits=(16, 2), store=True, compute='_compute_emi')
    state = fields.Selection([
            ('draft','Draft'),
            ('open','Open'),
            ('paid','Paid'),
            ('cancel','Cancelled'),
        ], string='Status', index=True, readonly=True, default='draft',
        track_visibility='onchange', copy=False)


    @api.multi
    def onchange_date(self, date):
        period_obj = self.env['account.period']
        return {'value':{'period_id' : period_obj.find(date).id}}

    @api.depends('move_id','partner_id')
    def _balance_status(self):
        for record in self:
            residual = 0.0
            if record.move_id:
                for line in record.move_id.line_id:
                    if line.reconcile_id:
                        residual += line.debit
            journal_interest = self.env.ref('society_fund_management.account_panalyty_interest_journal')
            account_ml = self.env['account.move.line'].search([('loan_id','=',record.id),('journal_id','=',journal_interest.id),('account_id','=',record.partner_id.property_account_receivable.id)])
            for ml in account_ml:
                if ml.reconcile_id:
                    residual += ml.debit
            record.balance_paid = residual

    @api.depends('partner_id', 'period_id', 'loan_emi')
    def _count_emi_status(self):
        for record in self:
            reconcile = 0
            if record.move_id:
                for line in record.move_id.line_id:
                    if line.reconcile_id:
                        reconcile += 1
            record.count_emi_paid = reconcile
            if reconcile != record.loan_duration:
                record.count_emi_current = reconcile + 1

    @api.depends('loan_duration', 'loan_amount','loan_int','int_amt','int_type','balance_paid','yearly_loan_int')
    def _compute_emi(self):
        for record in self:
            record.loan_int = round(record.yearly_loan_int/12,2)
            if record.int_type == 'fixed':
                record.total_amount = record.loan_amount + (record.loan_amount * (record.yearly_loan_int/100))
                record.loan_emi =  record.loan_amount / record.loan_duration
    	        record.int_amt = record.loan_amount * (record.yearly_loan_int/100)
                record.remaining_amount = record.total_amount - record.balance_paid
            else:
                passed_amount = record.loan_amount - record.balance_paid
                record.loan_emi =  record.loan_amount / record.loan_duration
                interest_tatal = 0.0
                initial_amt = record.loan_amount
                for count in range(0,record.loan_duration):
                    interest_tatal += (initial_amt * (record.loan_int/100))
                    initial_amt -= record.loan_emi
                    count += 1
                record.int_amt = interest_tatal
                record.total_amount = record.loan_amount + interest_tatal
                record.remaining_amount = record.total_amount - record.balance_paid

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('fund.loan') or 'New'
        result = super(fund_loan, self).create(vals)
        return result

    @api.multi
    def action_cancel(self):
        for record in self:
            if record.state == 'open':
                record.move_id.unlink()
                record.write({'state':'cancel'})

    @api.multi
    def action_cancel_draft(self):
        # go from canceled state to draft state
        self.write({'state': 'draft'})
        return True

    @api.multi
    def action_validate(self):
        account_move = self.env['account.move']
        for record in self:
            if record.state == 'draft':
                move_id = account_move.create({'name': record.name, 'date':record.date, 'period_id' : record.period_id.id, 'journal_id' : record.journal_id.id})
                lines = []
                cr_line_dict = {
                    'name': 'To Loan Account:',
                    'move_id':move_id.id,
                    'account_id': record.account_id.id,
                    'credit': record.loan_amount,
                    'partner_id': record.partner_id.id,
                    'date_created': record.date,
                }
                lines.append((0,0,cr_line_dict))
                end = int(record.loan_duration) + 1
                for i in range(1, end):
                    date_maturity = datetime.strptime(record.date, '%Y-%m-%d').date()
                    date_maturity = (date_maturity + relativedelta(months=i)).strftime('%Y-%m-%d')
                    dr_line_dict = {
                        'name': record.name+':'+'Member',
                        'move_id':move_id.id,
                        'loan_id':record.id,
                        'account_id': record.partner_id.property_account_receivable.id,
                        'debit': round((record.loan_amount / int(record.loan_duration)),2),
                        'partner_id': record.partner_id.id,
                        'date_created': record.date,
                        'date_maturity': date_maturity,
                    }
                    lines.append((0,0,dr_line_dict))
                move_id.write({'line_id': lines})
                record.write({'state': 'open','move_id':move_id.id})

class fund_payment(models.Model):
    _inherit = 'account.voucher'
    _description = 'Lavasa Fund Payment'

    def _default_scheme_journal_methods(self):
        return self.env.ref('society_fund_management.account_scheme_journal')

    def _default_panalty_interest_journal_methods(self):
        return self.env.ref('society_fund_management.account_panalyty_interest_journal')

    def _default_scheme_account_methods(self):
        return self.env.ref('society_fund_management.account_scheme_account')

    def _default_panalty_account_methods(self):
        return self.env.ref('society_fund_management.account_panalty_account')

    def _default_interest_account_methods(self):
        return self.env.ref('society_fund_management.account_interest_account')

    def _default_analytic_journal_methods(self):
        return self.env.ref('society_fund_management.fund_analytic_journal_income')

    def _default_analytic_interest_methods(self):
        return self.env.ref('society_fund_management.analytic_interest_society')

    def _default_analytic_panalty_methods(self):
        return self.env.ref('society_fund_management.analytic_panalty_society')

    scheme_id = fields.Many2one(related='partner_id.scheme_id', store=True, readonly=True, copy=False)
    scheme_journal_id = fields.Many2one('account.journal', 'scheme Journal', domain="[('type','=','purchase')]", default=lambda self: self._default_scheme_journal_methods())
    panalty_int_journal_id = fields.Many2one('account.journal', 'Panalty/Interest Journal', domain="[('type','=','sale')]", default=lambda self: self._default_panalty_interest_journal_methods())
    scheme_account_id = fields.Many2one('account.account', 'scheme Account', domain="[('type','=','other')]", default=lambda self: self._default_scheme_account_methods())
    analytic_journal_id = fields.Many2one('account.analytic.journal', string='Analytic Journal', default=lambda self: self._default_analytic_journal_methods())
    analytic_id = fields.Many2one('account.analytic.account', 'Interest Costing', domain="[('type','=','normal')]", default=lambda self: self._default_analytic_interest_methods(), readonly=True, states={'draft':[('readonly',False)],'scheme':[('readonly',False)]})
    analytic_panalty_id = fields.Many2one('account.analytic.account', 'Panalty Costing', domain="[('type','=','normal')]", default=lambda self: self._default_analytic_panalty_methods(), readonly=True, states={'draft':[('readonly',False)],'scheme':[('readonly',False)]})
    count_scheme_paid = fields.Integer(string='Total scheme Paid', store=True, compute='_count_scheme')
    count_scheme_current = fields.Integer(string='Current scheme', store=True, compute='_count_scheme')
    loan_id = fields.Many2one('fund.loan', string="Loan", store=True, compute='_get_loan')
    panalty = fields.Float(string='Panelty', digits=(16, 2), default=0.0, readonly=True, states={'draft':[('readonly',False)]})
    panalty_extra = fields.Float(string='Panelty Extra', digits=(16, 2), default=0.0, readonly=True, states={'draft':[('readonly',False)]})
    total_panalty = fields.Float(string='Panelty', digits=(16, 2), store=True, compute='_compute_panalty')
    panalty_account_id = fields.Many2one('account.account', 'Panalty Account', domain="[('type','=','other')]", default=lambda self: self._default_panalty_account_methods())
    interest_account_id = fields.Many2one('account.account', 'Interest Account', domain="[('type','=','other')]", default=lambda self: self._default_interest_account_methods())
    loan_emi = fields.Float(related='loan_id.loan_emi', store=True, readonly=True, copy=False)
    count_emi_paid = fields.Integer(related='loan_id.count_emi_paid', store=True, readonly=True, copy=False)
    balance_paid = fields.Float(related='loan_id.balance_paid', store=True, readonly=True, copy=False)
    count_emi_current = fields.Integer(related='loan_id.count_emi_current', store=True, readonly=True, copy=False)
    monthly_amt = fields.Float(related='scheme_id.month_amt', store=True, readonly=True, copy=False)
    monthly_int = fields.Float(string='Interest', digits=(16, 2), store=True, compute='_monthly_interest')
    total_payment = fields.Float(string='T.Payment(Without Scheme Amt.)', digits=(16, 2), store=True, compute='_compute_payment')
    total_all = fields.Float(string='Total', digits=(16, 2), store=True, compute='_compute_payment')
    amount = fields.Float(string='Total', digits=(16, 2), required=True, readonly=True, states={'draft':[('readonly',False)],'scheme':[('readonly',False)]})
    line_cr_ids = fields.One2many('account.voucher.line', 'voucher_id', string='Credits', domain=[('type','=','cr')], context={'default_type':'cr'}, readonly=True, states={'draft':[('readonly',False)], 'scheme':[('readonly',False)]})
    line_dr_ids = fields.One2many('account.voucher.line', 'voucher_id', string='Debits', domain=[('type','=','dr')], context={'default_type':'dr'}, readonly=True, states={'draft':[('readonly',False)], 'scheme':[('readonly',False)]})
    state = fields.Selection(
            [('draft', 'Draft'),
             ('cancel', 'Cancelled'),
             ('proforma', 'Pro-forma'),
             ('scheme', 'Scheme'),
             ('posted', 'Posted')
            ], 'Status', readonly=True, track_visibility='onchange', copy=False, default='draft',
            help=" * The 'Draft' status is used when a user is encoding a new and unconfirmed Voucher.\n"
                 " * The 'Pro-forma' status is used when the voucher does not have a voucher number.\n"
                 " * The 'Scheme-done' status is used when the scheme entry happened.\n"
                 " * The 'Panalty/Interest-done' status is used when the Panalty/Interest entry happened.\n"
                 " * The 'Posted' status is used when user create voucher,a voucher number is generated and voucher entries are created in account.\n"
                 " * The 'Cancelled' status is used when user cancel voucher.")
    printed = fields.Boolean(string='Printed')

    @api.constrains('panalty')
    def _check_panalty(self):
        for record in self:
            if record.panalty == 0.0 and record.partner_id.scheme_id:
                day = record.scheme_id.due_day
                date_payment = datetime.strptime(record.date, "%Y-%m-%d")
                if date_payment.day > day:
                    raise except_orm(_('Panalty Applied'),_('You have exceeded the normal date cycle, Panalty amount should be passed.'))

    @api.constrains('period_id')
    def _check_period_scheme(self):
        period_ids = []
        for record in self:
            for f in record.scheme_id.fiscal_year_ids:
                for p in f.period_ids:
                    if p.id not in period_ids:period_ids.append(p.id)
            if record.period_id.id not in period_ids and record.partner_id.scheme_id:
                raise except_orm(_('Wrong period selected'),_('You need to choose right period for assigned Fiscal Year "{}" for assigned memeber scheme {}.'.format(record.period_id.fiscalyear_id.name,record.scheme_id.name)))

    @api.depends('partner_id','scheme_id')
    def _count_scheme(self):
        account_move_line_obj = self.env['account.move.line']
        period_ids = []
        for record in self:
            for f in record.scheme_id.fiscal_year_ids:
                for p in f.period_ids:
                    if p.id not in period_ids:period_ids.append(p.id)
            scheme_account_id = record.env.ref('society_fund_management.account_scheme_account').id
            domain = [('move_id.name','=',record.scheme_id.name),('partner_id','=',record.partner_id.id),('debit','=',record.scheme_id.month_amt), ('period_id','in',period_ids),('account_id','=',scheme_account_id)]
            total_move_line_ids = account_move_line_obj.search(domain)
            record.count_scheme_paid = len(total_move_line_ids)
            record.count_scheme_current = record.count_scheme_paid
            if record.count_scheme_paid > 0:
                record.count_scheme_current = record.count_scheme_paid + 1

    @api.depends('partner_id')
    def _get_loan(self):
        fund_loan = self.env['fund.loan']
        for record in self:
            record.loan_id = False
            if record.partner_id:
                loan_id = fund_loan.search([('partner_id','=',record.partner_id.id),('state','=','open')], limit=1)
                if loan_id:
                    record.loan_id = loan_id.id

    @api.depends('panalty', 'panalty_extra')
    def _compute_panalty(self):
        for record in self:
            record.total_panalty =  record.panalty + record.panalty_extra

    @api.depends('loan_id.total_amount', 'loan_id.loan_amount', 'loan_id.loan_duration')
    def _monthly_interest(self):
        for record in self:
            if record.loan_id:
                total_interest = record.loan_id.total_amount - record.loan_id.loan_amount
                record.monthly_int = round((total_interest / record.loan_id.loan_duration),2)

    @api.depends('panalty', 'panalty_extra','loan_emi','monthly_amt')
    def _compute_payment(self):
        for record in self:
            record.total_payment =  record.panalty + record.panalty_extra + record.monthly_int + record.loan_emi
            record.total_all =  record.total_payment + record.monthly_amt

    @api.multi
    def action_validate_scheme(self):
        account_move = self.env['account.move']
        for record in self:
            if self.search([('period_id','=',record.period_id.id),('partner_id','=',record.partner_id.id),('state','in',['scheme','posted'])]):
                raise except_orm(_('Already Paid..!!!'),_('Already paid for month "{}" for member {}.'.format(record.period_id.name,record.partner_id.name)))
            if record.scheme_id:
                move_id = account_move.create({'name': record.scheme_id.name, 'date':record.date, 'period_id' : record.period_id.id, 'journal_id' : record.scheme_journal_id.id})
                dr_line_dict = {
                    'name': record.partner_id.name+':'+'Member',
                    'move_id':move_id,
                    'account_id': record.partner_id.property_account_payable.id,
                    'credit': record.scheme_id.month_amt,
                    'partner_id': record.partner_id.id,
                    'date_created': record.date,
                }
                cr_line_dict = {
                    'name': 'To scheme Account:',
                    'move_id':move_id,
                    'account_id': record.scheme_account_id.id,
                    'debit': record.scheme_id.month_amt,
                    'partner_id': record.partner_id.id,
                    'date_created': record.date,
                }
                move_id.write({'line_id':[(0,0,dr_line_dict),(0,0,cr_line_dict)]})
            if record.loan_id:
                Interest_move_id = account_move.create({'name': 'Interest Entry Move', 'date':record.date, 'period_id' : record.period_id.id, 'journal_id' : record.panalty_int_journal_id.id})
                dr_line_dict = {
                    'name': record.partner_id.name+':'+'Member',
                    'account_id': record.partner_id.property_account_receivable.id,
                    'debit': record.monthly_int,
                    'loan_id':record.loan_id.id,
                    'partner_id': record.partner_id.id,
                    'date_created': record.date,
                }
                cr_line_dict = {
                    'name': 'To Interest Account:',
                    'account_id': record.interest_account_id.id,
                    'credit': record.monthly_int,
                    'partner_id': record.partner_id.id,
                    'analytic_account_id':record.analytic_id.id,
                    'date_created': record.date,
                }
                Interest_move_id.write({'line_id':[(0,0,dr_line_dict),(0,0,cr_line_dict)]})
                record.loan_id._balance_status()
            if record.total_panalty > 0:
                Panalty_move_id = account_move.create({'name': 'Panalty Entry Move', 'date':record.date, 'period_id' : record.period_id.id, 'journal_id' : record.panalty_int_journal_id.id})
                dr_line_dict = {
                    'name': record.partner_id.name+':'+'Member',
                    'account_id': record.partner_id.property_account_receivable.id,
                    'debit': record.total_panalty,
                    'partner_id': record.partner_id.id,
                    'date_created': record.date,
                }
                cr_line_dict = {
                    'name': 'To Panalty Account:',
                    'account_id': record.panalty_account_id.id,
                    'credit': record.total_panalty,
                    'partner_id': record.partner_id.id,
                    'analytic_account_id':record.analytic_panalty_id.id,
                    'date_created': record.date,
                }
                Panalty_move_id.write({'line_id':[(0,0,dr_line_dict),(0,0,cr_line_dict)]})
            record.write({'state':'scheme'})

##    @api.multi
##    def action_validate_panalty_interest(self):
##        account_move = self.env['account.move']
##        for record in self:
##            if record.loan_id:
##                Interest_move_id = account_move.create({'name': 'Interest Entry Move', 'date':record.date, 'period_id' : record.period_id.id, 'journal_id' : record.panalty_int_journal_id.id})
##                dr_line_dict = {
##                    'name': record.partner_id.name+':'+'Member',
##                    'account_id': record.partner_id.property_account_receivable.id,
##                    'debit': record.monthly_int,
##                    'loan_id':record.loan_id.id,
##                    'partner_id': record.partner_id.id,
##                    'date_created': record.date,
##                }
##                cr_line_dict = {
##                    'name': 'To Interest Account:',
##                    'account_id': record.interest_account_id.id,
##                    'credit': record.monthly_int,
##                    'partner_id': record.partner_id.id,
##                    'analytic_account_id':record.analytic_id.id,
##                    'date_created': record.date,
##                }
##                Interest_move_id.write({'line_id':[(0,0,dr_line_dict),(0,0,cr_line_dict)]})
##                record.loan_id._balance_status()
##            if record.total_panalty > 0:
##                Panalty_move_id = account_move.create({'name': 'Panalty Entry Move', 'date':record.date, 'period_id' : record.period_id.id, 'journal_id' : record.panalty_int_journal_id.id})
##                dr_line_dict = {
##                    'name': record.partner_id.name+':'+'Member',
##                    'account_id': record.partner_id.property_account_receivable.id,
##                    'debit': record.total_panalty,
##                    'partner_id': record.partner_id.id,
##                    'date_created': record.date,
##                }
##                cr_line_dict = {
##                    'name': 'To Panalty Account:',
##                    'account_id': record.panalty_account_id.id,
##                    'credit': record.total_panalty,
##                    'partner_id': record.partner_id.id,
##                    'analytic_account_id':record.analytic_panalty_id.id,
##                    'date_created': record.date,
##                }
##                Panalty_move_id.write({'line_id':[(0,0,dr_line_dict),(0,0,cr_line_dict)]})
##            record.write({'state':'other'})

    @api.multi
    def proforma_voucher(self):
        result = super(fund_payment, self).proforma_voucher()
        for record in self:
            if record.loan_id:
                if record.move_id:
                    for line in record.move_id.line_id:
                        if line.account_id.id == record.partner_id.property_account_receivable.id:
                            line.write({'loan_id':record.loan_id.id})
                record.loan_id._balance_status()
                if record.loan_id.balance_paid == record.loan_id.total_amount:
                    record.loan_id.write({'state':'paid'})
        return result

    @api.multi
    def onchange_partner_id(self, partner_id, journal_id, amount, currency_id, ttype, date):
        result = super(fund_payment, self).onchange_partner_id(partner_id, journal_id, amount, currency_id, ttype, date)
        if result['value'] and result['value'].has_key('line_cr_ids') and result['value']['line_cr_ids']:
            ans_l = []
            min_date = min(item['date_due'] for item in result['value']['line_cr_ids'])
            for line in result['value']['line_cr_ids']:
                if line['date_due'] == min_date:
                    ans_l.append(line)
                result['value']['line_cr_ids'] = ans_l
        return result

    @api.multi
    def onchange_amount(self, amount, rate, partner_id, journal_id, currency_id, ttype, date, payment_rate_currency_id, company_id):
        result = super(fund_payment, self).onchange_amount(amount, rate, partner_id, journal_id, currency_id, ttype, date, payment_rate_currency_id, company_id)
        if result['value'] and result['value']['line_cr_ids']:
            temp = result['value']['line_cr_ids']
            l1 = temp[0]
            ans_l = []
            checking_l = []
            FalseDateDueList = [item for item in temp if type(item) != tuple and not item['date_due']]
            TrueDateDueList = [item for item in temp if type(item) != tuple and item['date_due']]
            TempData = TrueDateDueList + FalseDateDueList
            for item in TempData:
                if item == l1:
                    if not item['date_due']:
                        item['date_due'] = date
                        checking_l.append(item)
                    continue
                checking_l.append(item)
            min_date = min(item['date_due'] for item in checking_l if item['date_due'])
            for line in checking_l:
                if (line['date_due'] == min_date) or not line['date_due']:
                    if not line.has_key('reconcile'):
                        line['reconcile']=True
                        line['amount']=line['amount_unreconciled']
                    ans_l.append(line)
            result['value']['line_cr_ids'] = ans_l
        return result

class profit_sharing(models.Model):
    _name = 'profit.sharing'
    _description = 'Fund scheme Profit Sharing'

    def _default_ps_journal_methods(self):
        return self.env.ref('society_fund_management.account_ps_journal')

    def _default_panalty_account_methods(self):
        return self.env.ref('society_fund_management.account_panalty_account')

    def _default_interest_account_methods(self):
        return self.env.ref('society_fund_management.account_interest_account')

    name = fields.Char(string='Welfare Profit Sharing', required=True)
    date = fields.Date(string='Date', copy=False, required=True)
    period_id = fields.Many2one('account.period', 'Welfare Sharing Month', required=True)
    partner_ids = fields.Many2many('res.partner', 'parner_sharing_rel', 'partner_id', 'sharing_id', string="Members", copy=False)
    journal_id = fields.Many2one('account.journal', 'Sharing Journal', domain="[('type','=','purchase')]", default=lambda self: self._default_ps_journal_methods())
    interest_account_id = fields.Many2one('account.account', 'Interest Sharing Account', domain="[('type','=','other')]", required=True, default=lambda self: self._default_interest_account_methods())
    panalty_account_id = fields.Many2one('account.account', 'Panalty Sharing Account', domain="[('type','=','other')]", required=True, default=lambda self: self._default_panalty_account_methods())
    move_ids = fields.Many2many('account.move', 'profit_move_rel', 'sharing_id', 'move_id', string="Account Moves", copy=False)
    balance = fields.Float(string='Sharing Balance', digits=(16, 2), store=True, compute='_compute_balance')
    tatal_int_amt = fields.Float(string='Sharing Interest Amount', digits=(16, 2), store=True, compute='_compute_payment')
    tatal_pan_amt = fields.Float(string='Sharing Panalty Amount', digits=(16, 2), store=True, compute='_compute_payment')
    state = fields.Selection([
            ('draft','Draft'),
            ('paid','Paid'),
            ('cancel','Cancelled'),
        ], string='Status', index=True, readonly=True, default='draft',
        track_visibility='onchange', copy=False)

    @api.depends('interest_account_id','panalty_account_id')
    def _compute_balance(self):
        for record in self:
            if record.interest_account_id and record.panalty_account_id:
                record.balance = abs(record.interest_account_id.balance) + abs(record.panalty_account_id.balance)

    @api.depends('balance','partner_ids')
    def _compute_payment(self):
        for record in self:
            if record.partner_ids and record.interest_account_id and record.panalty_account_id:
                record.tatal_int_amt = round(abs(record.interest_account_id.balance)/len(record.partner_ids),2)
                record.tatal_pan_amt = round(abs(record.panalty_account_id.balance)/len(record.partner_ids),2)

    @api.multi
    def action_validate(self):
        account_move = self.env['account.move']
        for record in self:
            if not record.move_ids and record.partner_ids and record.interest_account_id and record.panalty_account_id:
                moves_l = []
                for partner in record.partner_ids:
                    move_id = account_move.create({'name': record.name, 'date':record.date, 'period_id' : record.period_id.id, 'journal_id' : record.journal_id.id})
                    cr_line_dict = {
                        'name': partner.name+':'+'Member',
                        'account_id': partner.property_account_payable.id,
                        'credit': record.tatal_int_amt + record.tatal_pan_amt,
                        'partner_id': partner.id,
                        'date_created': record.date,
                    }
                    dr_line_dict_1 = {
                        'name': 'To Sharing Interest Account:',
                        'account_id': record.interest_account_id.id,
                        'debit': record.tatal_int_amt,
                        'partner_id': partner.id,
                        'date_created': record.date,
                    }
                    dr_line_dict_2 = {
                        'name': 'To Sharing Panalty Account:',
                        'account_id': record.panalty_account_id.id,
                        'debit': record.tatal_pan_amt,
                        'partner_id': partner.id,
                        'date_created': record.date,
                    }
                    move_id.write({'line_id':[(0,0,cr_line_dict),(0,0,dr_line_dict_1),(0,0,dr_line_dict_2)]})
                    moves_l.append(move_id.id)
                record.write({'state':'paid','move_ids':[(6,0,moves_l)]})

    @api.multi
    def action_cancel(self):
        for record in self:
            if record.state == 'paid':
                record.move_ids.unlink()
                record.write({'state':'cancel'})

    @api.multi
    def action_cancel_draft(self):
        # go from canceled state to draft state
        return self.write({'state': 'draft'})
