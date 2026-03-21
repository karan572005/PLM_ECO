from odoo import http
from odoo.http import request
from odoo.addons.web.controllers.home import Home


class LoginRedirect(Home):

    @http.route('/web/login', type='http', auth="public", website=True)
    def web_login(self, redirect=None, **kw):
        response = super().web_login(redirect=redirect, **kw)
        if request.session.uid:
            user = request.env.user

            # Admin (id=2) — let through normally, sees everything
            if user.id == 2:
                return response

            if user.has_group('base.group_user'):
                action = request.env.ref('pml_eco.action_pml_eco').id
                menu = request.env.ref('pml_eco.menu_pml_eco_root').id
                return request.redirect(f'/web#action={action}&menu_id={menu}')

            if user.has_group('base.group_portal'):
                return request.redirect('/my')

        return response


try:
    from odoo.addons.auth_signup.controllers.main import AuthSignupHome

    class CustomSignup(AuthSignupHome):

        def do_signup(self, qcontext):
            super().do_signup(qcontext)
            login = qcontext.get('login')
            if not login:
                return

            user = request.env['res.users'].sudo().search(
                [('login', '=', login)], limit=1
            )
            if not user:
                return

            # 1. Convert portal → internal user
            portal_group = request.env.ref('base.group_portal').sudo()
            internal_group = request.env.ref('base.group_user').sudo()
            portal_group.write({'users': [(3, user.id)]})   # remove portal
            internal_group.write({'users': [(4, user.id)]}) # add internal

            # 2. Assign PLM Operations group
            plm_group = request.env.ref('pml_eco.group_plm_operations').sudo()
            plm_group.write({'users': [(4, user.id)]})

            # 3. Set home action → so back button always opens your module
            action = request.env.ref('pml_eco.action_pml_eco').sudo()
            user.sudo().write({'action_id': action.id})

except ImportError:
    pass