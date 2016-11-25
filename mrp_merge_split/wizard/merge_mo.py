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

class Merge_MO(models.TransientModel):
    _name = 'merge.mo'
    _description = 'Merged Manufacturing Order'

    @api.multi
    def merged_mo(self):
        mo_obj = self.env['mrp.production']
        mo_order_ids = mo_obj.browse(self.env.context['active_ids'])
        if not mo_order_ids or len(mo_order_ids) == 1:
            return 
        first_mo = mo_order_ids[0]
        product_id = first_mo.product_id.id
        product_uom = first_mo.product_uom.id
        bom_id = first_mo.bom_id.id
        result = [mo for mo in mo_order_ids if mo.product_id.id <> product_id]
        result1 = [mo for mo in mo_order_ids if mo.product_uom.id <> product_uom]
        state_res = [mo for mo in mo_order_ids if mo.state <> 'draft']
        diff_bom_l = [mo for mo in mo_order_ids if mo.bom_id.id <> bom_id]
        if len(result):
            raise Warning('Found Different FG Products !\n\n You can only allow to merge same FG product merging MO.')
        if len(result1):
            raise Warning('Found Different UOM FG Products !\n\n You can only allow to merge same UOM FG product merging MO.')
        if len(state_res):
            raise Warning('Found Different State !\n\n You can only allow to merge MO with draft status.')
        if len(diff_bom_l):
            raise Warning('Found Different BOM !\n\n You can only allow to merge MO with same raw materials.')
        total_qty = 0
        new_mo = mo_order_ids[0].copy()
        ref = ''
        for mo in mo_order_ids:
            total_qty += mo.product_qty
            if not ref:
                ref = mo.name
            else:
                ref += ', '+str(mo.name)
            mo.write({'state':'cancel'})
        res = mo_obj.product_id_change(new_mo.product_id.id, total_qty)
        new_mo.write({'product_qty':total_qty, 'mrp_raw_material_ids': res['value']['mrp_raw_material_ids'], 'origin': ref})
                

