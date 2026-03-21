# -*- coding: utf-8 -*-
from odoo import api, fields, models


class PmlEcoChanges(models.Model):
    _name = 'pml.eco.changes'
    _description = 'ECO Changes Comparison'

    eco_id = fields.Many2one(
        'pml.eco',
        string='ECO',
        required=True,
        ondelete='cascade',
    )
    eco_type = fields.Selection(
        related='eco_id.eco_type',
        string='ECO Type',
        store=True,
    )

    # ── BoM change lines ──────────────────────────────────────────────────────
    bom_component_change_ids = fields.One2many(
        'pml.eco.changes.bom.line',
        'changes_id',
        string='Component Changes',
    )
    bom_operation_change_ids = fields.One2many(
        'pml.eco.changes.operation.line',
        'changes_id',
        string='Operation Changes',
    )

    # ── Product change lines ──────────────────────────────────────────────────
    product_change_ids = fields.One2many(
        'pml.eco.changes.product.line',
        'changes_id',
        string='Product Field Changes',
    )

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            rec._populate_changes()
        return records

    def _populate_changes(self):
        """Auto-populate change lines from linked BoM or Product."""
        self.ensure_one()
        eco = self.eco_id

        if eco.eco_type == 'bill_of_material' and eco.bill_of_material_id:
            bom = eco.bill_of_material_id
            for comp in bom.component_ids:
                self.env['pml.eco.changes.bom.line'].create({
                    'changes_id': self.id,
                    'product_id': comp.product_id.id,
                    'old_qty': comp.quantity,
                    'new_qty': comp.quantity,
                    'uom_id': comp.uom_id.id,
                    'change_type': 'unchanged',
                })
            for op in bom.operation_ids:
                self.env['pml.eco.changes.operation.line'].create({
                    'changes_id': self.id,
                    'operation_name': op.name,
                    'old_duration': op.duration,
                    'new_duration': op.duration,
                    'change_type': 'unchanged',
                })

        elif eco.eco_type == 'product' and eco.pml_product_id:
            product = eco.pml_product_id
            for field_name, label in [
                ('sales_price', 'Sales Price'),
                ('cost_price', 'Cost Price'),
            ]:
                self.env['pml.eco.changes.product.line'].create({
                    'changes_id': self.id,
                    'field_label': label,
                    'old_value': str(getattr(product, field_name, '')),
                    'new_value': str(getattr(product, field_name, '')),
                    'change_type': 'unchanged',
                })


class PmlEcoChangesBomLine(models.Model):
    _name = 'pml.eco.changes.bom.line'
    _description = 'ECO BoM Component Change Line'

    changes_id = fields.Many2one(
        'pml.eco.changes',
        string='ECO Changes',
        required=True,
        ondelete='cascade',
    )
    product_id = fields.Many2one(
        'pml.product',
        string='Component',
        required=True,
    )
    old_qty = fields.Float(string='Old Qty', default=0.0)
    new_qty = fields.Float(string='New Qty', default=0.0)
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure')
    change_type = fields.Selection([
        ('added', 'Added'),
        ('removed', 'Removed'),
        ('modified', 'Modified'),
        ('unchanged', 'Unchanged'),
    ], string='Change', compute='_compute_change_type', store=True, readonly=False)

    @api.depends('old_qty', 'new_qty')
    def _compute_change_type(self):
        for rec in self:
            if rec.old_qty == 0 and rec.new_qty > 0:
                rec.change_type = 'added'
            elif rec.old_qty > 0 and rec.new_qty == 0:
                rec.change_type = 'removed'
            elif rec.old_qty != rec.new_qty:
                rec.change_type = 'modified'
            else:
                rec.change_type = 'unchanged'    # Colour helper for list view decoration
    color = fields.Char(compute='_compute_color')

    @api.depends('change_type')
    def _compute_color(self):
        mapping = {
            'added': 'green',
            'removed': 'red',
            'modified': 'orange',
            'unchanged': 'black',
        }
        for rec in self:
            rec.color = mapping.get(rec.change_type, 'black')


class PmlEcoChangesOperationLine(models.Model):
    _name = 'pml.eco.changes.operation.line'
    _description = 'ECO Operation Change Line'

    changes_id = fields.Many2one(
        'pml.eco.changes',
        string='ECO Changes',
        required=True,
        ondelete='cascade',
    )
    operation_name = fields.Char(string='Operation', required=True)
    old_duration = fields.Float(string='Old Duration (min)', default=0.0)
    new_duration = fields.Float(string='New Duration (min)', default=0.0)
    change_type = fields.Selection([
        ('added', 'Added'),
        ('removed', 'Removed'),
        ('modified', 'Modified'),
        ('unchanged', 'Unchanged'),
    ], string='Change', compute='_compute_change_type', store=True, readonly=False)

    @api.depends('old_duration', 'new_duration')
    def _compute_change_type(self):
        for rec in self:
            if rec.old_duration == 0 and rec.new_duration > 0:
                rec.change_type = 'added'
            elif rec.old_duration > 0 and rec.new_duration == 0:
                rec.change_type = 'removed'
            elif rec.old_duration != rec.new_duration:
                rec.change_type = 'modified'
            else:
                rec.change_type = 'unchanged'


class PmlEcoChangesProductLine(models.Model):
    _name = 'pml.eco.changes.product.line'
    _description = 'ECO Product Field Change Line'

    changes_id = fields.Many2one(
        'pml.eco.changes',
        string='ECO Changes',
        required=True,
        ondelete='cascade',
    )
    field_label = fields.Char(string='Field', required=True)
    old_value = fields.Char(string='Old Value (Version 1)')
    new_value = fields.Char(string='New Value (Version 2)')
    change_type = fields.Selection([
        ('added', 'Added'),
        ('removed', 'Removed'),
        ('modified', 'Modified'),
        ('unchanged', 'Unchanged'),
    ], string='Change', compute='_compute_change_type', store=True, readonly=False)

    @api.depends('old_value', 'new_value')
    def _compute_change_type(self):
        for rec in self:
            if not rec.old_value and rec.new_value:
                rec.change_type = 'added'
            elif rec.old_value and not rec.new_value:
                rec.change_type = 'removed'
            elif rec.old_value != rec.new_value:
                rec.change_type = 'modified'
            else:
                rec.change_type = 'unchanged'