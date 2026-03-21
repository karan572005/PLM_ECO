# -*- coding: utf-8 -*-
from odoo import api, fields, models


class PmlProduct(models.Model):
    _name = 'pml.product'
    _description = 'PML Product'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(
        string='Product Name',
        required=True,
        size=255,
        tracking=True,
    )
    sales_price = fields.Monetary(
        string='Sales Price',
        currency_field='currency_id',
        tracking=True,
    )
    cost_price = fields.Monetary(
        string='Cost Price',
        currency_field='currency_id',
        tracking=True,
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
    )
    version = fields.Integer(
        string='Version',
        default=1,
        readonly=True,
        copy=False,
        help='Version is updated automatically when a related ECO is applied.',
    )
    attachment_ids = fields.Many2many(
        'ir.attachment',
        'pml_product_attachment_rel',
        'product_id',
        'attachment_id',
        string='Attachments',
    )
    status = fields.Selection([
        ('active', 'Active'),
        ('archived', 'Archived'),
    ], string='Status', default='active', required=True, tracking=True)

    # ECO back-reference
    eco_ids = fields.One2many(
        'pml.eco',
        'pml_product_id',
        string='ECOs',
    )
    eco_count = fields.Integer(
        string='ECO Count',
        compute='_compute_eco_count',
    )

    @api.depends('eco_ids')
    def _compute_eco_count(self):
        for rec in self:
            rec.eco_count = len(rec.eco_ids)

    def action_view_ecos(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'ECOs',
            'res_model': 'pml.eco',
            'view_mode': 'list,form',
            'domain': [('pml_product_id', '=', self.id)],
            'context': {'default_pml_product_id': self.id},
        }

    def action_archive(self):
        self.write({'status': 'archived'})

    def action_unarchive(self):
        self.write({'status': 'active'})

    @api.constrains('status')
    def _check_archived_readonly(self):
        """Archived products cannot be edited."""
        for rec in self:
            if rec.status == 'archived':
                # Post a message — actual readonly enforced via view
                pass

    def write(self, vals):
        for rec in self:
            if rec.status == 'archived' and 'status' not in vals:
                from odoo.exceptions import UserError
                raise UserError(
                    'Product "%s" is archived and cannot be modified.' % rec.name
                )
        return super().write(vals)