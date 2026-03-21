# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError

class PmlBom(models.Model):
    _name = 'pml.bom'
    _description = 'PML Bill of Materials'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(
        string='Reference',
        required=True,
        copy=False,
        default='New',
        tracking=True,
        help='Auto-generated reference.',
    )
    product_id = fields.Many2one(
        'pml.product',
        string='Finished Product',
        required=True,
        ondelete='restrict',
        tracking=True,
        domain=[('status', '=', 'active')],
    )
    quantity = fields.Float(
        string='Quantity',
        default=1.0,
        required=True,
    )
    uom_id = fields.Many2one(
        'uom.uom',
        string='Unit of Measure',
        required=True,
        default=lambda self: self.env.ref('uom.product_uom_unit', raise_if_not_found=False),
    )
    version = fields.Integer(
        string='Version',
        default=1,
        readonly=True,
        copy=False,
        help='Version updates only when ECO of this BoM is applied.',
    )
    status = fields.Selection([
        ('active', 'Active'),
        ('archived', 'Archived'),
    ], string='Status', default='active', required=True, tracking=True)

    component_ids = fields.One2many(
        'pml.bom.component',
        'bom_id',
        string='Components',
    )
    operation_ids = fields.One2many(
        'pml.bom.operation',
        'bom_id',
        string='Operations',
    )

    # ECO back-reference
    eco_ids = fields.One2many(
        'pml.eco',
        'bill_of_material_id',
        string='ECOs',
    )
    eco_count = fields.Integer(
        string='ECO Count',
        compute='_compute_eco_count',
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals['name'] == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('pml.bom') or 'New'
        return super().create(vals_list)

    def write(self, vals):
        for rec in self:
            if rec.status == 'archived' and 'status' not in vals:
                raise UserError(
                    'Bill of Materials "%s" is archived and cannot be modified.' % rec.name
                )
        return super().write(vals)

    def copy(self, default=None):
        default = default or {}
        new_bom = super().copy(default)
        return new_bom

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
            'domain': [('bill_of_material_id', '=', self.id)],
            'context': {'default_bill_of_material_id': self.id},
        }

    def action_archive(self):
        self.write({'status': 'archived'})

    def action_unarchive(self):
        self.write({'status': 'active'})

    def name_get(self):
        result = []
        for rec in self:
            result.append((rec.id, '%s (v%s)' % (rec.name, rec.version)))
        return result


class PmlBomComponent(models.Model):
    _name = 'pml.bom.component'
    _description = 'PML BoM Component'

    bom_id = fields.Many2one(
        'pml.bom',
        string='Bill of Materials',
        required=True,
        ondelete='cascade',
    )
    product_id = fields.Many2one(
        'pml.product',
        string='Component',
        required=True,
        domain=[('status', '=', 'active')],
    )
    quantity = fields.Float(
        string='Quantity',
        default=1.0,
        required=True,
    )
    uom_id = fields.Many2one(
        'uom.uom',
        string='Unit of Measure',
        required=True,
        default=lambda self: self.env.ref('uom.product_uom_unit', raise_if_not_found=False),
    )
    to_consume = fields.Float(
        string='To Consume',
        default=0.0,
    )


class PmlBomOperation(models.Model):
    _name = 'pml.bom.operation'
    _description = 'PML BoM Operation'

    bom_id = fields.Many2one(
        'pml.bom',
        string='Bill of Materials',
        required=True,
        ondelete='cascade',
    )
    name = fields.Char(
        string='Operation',
        required=True,
    )
    work_center = fields.Char(
        string='Work Center',
    )
    duration = fields.Float(
        string='Expected Duration (min)',
        default=0.0,
    )

