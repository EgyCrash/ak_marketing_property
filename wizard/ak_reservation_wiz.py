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
from openerp.osv import osv
from datetime import datetime, timedelta
from openerp.osv.orm import except_orm
from openerp.exceptions import Warning

class ak_reservation_wiz(models.TransientModel):
    _name = 'ak.reservation.wiz'
    _description = "Reservation Wizard"

    ak_tenant_id = fields.Many2one('res.partner', string='Tenant',
                                   domain=[('ak_is_owner', '=', False)])
    ak_parent_property_id = fields.Many2one('ak.property', string='Parent Property', domain=[('ak_main_property', '=', True)])
    ak_sub_property_id = fields.Many2many('ak.property', 'ak_sub_property_wizard_ref', 'reservation_id',
                                        'property_id', string='Sub Properties', domain=[('ak_main_property', '=', False)])
    ak_amount = fields.Float(string="Reservation Amount")
    ak_amount_numeric = fields.Char(string='Reservation Amount(In alphanumeric)')
    ak_all = fields.Boolean("All Sub Property", default=True)
    ak_notes = fields.Text('Notes')
    ak_button_hide_flag = fields.Boolean('Button Hide Flag')
    ak_type = fields.Selection([('case', 'Cash'), ('check', 'Cheque'), ('wire', 'Wire Transfer')], default='case', string='Payment Type')
    journal_id = fields.Many2one('account.journal', string='Journal')
    ak_account_id = fields.Many2one('account.account', string="Account", company_dependent=True)

    @api.onchange('ak_type')
    def onchange_type(self):
        '''
        Created this method to select journal automatically based on type selected
        '''
        journal_obj = self.env['account.journal']
        criteria = []
        if self.ak_type == 'case':
            criteria = [('type', '=', 'cash')]
        elif self.ak_type == 'check':
            criteria = [('type', '=', 'bank')]
        else:
            criteria = [('type', '=', 'bank')]
        return {'domain':{'journal_id':criteria}}

    @api.onchange('ak_parent_property_id')
    def _onchange_parent_property(self):
        if self.ak_parent_property_id and self.ak_all:
            self.ak_sub_property_id = [(6,0, [])]
            sub_ids = self.env['ak.property'].search([('main_property_id', '=', self.ak_parent_property_id.id),
                                           ('ak_is_rented', '=', False), ('ak_is_reserved', '=', False)])
            if sub_ids:
                self.ak_sub_property_id = [(6,0, sub_ids.ids)]

    @api.onchange('ak_all')
    def _onchange_ak_all(self):
        self.ak_sub_property_id = [(6,0, [])]
        if self.ak_all:
            sub_ids = self.env['ak.property'].search([('main_property_id', '=', self.ak_parent_property_id.id),
                                           ('ak_is_rented', '=', False), ('ak_is_reserved', '=', False)])
            if sub_ids:
                self.ak_sub_property_id = [(6,0, sub_ids.ids)]

    @api.cr_uid_ids_context
    def property_reservation(self, cr, uid, ids, context=None):
        reservation_obj = self.pool.get('ak.reservation')
        property_obj = self.pool.get('ak.property')
        reservation_read = self.read(cr, uid, ids, context=context)[0]
        group_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'account', 'group_account_manager')
        if group_id:
            group = self.pool.get('res.groups').browse(cr, uid, group_id[1]).users
            if group:
                reservation_read['ak_account_manager'] = group[0].name
        sub_property_list = []
        reservation_property_list = []
        if reservation_read.get('ak_all'):
            property_id = reservation_read.get('ak_parent_property_id')
            if property_id:
                sub_properties = property_obj.browse(cr, uid, property_id[0], context=context).ak_sub_property_ids
                if sub_properties:
                    for each_sub_property in sub_properties:
                        if not each_sub_property.ak_is_reserved:
                            reservation_property_list.append(each_sub_property.id)
                    reservation_read['ak_sub_property_id'] = reservation_property_list
        reservation_read['ak_re_end_date'] = (datetime.now() + timedelta(days=4)).strftime('%Y-%m-%d')
        if not reservation_read['ak_sub_property_id']:
            raise except_orm(_('No Records'), _("No sub property available to reserve for this main property"))
        ak_tenant_id = False
        for reservarion_data in self.browse(cr, uid, ids, context=context):
            if reservarion_data.ak_amount <= 0.00:
                raise Warning(_('Please update amount!'))
            ak_tenant_id = reservarion_data.ak_tenant_id
            sale_journal = self.pool.get('account.journal').search(cr, uid, [('type','=','sale')])
            if not sale_journal:
                raise osv.except_osv(_('Warning!'), _('Journal is not available of type sale.') % \
                            ())
            else:
                sale_journal = sale_journal[0]
            if reservarion_data.ak_all:
                sub_ids = property_obj.search(cr, uid, [('main_property_id', '=', reservarion_data.ak_parent_property_id.id),
                                                                     ('ak_is_rented', '=', False), ('ak_is_reserved', '=', False)])
                data = property_obj.browse(cr, uid, sub_ids)
                for each_sub_property in data:
                    sub_property_list.append(each_sub_property.id)
                    if each_sub_property.ak_under_maintenance:
                        raise osv.except_osv(_('Warning!'), _("You cannot reserved selected property because its already under maintenance."))
    #             context.update({'from_reservation_wizard': True})
                reservation = reservation_obj.create(cr, uid, {'ak_tenant_id': reservarion_data.ak_tenant_id.id,
                                                 'ak_property_id': reservarion_data.ak_parent_property_id.id,
                                                 'ak_sub_property_id': sub_property_list and [(6, 0, sub_property_list)] or False,
                                                 'ak_user_id':uid,
                                                 'ak_notes': reservarion_data.ak_notes or '',
                                                 'ak_amount': reservarion_data.ak_amount,
                                                 'ak_amount_numeric':reservarion_data.ak_amount_numeric,
                                                 'ak_reservation_date':datetime.now().strftime('%Y-%m-%d'),
                                                 'ak_type':reservarion_data.ak_type or False,
                                                 'journal_id':reservarion_data.journal_id and reservarion_data.journal_id.id or False,
                                                 'ak_account_id':reservarion_data.ak_account_id and reservarion_data.ak_account_id.id or False}, context=context)
                if reservation:
                    voucher_obj = self.pool.get('account.voucher')
                    voucher_line_obj = self.pool.get('account.voucher.line')
                    voucher_default_data = voucher_obj.default_get(cr, uid, ['message_follower_ids', 'number', 'journal_id', 'currency_id', 'narration', 'partner_id', 'message_ids', 'payment_rate_currency_id', 'reference', 'move_ids', 'state', 'type', 'account_id', 'company_id', 'period_id', 'date', 'tax_amount', 'tax_id', 'audit', 'name', 'amount', 'line_ids', 'line_ids'], context)
                    voucher_onchange_data = voucher_obj.onchange_journal_voucher(cr, uid, [], [(6, 0, [])], False, 0.0, reservarion_data.ak_tenant_id.id, reservarion_data.journal_id and reservarion_data.journal_id.id or False, False, False)
                    line_cr_ids, line_dr_ids = [], []
                    voucher_onchange_data['value']['line_cr_ids'] = []
                    voucher_onchange_data['value']['line_dr_ids'] = []
                    voucher_data = {}
                    voucher_default_data = [voucher_default_data]
                    voucher_onchange_data = [voucher_onchange_data['value']]
                    for dic in voucher_default_data + voucher_onchange_data:
                        voucher_data.update(dic)
                    if reservarion_data.ak_type == 'wire':
                        voucher_data['account_id'] = reservarion_data.ak_account_id and reservarion_data.ak_account_id.id or False
                    voucher_data.update({'partner_id': reservarion_data.ak_tenant_id.id,
                                         'narration': reservarion_data.ak_notes or '',
                                         'ak_type':reservarion_data.ak_type,
                                         'journal_id': reservarion_data.journal_id and reservarion_data.journal_id.id or False})
                                         # 'analytic_id': reservarion_data.ak_parent_property_id.ak_analytic_account_id.id or False})
                    voucher_id = voucher_obj.create(cr, uid, voucher_data, context)

                    voucher_onchange_data = voucher_onchange_data[0]
                    context['partner_id'] = reservarion_data.ak_tenant_id.id
                    context['journal_id'] = reservarion_data.journal_id and reservarion_data.journal_id.id or False
                    context['type'] = voucher_data['type']
                    voucher_line_default_data = voucher_line_obj.default_get(cr, uid, ['account_analytic_id', 'type', 'account_id', 'name', 'amount'], context)
                    voucher_line_default_data['amount'] = reservarion_data.ak_amount
                    voucher_line_default_data['type'] = 'cr'
                    voucher_obj.write(cr, uid, voucher_id, {'amount':reservarion_data.ak_amount, 'line_ids': [[0, False, voucher_line_default_data]]})
                    account_voucher = voucher_obj.browse(cr, uid, voucher_id) 
                    
                    if reservarion_data.ak_tenant_id.property_account_receivable:
                        from_account =  reservarion_data.ak_tenant_id.property_account_receivable.id
                    else:
                        raise osv.except_osv(_('Warning!'), _('There is no receivable account defined for this tenant: "%s".') % \
                                (reservarion_data.ak_tenant_id.name,))
                    downpayment_account = self.pool.get('account.config.settings').get_default_downpayment_account(cr, uid, 'ak_downpayment_account')['ak_downpayment_account']
                    if downpayment_account:
                        to_account = downpayment_account
                    else:
                        raise osv.except_osv(_('Warning!'), _('Plese configure downpayment account.') % \
                            ())
                    
                    analytic_id = reservarion_data.ak_parent_property_id.ak_analytic_account_id and reservarion_data.ak_parent_property_id.ak_analytic_account_id.id or False
                    move = self.pool.get('account.move').create(cr, uid, {
                        'name': '/',
                        'journal_id': sale_journal,
                        'date': datetime.today().date(),
                        'line_id': [(0, 0, {
                                'name': 'Reservation Payment',
                                'partner_id': reservarion_data.ak_tenant_id and reservarion_data.ak_tenant_id.id or False,
                                'debit': reservarion_data.ak_amount,
                                'account_id': from_account,
                            }), (0, 0, {
                                'name': 'Reservation Payment',
                                'partner_id': reservarion_data.ak_tenant_id and reservarion_data.ak_tenant_id.id or False,
                                'credit': reservarion_data.ak_amount,
                                'account_id': to_account,
                                'analytic_account_id': analytic_id,
                                'ak_is_reservation':True,
                            })]
                    }, context=context)
                    
                    for sub_property in reservarion_data.ak_sub_property_id:
                        sub_property.write({'ak_last_reservation_date':datetime.now() + timedelta(days=3), 'ak_is_reserved': True})
            else:
                data = reservarion_data.ak_sub_property_id
                for each_sub_property in reservarion_data.ak_sub_property_id:
                    sub_property_list.append(each_sub_property.id)
                    if each_sub_property.ak_under_maintenance:
                        raise osv.except_osv(_('Warning!'), _("You cannot reserved selected property because its already under maintenance."))
    #             context.update({'from_reservation_wizard': True})
                reservation = reservation_obj.create(cr, uid, {'ak_tenant_id': reservarion_data.ak_tenant_id.id,
                                                 'ak_property_id': reservarion_data.ak_parent_property_id.id,
                                                 'ak_sub_property_id': sub_property_list and [(6, 0, sub_property_list)] or False,
                                                 'ak_user_id':uid,
                                                 'ak_notes': reservarion_data.ak_notes or '',
                                                 'ak_amount': reservarion_data.ak_amount,
                                                 'ak_amount_numeric':reservarion_data.ak_amount_numeric,
                                                 'ak_reservation_date':datetime.now().strftime('%Y-%m-%d'),
                                                 'ak_type':reservarion_data.ak_type or False,
                                                 'journal_id':reservarion_data.journal_id and reservarion_data.journal_id.id or False,
                                                 'ak_account_id':reservarion_data.ak_account_id and reservarion_data.ak_account_id.id or False}, context=context)
                if reservation:
                    voucher_obj = self.pool.get('account.voucher')
                    voucher_line_obj = self.pool.get('account.voucher.line')
                    voucher_default_data = voucher_obj.default_get(cr, uid, ['message_follower_ids', 'number', 'journal_id', 'currency_id', 'narration', 'partner_id', 'message_ids', 'payment_rate_currency_id', 'reference', 'move_ids', 'state', 'type', 'account_id', 'company_id', 'period_id', 'date', 'tax_amount', 'tax_id', 'audit', 'name', 'amount', 'line_ids', 'line_ids'], context)
                    voucher_onchange_data = voucher_obj.onchange_journal_voucher(cr, uid, [], [(6, 0, [])], False, 0.0, reservarion_data.ak_tenant_id.id, reservarion_data.journal_id and reservarion_data.journal_id.id or False, False, False)
                    line_cr_ids, line_dr_ids = [], []
                    voucher_onchange_data['value']['line_cr_ids'] = []
                    voucher_onchange_data['value']['line_dr_ids'] = []
                    voucher_data = {}
                    voucher_default_data = [voucher_default_data]
                    voucher_onchange_data = [voucher_onchange_data['value']]
                    for dic in voucher_default_data + voucher_onchange_data:
                        voucher_data.update(dic)
                    if reservarion_data.ak_type == 'wire':
                        voucher_data['account_id'] = reservarion_data.ak_account_id and reservarion_data.ak_account_id.id or False
                    voucher_data.update({'partner_id': reservarion_data.ak_tenant_id.id,
                                         'narration': reservarion_data.ak_notes or '',
                                         'ak_type':reservarion_data.ak_type,
                                         'journal_id': reservarion_data.journal_id and reservarion_data.journal_id.id or False})
                                         # 'analytic_id': reservarion_data.ak_parent_property_id.ak_analytic_account_id.id or False
                    voucher_id = voucher_obj.create(cr, uid, voucher_data, context)

                    voucher_onchange_data = voucher_onchange_data[0]
                    context['partner_id'] = reservarion_data.ak_tenant_id.id
                    context['journal_id'] = reservarion_data.journal_id and reservarion_data.journal_id.id or False
                    context['type'] = voucher_data['type']
                    voucher_line_default_data = voucher_line_obj.default_get(cr, uid, ['account_analytic_id', 'type', 'account_id', 'name', 'amount'], context)
                    voucher_line_default_data['amount'] = reservarion_data.ak_amount
                    # voucher_line_default_data['account_analytic_id'] = reservarion_data.ak_parent_property_id.ak_analytic_account_id.id or False
                    voucher_line_default_data['type'] = 'cr'
                    voucher_obj.write(cr, uid, voucher_id, {'amount':reservarion_data.ak_amount, 'line_ids': [[0, False, voucher_line_default_data]]})
                    account_voucher = voucher_obj.browse(cr, uid, voucher_id) 
                 
                    if reservarion_data.ak_tenant_id.property_account_receivable:
                        from_account =  reservarion_data.ak_tenant_id.property_account_receivable.id
                    else:
                        raise osv.except_osv(_('Warning!'), _('There is no receivable account defined for this tenant: "%s".') % \
                                (reservarion_data.ak_tenant_id.name,))
                    downpayment_account = self.pool.get('account.config.settings').get_default_downpayment_account(cr, uid, 'ak_downpayment_account')['ak_downpayment_account']
                    if downpayment_account:
                        to_account = downpayment_account
                    else:
                        raise osv.except_osv(_('Warning!'), _('Plese configure downpayment account.') % \
                            ())

                    analytic_id = reservarion_data.ak_parent_property_id.ak_analytic_account_id and reservarion_data.ak_parent_property_id.ak_analytic_account_id.id or False
                    move = self.pool.get('account.move').create(cr, uid, {
                        'name': '/',
                        'journal_id': sale_journal,
                        'date': datetime.today().date(),
                        'line_id': [(0, 0, {
                                'name': 'Reservation Payment',
                                'partner_id': reservarion_data.ak_tenant_id and reservarion_data.ak_tenant_id.id or False,
                                'debit': reservarion_data.ak_amount,
                                'account_id': from_account,
                            }), (0, 0, {
                                'name': 'Reservation Payment',
                                'partner_id': reservarion_data.ak_tenant_id and reservarion_data.ak_tenant_id.id or False,
                                'credit': reservarion_data.ak_amount,
                                'account_id': to_account,
                                'analytic_account_id': analytic_id,
                                'ak_is_reservation':True,
                            })]
                    }, context=context)
                    
                    for sub_property in reservarion_data.ak_sub_property_id:
                        sub_property.write({'ak_last_reservation_date':datetime.now() + timedelta(days=3), 'ak_is_reserved': True})
        values = {
                'ids': [],
                'model': 'ak.reservation',
                'form': reservation_read
            }
        res_read = reservation_obj.read(cr,uid, [reservation],context=context)
        res_read = res_read and res_read[0] or {}
        val = {
            'ids':[reservation],
            'model':'ak.reservation',
            'form':res_read
        }
        if ak_tenant_id:
            values['form'].update({'mobile':ak_tenant_id.mobile or False})
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'ak_akhawen.template_ak_property_reservation',
            'datas': val
            }
        # return self.pool['report'].get_action(cr, uid, [],
        #                                   'ak_akhawen.template_ak_property_reservation',
        #                                   data=val, context=context)
        # return self.pool['report'].get_action(cr, uid, [],
        #                                   'ak_akhawen.report_reservation_receipt_voucher_akhawen',
        #                                   data=values, context=context)

    @api.cr_uid_ids_context
    def default_get(self, cr, uid, fields, context=None):
        """ To get default values for the object.
        """
        if context is None:
            context = {}
        res = super(ak_reservation_wiz, self).default_get(cr, uid,
                                                          fields,
                                                          context=context)
        if context and context.get('from_sub') and context.get('property_id'):
            property = self.pool.get('ak.property').browse(cr, uid, context['property_id'], context=context)
            res.update({'ak_sub_property_id': context.get('property_id') and [(6, 0, [context.get('property_id')])] or False,
                        'ak_parent_property_id': property.main_property_id.id, 'ak_all':False})
            return res
        if context and context.get('property_id'):
            res.update({'ak_parent_property_id': context.get('property_id')})
            return res

    @api.onchange('ak_tenant_id')
    def _onchange_tenant(self):
        tanant_obj = self.env['res.partner']
        reason = ""
        if self.ak_tenant_id.ak_reason_blacklisted:
            reason = self.ak_tenant_id.ak_reason_blacklisted
        if self.ak_tenant_id.ak_is_blacklisted:
            raise except_orm(_('Blacklisted Tenant'), _("Selected is blacklisted because of " + reason))
        if self.ak_tenant_id.ak_id_expiry_date and self.ak_tenant_id.ak_id_expiry_date < fields.Date.today():
            warning = {'message': _("You can not select this tenant because he/she is expired in propery.")}
            self.ak_tenant_id = False
            return {'warning': warning}


class ak_reservation_client_wiz(models.TransientModel):
    _name = 'ak.reservation.client.wiz'
    _description = "Reservation Client Wizard"

    ak_tenant_id = fields.Many2one('res.partner', string='Tenant',
                                   domain=[('ak_is_owner', '=', False)])
    ak_parent_property_id = fields.Many2one('ak.property', string='Parent Property', domain=[('ak_main_property', '=', True)])
    # ak_sub_property_id = fields.Many2many('ak.property', 'ak_sub_property_ref2', 'reservation_id',
    #                                     'property_id', string='Sub Properties', domain=[('ak_main_property', '=', False)])
    ak_amount = fields.Float(string="Reservation Amount")
    client_id = fields.Char('Client ID', size=10)
    name = fields.Char('Name')
    mobile = fields.Char('Mobile')
    ak_type = fields.Selection([('case', 'Cash'), ('check', 'Cheque'), ('wire', 'Wire Transfer')], default='case', string='Payment Type')
    journal_id = fields.Many2one('account.journal', string='Journal')
    ak_account_id = fields.Many2one('account.account', string="Account", company_dependent=True)

    @api.onchange('ak_type')
    def onchange_type(self):
        '''
        Created this method to select journal automatically based on type selected
        '''
        journal_obj = self.env['account.journal']
        criteria = []
        if self.ak_type == 'case':
            criteria = [('type', '=', 'cash')]
        elif self.ak_type == 'check':
            criteria = [('type', '=', 'bank')]
        else:
            criteria = [('type', '=', 'bank')]
        return {'domain':{'journal_id':criteria}}

    @api.cr_uid_ids_context
    def property_reservation(self, cr, uid, ids, context=None):
        reservation_obj = self.pool.get('ak.reservation')
        partner_obj = self.pool.get('res.partner')
        for data in self.browse(cr, uid, ids, context=context):
            # sub_property_list = []
            # if data.ak_sub_property_id.ak_under_maintenance:
            #     raise osv.except_osv(_('Warning!'), _("You cannot reserved selected property because its already under maintenance."))
            # for each_sub_property in data.ak_sub_property_id:
            #     sub_property_list.append(each_sub_property.id)
            if not data.ak_tenant_id:
                if data.client_id:
                    if len(str(data.client_id)) < 10:
                        raise except_orm(_('Insufficient Length'), _("ID number must be of 10 digits"))
                partner_search = partner_obj.search(cr, uid, [('ak_id_number', '=', data.client_id)])
                if not partner_search:
                    partner = partner_obj.create(cr, uid, {'name': data.name,
                                            'ak_id_number': data.client_id,
                                            'mobile': data.mobile})
                    partner = partner_obj.browse(cr, uid, partner, context=context)
            reservation = reservation_obj.create(cr, uid, {'ak_tenant_id': data.ak_tenant_id.id or partner.id,
                                             'ak_property_id': data.ak_parent_property_id.id,
                                             # 'ak_sub_property_id': sub_property_list and [(6, 0, sub_property_list)] or False,
                                             'ak_user_id':uid,
                                             'ak_amount': data.ak_amount,
                                             'ak_reservation_date':datetime.now().strftime('%Y-%m-%d'),
                                             'ak_marketing_reservation': True,
                                             'ak_type':data.ak_type or False,
                                             'journal_id':data.journal_id and data.journal_id.id or False,
                                             'ak_account_id':data.ak_account_id and data.ak_account_id.id or False})

            if reservation:
                data.ak_parent_property_id.write({'ak_is_reserved': True})
            #     data.ak_sub_property_id.write({'ak_last_reservation_date':datetime.now() + timedelta(days=3), 'ak_is_reserved': True})
        return True

    @api.cr_uid_ids_context
    def default_get(self, cr, uid, fields, context=None):
        """ To get default values for the object.
        """
        if context is None:
            context = {}
        res = super(ak_reservation_client_wiz, self).default_get(cr, uid,
                                                          fields,
                                                          context=context)
        # if context and context.get('from_sub') and context.get('property_id'):
        #     property = self.pool.get('ak.property').browse(cr, uid, context['property_id'], context=context)
        #     res.update({'ak_sub_property_id': context.get('property_id') and [(6, 0, [context.get('property_id')])] or False,
        #                 'ak_parent_property_id': property.main_property_id.id})
            # return res
        if context and context.get('property_id'):
            res.update({'ak_parent_property_id': context.get('property_id')})
            return res

    # @api.onchange('ak_parent_property_id')
    # def _onchange_ak_parent_property_id(self):
    #     sub_property_ids = []
    #     if self.ak_parent_property_id.ak_sub_property_ids:
    #         for each_sub_property in self.ak_parent_property_id.ak_sub_property_ids:
    #             if not each_sub_property.ak_is_reserved:
    #                 sub_property_ids.append(each_sub_property.id)
    #     return {'domain': {'ak_sub_property_id': [('id', 'in', sub_property_ids)]}}

    @api.onchange('ak_tenant_id')
    def _onchange_tenant(self):
        tanant_obj = self.env['res.partner']
        reason = ""
        self.name = False
        self.client_id = False
        self.mobile = False
        if self.ak_tenant_id:
            self.name = self.ak_tenant_id.name
            self.mobile = self.ak_tenant_id.mobile
            self.client_id = self.ak_tenant_id.ak_id_number
            if self.ak_tenant_id.ak_reason_blacklisted:
                reason = self.ak_tenant_id.ak_reason_blacklisted
            if self.ak_tenant_id.ak_is_blacklisted:
                raise except_orm(_('Blacklisted Tenant'), _("Selected is blacklisted because of " + reason))
            if self.ak_tenant_id.ak_id_expiry_date and self.ak_tenant_id.ak_id_expiry_date < fields.Date.today():
                warning = {'message': _("You can not select this tenant because he/she is expired in propery.")}
                self.ak_tenant_id = False
                return {'warning': warning}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: