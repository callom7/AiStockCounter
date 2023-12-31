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

from openerp.osv import fields, osv, orm
import openerp.addons.decimal_precision as dp
from openerp.tools.translate import _
from openerp import tools
import os 
import logging

class stock_change_product_qty(osv.osv_memory):
    _name = "stock.change.product.qty"
    _description = "Change Product Quantity"
    _columns = {
        'product_id' : fields.many2one('product.product', 'Product'),
        'new_quantity': fields.float('New Quantity on Hand', digits_compute=dp.get_precision('Product Unit of Measure'), required=True, help='This quantity is expressed in the Default Unit of Measure of the product.'),
        'lot_id': fields.many2one('stock.production.lot', 'Serial Number', domain="[('product_id','=',product_id)]"),
        'location_id': fields.many2one('stock.location', 'Location', required=True, domain="[('usage', '=', 'internal')]"),
    }
    _defaults = {
        'new_quantity': 1,
        'product_id': lambda self, cr, uid, ctx: ctx and ctx.get('active_id', False) or False
    }

    def default_get(self, cr, uid, fields, context):
        """ To get default values for the object.
         @param self: The object pointer.
         @param cr: A database cursor
         @param uid: ID of the user currently logged in
         @param fields: List of fields for which we want default values
         @param context: A standard dictionary
         @return: A dictionary which of fields with values.
        """

        res = super(stock_change_product_qty, self).default_get(cr, uid, fields, context=context)

        if context.get('active_model') == 'product.template':
            product_ids = self.pool.get('product.product').search(cr, uid, [('product_tmpl_id', '=', context.get('active_id'))], context=context)
            if len(product_ids) == 1:
                res['product_id'] = product_ids[0]
            else:
                raise orm.except_orm(_('Warning'), _('Please use the Product Variant view to update the product quantity.'))

        if 'location_id' in fields:
            location_id = res.get('location_id', False)
            if not location_id:
                try:
                    model, location_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'stock', 'stock_location_stock')
                except (orm.except_orm, ValueError):
                    pass
            if location_id:
                try:
                    self.pool.get('stock.location').check_access_rule(cr, uid, [location_id], 'read', context=context)
                except (orm.except_orm, ValueError):
                   location_id = False
            res['location_id'] = location_id
        return res

    def _prepare_inventory_line(self, cr, uid, inventory_id, data, context=None):

        product = data.product_id.with_context(location=data.location_id.id, lot_id=data.lot_id.id)
        th_qty = product.qty_available

        res = {'inventory_id': inventory_id,
               'product_qty': data.new_quantity,
               'location_id': data.location_id.id,
               'product_id': data.product_id.id,
               'product_uom_id': data.product_id.uom_id.id,
               'theoretical_qty': th_qty,
               'prod_lot_id': data.lot_id.id
               }

        return res

    def change_product_qty(self, cr, uid, ids, context=None):
        """ Changes the Product Quantity by making a Physical Inventory.
        @param self: The object pointer.
        @param cr: A database cursor
        @param uid: ID of the user currently logged in
        @param ids: List of IDs selected
        @param context: A standard dictionary
        @return:
        """
        if context is None:
            context = {}

        inventory_obj = self.pool.get('stock.inventory')
        inventory_line_obj = self.pool.get('stock.inventory.line')

        for data in self.browse(cr, uid, ids, context=context):
            if data.new_quantity < 0:
                raise osv.except_osv(_('Warning!'), _('Quantity cannot be negative.'))
            ctx = context.copy()
            ctx['location'] = data.location_id.id
            ctx['lot_id'] = data.lot_id.id
            if data.product_id.id and data.lot_id.id:
                filter = 'none'
            elif data.product_id.id:
                filter = 'product'
            else:
                filter = 'none'
            inventory_id = inventory_obj.create(cr, uid, {
                'name': _('INV: %s') % tools.ustr(data.product_id.name),
                'filter': filter,
                'product_id': data.product_id.id,
                'location_id': data.location_id.id,
                'lot_id': data.lot_id.id}, context=context)

            line_data = self._prepare_inventory_line(cr, uid, inventory_id, data, context=context)

            inventory_line_obj.create(cr, uid, line_data, context=context)
            inventory_obj.action_done(cr, uid, [inventory_id], context=context)
        return {}
       
    def launch2(self, cr, uid, ids, context=None):
        """ Changes the Product Quantity by making a Physical Inventory.
        @param self: The object pointer.
        @param cr: A database cursor
        @param uid: ID of the user currently logged in
        @param ids: List of IDs selected
        @param context: A standard dictionary
        @return:
        """
        if context is None:
            context = {}

        # Reading the output.txt file in order to extract the quantity information
        file_path = 'C:\\aiImageRecognition3\\yolov5\\output.txt'
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                file_content = f.read().strip()
                # Extracting the quantity from text file)
                items = file_content.split(',')
                products = {}
                for item in items:
                    split_items = item.strip().split(' ')
                    if len(split_items) < 2:
                        continue  
                    qty, name = split_items
                    products[name] = int(qty)

            # Updating the quantity of products
            product_obj = self.pool.get('product.product')
            for data in self.browse(cr, uid, ids, context=context):
                if data.product_id.name in products:
                    new_quantity = products[data.product_id.name]
                    if new_quantity < 0:
                        raise osv.except_osv(_('Warning!'), _('Quantity cannot be negative.'))

                    data.write({'new_quantity': new_quantity})

                    inventory_obj = self.pool.get('stock.inventory')
                    inventory_line_obj = self.pool.get('stock.inventory.line')

                    if data.new_quantity < 0:
                        raise osv.except_osv(_('Warning!'), _('Quantity cannot be negative.'))
                    ctx = context.copy()
                    ctx['location'] = data.location_id.id
                    ctx['lot_id'] = data.lot_id.id
                    if data.product_id.id and data.lot_id.id:
                        filter = 'none'
                    elif data.product_id.id:
                        filter = 'product'
                    else:
                        filter = 'none'
                    inventory_id = inventory_obj.create(cr, uid, {
                        'name': _('INV: %s') % tools.ustr(data.product_id.name),
                        'filter': filter,
                        'product_id': data.product_id.id,
                        'location_id': data.location_id.id,
                        'lot_id': data.lot_id.id}, context=context)

                    line_data = self._prepare_inventory_line(cr, uid, inventory_id, data, context=context)

                    inventory_line_obj.create(cr, uid, line_data, context=context)
                    inventory_obj.action_done(cr, uid, [inventory_id], context=context)
        else:
            raise osv.except_osv(_('Warning!'), _('Text File does not exist.'))
        return {}



    def onchange_location_id(self, cr, uid, ids, location_id, product_id, context=None):
        if location_id:
            qty_wh = 0.0
            qty = self.pool.get('product.product')._product_available(cr, uid, [product_id], context=dict(context or {}, location=location_id, compute_child=False))
            if product_id in qty:
                qty_wh = qty[product_id]['qty_available']
            return { 'value': { 'new_quantity': qty_wh } }
    


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
