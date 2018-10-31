# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-today OpenERP SA (<http://www.openerp.com>)
#    Copyright (C) 2013-today Synconics Technologies Pvt. Ltd. (<http://www.synconics.com>)
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

from openerp import api, models, fields , _
from datetime import datetime, timedelta

class ak_marketing_reservation_wiz(models.TransientModel):
    _name = 'ak.marketing.reservation.wiz'
    _description = "Marketing Reservation Deal Wizard"

    responsible_commission = fields.Float('Responsible by Commission')
    reserved_commission = fields.Float('Reserved by Commission')
    responsible_user_id = fields.Many2one('res.users')
    reserved_user_id = fields.Many2one('res.users')

    @api.cr_uid_ids_context
    def default_get(self, cr, uid, fields, context=None):
        """ To get default values for the object.
        """
        if context is None:
            context = {}
        res = super(ak_marketing_reservation_wiz, self).default_get(cr, uid, fields, context=context)
        if context and context.get('active_id'):
        	reservation = self.pool.get('ak.reservation').browse(cr, uid, context['active_id'], context=context)
        	res.update({'responsible_user_id': reservation.ak_property_id.ak_responisible.id , 'reserved_user_id': reservation.ak_user_id.id})
		return res

    @api.multi
    def done_reservation(self):
        employee_obj = self.env['hr.employee']
        if self.responsible_user_id and self.reserved_user_id:
            responsible_employee = employee_obj.search([('user_id','=',self.responsible_user_id.id)])
            if responsible_employee and self.responsible_commission > 0.0:
                responsible_employee.write({'ak_commission_history_ids': [(0, 0, {
                     'date': fields.Date.today(),
                     'amount': self.responsible_commission,
                     'description': 'Commission from marketing deal.',
                     'status': 'unpaid',
                })]})
            if self.responsible_user_id != self.reserved_user_id:
                reserved_employee = employee_obj.search([('user_id','=',self.reserved_user_id.id)])
                if reserved_employee and self.reserved_commission > 0.0:
                    reserved_employee.write({'ak_commission_history_ids': [(0, 0, {
                     'date': fields.Date.today(),
                     'amount': self.reserved_commission,
                     'description': 'Commission from marketing deal.',
                     'status': 'unpaid',
                })]})
            if self._context.get('active_id'):
                reservation = self.env['ak.reservation'].browse(self._context.get('active_id'))
                reservation.write({'state': 'done_marketing'})

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: