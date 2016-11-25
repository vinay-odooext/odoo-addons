from openerp import models, fields, api, _
from openerp.exceptions import Warning

# from pprint import pprint


class sale_order(models.Model):
    _inherit = "sale.order"

    state = fields.Selection([
            ('draft', 'Quotation'),
            ('sent', 'Quotation Sent'),
            ('confirm', 'Quotation Confirm'),
            ('cancel', 'Cancelled'),
            ('waiting_date', 'Waiting Schedule'),
            ('progress', 'Sales Order'),
            ('manual', 'Sale to Invoice'),
            ('shipping_except', 'Shipping Exception'),
            ('invoice_except', 'Invoice Exception'),
            ('done', 'Done'),
            ], 'Status', readonly=True, copy=False, help="Gives the status of the quotation or sales order.\
              \nThe exception status is automatically set when a cancel operation occurs \
              in the invoice validation (Invoice Exception) or in the picking list process (Shipping Exception).\nThe 'Waiting Schedule' status is set when the invoice is confirmed\
               but waiting for the scheduler to run on the order date.", index=True)
    gr_merge_on = fields.Selection([
            ('gr_so', 'Group by SO'),
            ('gr_sol', 'Group by SOL'),
            ], 'Status', copy=False, help="Gives the status of the sales order.\
              \nGrouping of procurement and Delivery order \
              will be done on the bases of this field with in workflow transition.", index=True, default='gr_so')

    @api.multi
    def action_quotation_confirm(self):
        return self.write({'state': 'confirm'})

    @api.multi
    def action_ship_create(self):
        res = super(sale_order, self).action_ship_create()
        for order in self:
            order.order_line._compute_remaining_do()
        return res

    @api.multi
    def action_ship_create_gr_sol(self):
        """Create the required procurements to supply sales order lines, also connecting
        the procurements to appropriate stock moves in order to bring the goods to the
        sales order's requested location.

        :return: True
        """
        sale_line_obj = self.env['sale.order.line']
        except_proc_ids = self.env['procurement.order']
        for line in self.order_line:
            #Try to fix exception procurement (possible when after a shipping exception the user choose to recreate)
            if line.procurement_ids:
                #first check them to see if they are in exception or not (one of the related moves is cancelled)
                line.procurement_ids.filtered(lambda r: r.state not in ['cancel', 'done']).check()
                line.refresh()
                #run again procurement that are in exception in order to trigger another move
                except_proc_ids += line.procurement_ids.filtered(lambda r: r.state in ['exception', 'cancel'])
                except_proc_ids.reset_to_confirmed()
        #Confirm procurement order such that rules will be applied on it
        #note that the workflow normally ensure proc_ids isn't an empty list
        except_proc_ids.run()
        #if shipping was in exception and the user choose to recreate the delivery order, write the new status of SO
        if self.state == 'shipping_except':
            val = {'state': 'progress', 'shipped': False}
            if (self.order_policy == 'manual'):
                for line in self.order_line:
                    if (not line.invoiced) and (line.state not in ('cancel', 'draft')):
                        val['state'] = 'manual'
                        break
            self.write(val)
        return True

class sale_order_line(models.Model):
    _inherit = 'sale.order.line'

    @api.depends('state')
    def _compute_remaining_do(self):
        for record in self:
            if record.product_id.type == 'service':
                record.remaining_do = True
            else:
                proc_ids = self.env['procurement.order'].search([('sale_line_id','=',record.id),('state','!=','cancel')])
                if len(proc_ids.ids):
                    record.remaining_do = True

    remaining_do = fields.Boolean(string='Remaining Do', store=True, compute='_compute_remaining_do', help="It help you for pending lines for creating DO.")
