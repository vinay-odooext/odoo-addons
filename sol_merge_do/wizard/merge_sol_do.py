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

class Merge_SOL_DO(models.TransientModel):
    _name = 'merge.sol.do'
    _description = 'Merged SOL Group By Lines'

    @api.multi
    def _prepare_order_line_procurement(self, order, line, group_id=False):
        date_planned = self.env['sale.order']._get_date_planned(order, line, order.date_order)
        return {
            'name': line.name,
            'origin': line.order_id.name,
            'location_id':order.partner_shipping_id.property_stock_customer.id,
            'route_ids':line.route_id and [(4, line.route_id.id)] or [],
            'warehouse_id':order.warehouse_id and order.warehouse_id.id or False,
            'partner_dest_id':order.partner_shipping_id.id,
            'date_planned': date_planned,
            'product_id': line.product_id.id,
            'product_qty': line.product_uom_qty,
            'product_uom': line.product_uom.id,
            'product_uos_qty': (line.product_uos and line.product_uos_qty) or line.product_uom_qty,
            'product_uos': (line.product_uos and line.product_uos.id) or line.product_uom.id,
            'company_id': order.company_id.id,
            'group_id': group_id,
            'invoice_state': (order.order_policy == 'picking') and '2binvoiced' or 'none',
            'sale_line_id': line.id
        }
        
    @api.multi
    def merged_sol_do(self):
        move_lines = self.env['stock.move']
        order_lines = self.env['sale.order.line'].browse(self.env.context['active_ids'])
        if not order_lines or len(order_lines) == 1:
            return 
        first_sol = order_lines[0]
        partner_id = first_sol.order_partner_id.id
        product_uom = first_sol.product_uom.id
        result = [line for line in order_lines if line.order_partner_id.id <> partner_id]
        result1 = [line for line in order_lines if line.product_uom.id <> product_uom]
        if len(result):
            raise Warning('Found Different Partners !\n\n You can only allow to merge SOL with same partner reference.')
        if len(result1):
            raise Warning('Found Different UOM SOL Products !\n\n You can only allow to merge same UOM SOL product.')
        procurement_obj = self.env['procurement.order']
        proc_ids = self.env['procurement.order']
        for line in order_lines:
            if line.order_id.procurement_group_id:
                group_id = line.order_id.procurement_group_id
            else:
                group_id = self.env['procurement.group'].create({'name': 'Common Group', 'partner_id': partner_id})
        for line in order_lines:
            line.order_id.write({'procurement_group_id': group_id.id,'gr_merge_on':'gr_sol'})
            if not line.product_id:
                continue
            vals = self._prepare_order_line_procurement(line.order_id, line, group_id=line.order_id.procurement_group_id.id)
            ctx = dict(self.env.context)
            ctx['procurement_autorun_defer'] = True
            proc_id = procurement_obj.with_context(ctx).create(vals)
            proc_ids += proc_id
            line.order_id.action_button_confirm()
        proc_ids.run()
        order_lines._compute_remaining_do()
        return True