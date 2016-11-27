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
    _description = 'Scheme Fund Registration'

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
    start_date = fields.Date(string='Start Date', index=True, copy=False, required=True)
    end_date = fields.Date(string='End Date', index=True, copy=False, required=True)
    due_day = fields.Float(string='Monthly Due Day', digits=(16, 2), default=10.0, required=True)
    duration = fields.Integer(string='Scheme Duration', default=12, required=True)
    mem_fees = fields.Float(string='Membership Fees', digits=(16, 2), default=3600.0, required=True)
    month_amt = fields.Float(string='Monthly Fees', digits=(16, 2), store=True, compute='_compute_amount')

    @api.depends('mem_fees', 'duration')
    def _compute_amount(self):
        for record in self:
            record.month_amt = round(record.mem_fees / record.duration,2)

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
        return self.env.ref('society_fund_management_9.account_loan_journal')

    def _default_loan_account_methods(self):
        return self.env.ref('society_fund_management_9.account_loan_account')

    name = fields.Char(string='Number', required=True, copy=False, readonly=True, index=True, default='New')
    partner_id = fields.Many2one('res.partner', string='Member', ondelete='cascade', index=True, required=True)
    guarantor_ids = fields.Many2many('res.partner', 'loan_guaranter_rel', 'partner_id', 'loan_id', string="Guarantors", copy=False)
    journal_id = fields.Many2one('account.journal', 'Loan Journal', required=True, default=lambda self: self._default_loan_journal_methods())
    account_id = fields.Many2one('account.account', 'Loan Account', required=True, domain="[('internal_type','=','other')]", default=lambda self: self._default_loan_account_methods())
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

    @api.depends('move_id','partner_id')
    def _balance_status(self):
        for record in self:
            residual = 0.0
            if record.move_id:
                for line in record.move_id.line_ids:
                    if line.reconciled:
                        residual += line.debit
            journal_interest = self.env.ref('society_fund_management_9.account_panalyty_interest_journal')
            account_ml = self.env['account.move.line'].search([('loan_id','=',record.id),('journal_id','=',journal_interest.id),('account_id','=',record.partner_id.property_account_receivable_id.id)])
            for ml in account_ml:
                if ml.reconciled:
                    residual += ml.debit
            record.balance_paid = residual

    @api.depends('partner_id', 'loan_emi')
    def _count_emi_status(self):
        for record in self:
            reconcile = 0
            if record.move_id:
                for line in record.move_id.line_ids:
                    if line.reconciled:
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
                record.loan_emi =  passed_amount / (record.loan_duration - record.count_emi_paid)
                interest_total = 0.0
                initial_amt = passed_amount
                for count in range(0,(record.loan_duration - record.count_emi_paid)):
                    interest_total += (initial_amt * (record.loan_int/100))
                    if initial_amt > record.loan_emi:
                        initial_amt -= record.loan_emi
                    else:
                        initial_amt = 0.0
                        break
                    count += 1
                record.int_amt = interest_total
                record.total_amount = record.loan_amount + interest_total
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
                move_id = account_move.create({'name': record.name, 'date':record.date, 'journal_id' : record.journal_id.id})
                lines = []
                cr_line_dict = {
                    'name': 'To Loan Account:',
                    'move_id':move_id.id,
                    'account_id': record.account_id.id,
                    'credit': record.loan_amount,
                    'partner_id': record.partner_id.id,
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
                        'account_id': record.partner_id.property_account_receivable_id.id,
                        'debit': round((record.loan_amount / int(record.loan_duration)),2),
                        'partner_id': record.partner_id.id,
                        'date_maturity': date_maturity,
                    }
                    lines.append((0,0,dr_line_dict))
                move_id.write({'line_ids': lines})
                record.write({'state': 'open','move_id':move_id.id})

class fund_payment(models.Model):
    _inherit = 'account.payment'
    _description = 'Scheme Fund Payment'

    def _default_scheme_journal_methods(self):
        return self.env.ref('society_fund_management_9.account_scheme_journal')

    def _default_panalty_interest_journal_methods(self):
        return self.env.ref('society_fund_management_9.account_panalyty_interest_journal')

    def _default_scheme_account_methods(self):
        return self.env.ref('society_fund_management_9.account_scheme_account')

    def _default_panalty_account_methods(self):
        return self.env.ref('society_fund_management_9.account_panalty_account')

    def _default_interest_account_methods(self):
        return self.env.ref('society_fund_management_9.account_interest_account')

    def _default_analytic_interest_methods(self):
        return self.env.ref('society_fund_management_9.analytic_interest_society')

    def _default_analytic_panalty_methods(self):
        return self.env.ref('society_fund_management_9.analytic_panalty_society')

    scheme_id = fields.Many2one(related='partner_id.scheme_id', store=True, readonly=True, copy=False)
    scheme_journal_id = fields.Many2one('account.journal', 'scheme Journal', domain="[('type','=','purchase')]", default=lambda self: self._default_scheme_journal_methods())
    panalty_int_journal_id = fields.Many2one('account.journal', 'Panalty/Interest Journal', domain="[('type','=','sale')]", default=lambda self: self._default_panalty_interest_journal_methods())
    scheme_account_id = fields.Many2one('account.account', 'scheme Account', domain="[('internal_type','=','other')]", default=lambda self: self._default_scheme_account_methods())
    analytic_id = fields.Many2one('account.analytic.account', 'Interest Costing', domain="[('type','=','normal')]", default=lambda self: self._default_analytic_interest_methods(), readonly=True, states={'draft':[('readonly',False)],'sip':[('readonly',False)]})
    analytic_panalty_id = fields.Many2one('account.analytic.account', 'Panalty Costing', domain="[('type','=','normal')]", default=lambda self: self._default_analytic_panalty_methods(), readonly=True, states={'draft':[('readonly',False)],'sip':[('readonly',False)]})
    count_scheme_paid = fields.Integer(string='Total scheme Paid', store=True, compute='_count_scheme')
    count_scheme_current = fields.Integer(string='Current scheme', store=True, compute='_count_scheme')
    loan_id = fields.Many2one('fund.loan', string="Loan", store=True, compute='_get_loan')
    panalty = fields.Float(string='Panelty', digits=(16, 2), default=0.0, readonly=True, states={'draft':[('readonly',False)]})
    panalty_extra = fields.Float(string='Panelty Extra', digits=(16, 2), default=0.0, readonly=True, states={'draft':[('readonly',False)]})
    total_panalty = fields.Float(string='Panelty', digits=(16, 2), store=True, compute='_compute_panalty')
    panalty_account_id = fields.Many2one('account.account', 'Panalty Account', domain="[('internal_type','=','other')]", default=lambda self: self._default_panalty_account_methods())
    interest_account_id = fields.Many2one('account.account', 'Interest Account', domain="[('internal_type','=','other')]", default=lambda self: self._default_interest_account_methods())
    loan_emi = fields.Float(related='loan_id.loan_emi', store=True, readonly=True, copy=False)
    count_emi_paid = fields.Integer(related='loan_id.count_emi_paid', store=True, readonly=True, copy=False)
    balance_paid = fields.Float(related='loan_id.balance_paid', store=True, readonly=True, copy=False)
    count_emi_current = fields.Integer(related='loan_id.count_emi_current', store=True, readonly=True, copy=False)
    monthly_amt = fields.Float(related='scheme_id.month_amt', store=True, readonly=True, copy=False)
    monthly_int = fields.Float(string='Interest', digits=(16, 2), store=True, compute='_monthly_interest')
    total_payment = fields.Float(string='T.Payment(Without Scheme Amt.)', digits=(16, 2), store=True, compute='_compute_payment')
    total_all = fields.Float(string='Total', digits=(16, 2), store=True, compute='_compute_payment')
    state = fields.Selection([('draft', 'Draft'), ('sip', 'Scheme/Interest/Panelty'), ('posted', 'Posted'), ('sent', 'Sent'), ('reconciled', 'Reconciled')], readonly=True, default='draft', copy=False, string="Status")
    scheme_move_id = fields.Many2one('account.move', string='Scheme Journal Entry',
        readonly=True, index=True, ondelete='cascade', copy=False,
        help="Link to the automatically generated Scheme Journal Items.")
    interest_move_id = fields.Many2one('account.move', string='Interest Journal Entry',
        readonly=True, index=True, ondelete='cascade', copy=False,
        help="Link to the automatically generated Interest Journal Items.")
    panalty_move_id = fields.Many2one('account.move', string='Panalty Journal Entry',
        readonly=True, index=True, ondelete='cascade', copy=False,
        help="Link to the automatically generated Panalty Journal Items.")
    payment_move_id = fields.Many2one('account.move', string='Payment Journal Entry',
            readonly=True, index=True, ondelete='cascade', copy=False,
            help="Link to the automatically generated Payment Journal Items.")
    printed = fields.Boolean(string='Printed')

    @api.one
    @api.constrains('amount')
    def _check_amount(self):
        return

    @api.constrains('panalty')
    def _check_panalty(self):
        for record in self:
            if record.panalty == 0.0 and record.partner_id.scheme_id:
                day = record.scheme_id.due_day
                date_payment = datetime.strptime(record.payment_date, "%Y-%m-%d")
                if date_payment.day > day:
                    raise except_orm(_('Panalty Applied'),_('You have exceeded the normal date cycle, Panalty amount should be passed.'))

    @api.depends('partner_id','scheme_id')
    def _count_scheme(self):
        account_move_line_obj = self.env['account.move.line']
        scheme_account_id = self.env.ref('society_fund_management_9.account_scheme_account').id
        for record in self:
            if record.scheme_id:
                domain = [('move_id.name','=',record.scheme_id.name),('partner_id','=',record.partner_id.id),('debit','=',record.scheme_id.month_amt), ('account_id','=',scheme_account_id)]
                total_move_line_ids = account_move_line_obj.search(domain)
                start_date = datetime.strptime(record.scheme_id.start_date, '%Y-%m-%d')
                end_date = datetime.strptime(record.scheme_id.end_date, '%Y-%m-%d')
                filter_lines = total_move_line_ids.filtered(lambda r: (datetime.strptime(r.date, '%Y-%m-%d') >= start_date) and (datetime.strptime(r.date, '%Y-%m-%d') <= end_date))
                record.count_scheme_paid = len(filter_lines)
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
                if record.loan_id.int_type == 'fixed':
                    record.monthly_int = round((record.loan_id.int_amt / record.loan_id.loan_duration),2)
                else:
                    record.monthly_int = round((record.loan_id.int_amt / (record.loan_id.loan_duration - record.count_emi_paid)),2)

    @api.depends('panalty', 'panalty_extra','loan_emi','monthly_amt')
    def _compute_payment(self):
        for record in self:
            record.total_payment =  record.panalty + record.panalty_extra + record.monthly_int + record.loan_emi
            record.total_all =  record.total_payment + record.monthly_amt

    @api.multi
    def action_validate_scheme(self):
        account_move = self.env['account.move']
        for record in self:
            passed_date = datetime.strptime(record.payment_date, '%Y-%m-%d')
            checking_duplicate = self.search([('payment_date','=',passed_date),('partner_id','=',record.partner_id.id),('state','!=','draft')])
            if checking_duplicate:
                raise except_orm(_('Already Paid..!!!'),_('Already paid for Day "{}" for member {}.'.format(record.payment_date,record.partner_id.name)))
            if record.scheme_id:
                move_id = account_move.create({'name': record.scheme_id.name, 'date':record.payment_date, 'journal_id' : record.scheme_journal_id.id})
                record.write({'scheme_move_id':move_id.id})
                dr_line_dict = {
                    'name': record.partner_id.name+':'+'Member',
                    'account_id': record.partner_id.property_account_payable_id.id,
                    'credit': record.monthly_amt,
                    'partner_id': record.partner_id.id
                }
                cr_line_dict = {
                    'name': 'To scheme Account:',
                    'account_id': record.scheme_account_id.id,
                    'debit': record.monthly_amt,
                    'partner_id': record.partner_id.id
                }
                move_id.write({'line_ids':[(0,0,dr_line_dict),(0,0,cr_line_dict)]})
            if record.loan_id:
                interest_move_id = account_move.create({'name': 'Interest Entry Move', 'date':record.payment_date, 'journal_id' : record.panalty_int_journal_id.id})
                record.write({'interest_move_id':interest_move_id.id})
                dr_line_dict = {
                    'name': record.partner_id.name+':'+'Member',
                    'account_id': record.partner_id.property_account_receivable_id.id,
                    'debit': record.monthly_int,
                    'loan_id':record.loan_id.id,
                    'partner_id': record.partner_id.id
                }
                cr_line_dict = {
                    'name': 'To Interest Account:',
                    'account_id': record.interest_account_id.id,
                    'credit': record.monthly_int,
                    'partner_id': record.partner_id.id,
                    'analytic_account_id':record.analytic_id.id
                }
                interest_move_id.write({'line_ids':[(0,0,dr_line_dict),(0,0,cr_line_dict)]})
                record.loan_id._balance_status()
            if record.total_panalty > 0:
                panalty_move_id = account_move.create({'name': 'Panalty Entry Move', 'date':record.payment_date, 'journal_id' : record.panalty_int_journal_id.id})
                record.write({'panalty_move_id':panalty_move_id.id})
                dr_line_dict = {
                    'name': record.partner_id.name+':'+'Member',
                    'account_id': record.partner_id.property_account_receivable_id.id,
                    'debit': record.total_panalty,
                    'partner_id': record.partner_id.id
                }
                cr_line_dict = {
                    'name': 'To Panalty Account:',
                    'account_id': record.panalty_account_id.id,
                    'credit': record.total_panalty,
                    'partner_id': record.partner_id.id,
                    'analytic_account_id':record.analytic_panalty_id.id
                }
                panalty_move_id.write({'line_ids':[(0,0,dr_line_dict),(0,0,cr_line_dict)]})
            record.write({'state':'sip','payment_type':'transfer'})

    @api.multi
    def _create_fund_payment_entry(self):
        account_move = self.env['account.move']
        for record in self:
            move_id = account_move.create({'name': record.name, 'date':record.payment_date, 'journal_id' : record.journal_id.id})
            dr_line_dict = {
                'name': 'To Payment Account:',
                'account_id': record.company_id.transfer_account_id.id,
                'debit': record.amount,
                'partner_id': record.partner_id.id
            }
            cr_line_dict = {
                'name': record.partner_id.name+':'+'Member',
                'account_id': record.partner_id.property_account_receivable_id.id,
                'credit': record.amount,
                'partner_id': record.partner_id.id
            }
            move_id.write({'line_ids':[(0,0,dr_line_dict),(0,0,cr_line_dict)]})
            record.write({'payment_move_id':move_id.id, 'state':'posted'})

    @api.multi
    def fund_post(self):
        for rec in self:
            # Use the right sequence to set the name
            if rec.payment_type == 'transfer':
                sequence = rec.env.ref('account.sequence_payment_transfer')
            else:
                if rec.partner_type == 'customer':
                    if rec.payment_type == 'inbound':
                        sequence = rec.env.ref('account.sequence_payment_customer_invoice')
                    if rec.payment_type == 'outbound':
                        sequence = rec.env.ref('account.sequence_payment_customer_refund')
                if rec.partner_type == 'supplier':
                    if rec.payment_type == 'inbound':
                        sequence = rec.env.ref('account.sequence_payment_supplier_refund')
                    if rec.payment_type == 'outbound':
                        sequence = rec.env.ref('account.sequence_payment_supplier_invoice')
            rec.name = sequence.with_context(ir_sequence_date=rec.payment_date).next_by_id()
            if rec.amount == 0:
                raise except_orm(_('Missing Payment Amount !'),_('You should passed amount from total payment value.'))
            # Create the journal entry
            rec._create_fund_payment_entry()
            # In case of a transfer, the first journal entry created debited the source liquidity account and credited
            # the transfer account. Now we debit the transfer account and credit the destination liquidity account.
            if rec.payment_type == 'transfer':
                transfer_credit_aml = rec.payment_move_id.line_ids.filtered(lambda r: r.credit > 0)
                transfer_debit_aml = self.env['account.move.line']
                if rec.loan_id:
                    payment_date = datetime.strptime(rec.payment_date, '%Y-%m-%d').strftime('%Y-%m')
                    loan_ml = rec.loan_id.move_id.line_ids.filtered(lambda r: r.debit > 0 and (datetime.strptime(r.date_maturity, '%Y-%m-%d').strftime('%Y-%m') == payment_date))
                    transfer_debit_aml += loan_ml
                    interest_aml = rec.interest_move_id.line_ids.filtered(lambda r: r.debit > 0)
                    transfer_debit_aml += interest_aml
                if rec.panalty_move_id:
                    panalty_aml = rec.panalty_move_id.line_ids.filtered(lambda r: r.debit > 0)
                    transfer_debit_aml += panalty_aml
                (transfer_credit_aml + transfer_debit_aml).reconcile()

            rec.state = 'reconciled'
            if rec.loan_id:
                rec.loan_id._balance_status()
                if rec.loan_id.balance_paid == rec.loan_id.total_amount:
                    rec.loan_id.write({'state':'paid'})


class profit_sharing(models.Model):
    _name = 'profit.sharing'
    _description = 'Fund scheme Profit Sharing'

    def _default_ps_journal_methods(self):
        return self.env.ref('society_fund_management_9.account_ps_journal')

    def _default_panalty_account_methods(self):
        return self.env.ref('society_fund_management_9.account_panalty_account')

    def _default_interest_account_methods(self):
        return self.env.ref('society_fund_management_9.account_interest_account')

    name = fields.Char(string='Welfare Profit Sharing', required=True)
    date = fields.Date(string='Date', copy=False, required=True, default=fields.Date.context_today)
    start_date = fields.Date(string='Start Date Balance', index=True, copy=False, required=True)
    end_date = fields.Date(string='End Date Balance', index=True, copy=False, required=True, default=fields.Date.context_today)
    partner_ids = fields.Many2many('res.partner', 'parner_sharing_rel', 'partner_id', 'sharing_id', string="Members", copy=False)
    journal_id = fields.Many2one('account.journal', 'Sharing Journal', domain="[('type','=','purchase')]", default=lambda self: self._default_ps_journal_methods())
    interest_account_id = fields.Many2one('account.account', 'Interest Sharing Account', domain="[('internal_type','=','other')]", required=True, default=lambda self: self._default_interest_account_methods())
    panalty_account_id = fields.Many2one('account.account', 'Panalty Sharing Account', domain="[('internal_type','=','other')]", required=True, default=lambda self: self._default_panalty_account_methods())
    move_ids = fields.Many2many('account.move', 'profit_move_rel', 'sharing_id', 'move_id', string="Account Moves", copy=False)
    balance = fields.Float(string='Sharing Balance', digits=(16, 2), store=True, compute='_compute_balance')
    tatal_int_amt = fields.Float(string='Sharing Interest Amount', digits=(16, 2), store=True, compute='_compute_balance')
    tatal_pan_amt = fields.Float(string='Sharing Panalty Amount', digits=(16, 2), store=True, compute='_compute_balance')
    state = fields.Selection([
            ('draft','Draft'),
            ('paid','Paid'),
            ('cancel','Cancelled'),
        ], string='Status', index=True, readonly=True, default='draft',
        track_visibility='onchange', copy=False)

    @api.depends('interest_account_id','panalty_account_id','start_date','end_date','partner_ids','balance')
    def _compute_balance(self):
        for record in self:
            record.balance = 0.0
            record.tatal_int_amt = 0.0
            record.tatal_pan_amt = 0.0
            if record.partner_ids and record.interest_account_id and record.panalty_account_id:
                # Prepare sql query base on selected parameters from wizard
                tables, where_clause, where_params = self.env['account.move.line'].with_context({'date_from':record.start_date, 'date_to': record.end_date})._query_get()
                tables = tables.replace('"','')
                if not tables:
                    tables = 'account_move_line'
                wheres = [""]
                if where_clause.strip():
                    wheres.append(where_clause.strip())
                filters = " AND ".join(wheres)
                # compute the balance, debit and credit for the provided accounts
                request = ("SELECT account_id AS id, SUM(debit) AS debit, SUM(credit) AS credit, (SUM(debit) - SUM(credit)) AS balance" +\
                           " FROM " + tables + " WHERE account_id IN %s " + filters + " GROUP BY account_id")
                params = (tuple([record.interest_account_id.id,record.panalty_account_id.id]),) + tuple(where_params)
                self.env.cr.execute(request, params)
                result = self.env.cr.dictfetchall()
                for res in result:
                    record.balance += abs(res['balance'])
                    if res['id'] == record.interest_account_id.id:
                        record.tatal_int_amt = round(abs(res['balance'])/len(record.partner_ids),2)
                    if res['id'] == record.panalty_account_id.id:
                        record.tatal_pan_amt = round(abs(res['balance'])/len(record.partner_ids),2)

    @api.multi
    def action_validate(self):
        account_move = self.env['account.move']
        for record in self:
            if not record.move_ids and record.partner_ids and record.interest_account_id and record.panalty_account_id:
                moves_l = []
                for partner in record.partner_ids:
                    move_id = account_move.create({'name': record.name, 'date':record.date, 'journal_id' : record.journal_id.id})
                    cr_line_dict = {
                        'name': partner.name+':'+'Member',
                        'account_id': partner.property_account_payable_id.id,
                        'credit': record.tatal_int_amt + record.tatal_pan_amt,
                        'partner_id': partner.id,
                    }
                    dr_line_dict_1 = {
                        'name': 'To Sharing Interest Account:',
                        'account_id': record.interest_account_id.id,
                        'debit': record.tatal_int_amt,
                        'partner_id': partner.id,
                    }
                    dr_line_dict_2 = {
                        'name': 'To Sharing Panalty Account:',
                        'account_id': record.panalty_account_id.id,
                        'debit': record.tatal_pan_amt,
                        'partner_id': partner.id,
                    }
                    move_id.write({'line_ids':[(0,0,cr_line_dict),(0,0,dr_line_dict_1),(0,0,dr_line_dict_2)]})
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
