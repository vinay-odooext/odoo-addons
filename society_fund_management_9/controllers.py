# -*- coding: utf-8 -*-
from openerp import http

# class SocietyFundManagement(http.Controller):
#     @http.route('/society_fund_management/society_fund_management/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/society_fund_management/society_fund_management/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('society_fund_management.listing', {
#             'root': '/chit_fund_management/society_fund_management',
#             'objects': http.request.env['society_fund_management.society_fund_management'].search([]),
#         })

#     @http.route('/society_fund_management/society_fund_management/objects/<model("society_fund_management.society_fund_management"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('society_fund_management.object', {
#             'object': obj
#         })
