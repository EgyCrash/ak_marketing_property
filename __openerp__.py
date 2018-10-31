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


{
    'name': 'Property Marketing',
    'version': '1.0',
    'category': 'Property Marketing Management',
    'sequence': 1,
    'description': """
    Marketing management for properties.
    """,
    'author': "Crevisoft.com",
    'email':"Info@crevisoft.com",
    'website': "www.crevisoft.com",
    'depends': [
        "ak_akhawen",
        "mass_mailing",
        ],
    'data': [
        "security/security.xml",
        "security/ir.model.access.csv",
        "views/ak_marketing_property.xml",
        "wizard/ak_marketing_reservation_wiz_view.xml",
        "views/marketing_view.xml",
        "marketing_menu.xml" ,
        "marketing_data.xml",
    ],
    'demo': [],
    'installable': True,
    'auto_install': False,
    'application': True,
}