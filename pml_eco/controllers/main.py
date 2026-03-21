from odoo import http
from odoo.http import request
from odoo.addons.web.controllers.home import Home
class LoginRedirect(Home):

    @http.route('/web/login', type='http', auth="public", website=True)
    def web_login(self, redirect=None, **kw):
        # Call original login
        response = super().web_login(redirect=redirect, **kw)
        print("called")
        # Check login success
        if request.session.uid:
            user = request.env.user
            print(user.name)
            action = request.env.ref('pml_eco.action_pml_eco').id
            menu = request.env.ref('pml_eco.menu_pml_eco_root').id

            if user.has_group('base.group_portal'):
                return request.redirect(f'/web#action={action}&menu_id={menu}')


            elif user.has_group('base.group_user'):
                return request.redirect('/my')

            # elif user.has_group('your_module.your_group'):
            #     return request.redirect('/web#action=384')

            return request.redirect('/web')

        return response