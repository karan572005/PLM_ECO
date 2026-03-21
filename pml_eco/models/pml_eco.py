# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class PmlEco(models.Model):
    _name = 'pml.eco'
    _description = 'Engineering Change Order'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    # ─── Core Fields ───────────────────────────────────────────────────────────

    name = fields.Char(
        string='Title',
        required=True,
        tracking=True,
    )
    eco_type = fields.Selection([
        ('bill_of_material', 'Bills of Materials'),
        ('product', 'Product'),
    ], string='ECO Type', required=True, tracking=True)

    pml_product_id = fields.Many2one(
        'pml.product',
        string='PML Product',
        ondelete='restrict',
        tracking=True,
        domain=[('status', '=', 'active')],
    )
    bill_of_material_id = fields.Many2one(
        'pml.bom',
        string='Bill of Materials',
        ondelete='restrict',
        tracking=True,
        domain=[('status', '=', 'active')],
    )
    user_id = fields.Many2one(
        'res.users',
        string='User',
        required=True,
        default=lambda self: self.env.user,
        tracking=True,
    )
    effective_date = fields.Datetime(
        string='Effective Date',
        tracking=True,
        help='Auto-populated when ECO reaches Done stage.',
    )
    version_update = fields.Boolean(
        string='Version Update',
        default=False,
        help='If checked, version field on the related Product/BoM will increment when ECO is Done.',
    )
    note = fields.Html(string='Note')

    # ─── Stage / Status ────────────────────────────────────────────────────────

    stage_id = fields.Many2one(
        'pml.eco.stage',
        string='Stage',
        tracking=True,
        group_expand='_read_group_stage_ids',
        default=lambda self: self._default_stage(),
    )
    # Derived colour for kanban/list badge
    state_color = fields.Selection([
        ('green', 'Approved'),
        ('white', 'In Progress'),
        ('red', 'Cancelled'),
    ], string='State Color', compute='_compute_state_color', store=True)

    is_done = fields.Boolean(
        related='stage_id.is_done',
        string='Is Done',
        store=True,
    )

    # Legacy status kept for compatibility & statusbar widget
    status = fields.Selection([
        ('draft', 'New'),
        ('in_progress', 'In Progress'),
        ('approved', 'Approved'),
        ('done', 'Done'),
        ('canceled', 'Canceled'),
    ], string='Status', default='draft', required=True, copy=False, tracking=True)

    eco_applied = fields.Boolean(
        string='ECO Applied',
        default=False,
        readonly=True,
        copy=False,
    )

    # ─── Relations ─────────────────────────────────────────────────────────────

    approval_ids = fields.One2many(
        'pml.eco.approval',
        'eco_id',
        string='Approvals',
    )
    changes_id = fields.One2many(
        'pml.eco.changes',
        'eco_id',
        string='Changes',
    )

    # ─── Computed counts for stat buttons ──────────────────────────────────────

    approval_count = fields.Integer(
        string='Approvals',
        compute='_compute_approval_count',
    )
    pending_approval_count = fields.Integer(
        string='Pending Approvals',
        compute='_compute_approval_count',
    )

    # ─── Defaults ──────────────────────────────────────────────────────────────

    def _default_stage(self):
        stage = self.env['pml.eco.stage'].search(
            [('is_first', '=', True)], limit=1
        )
        return stage or self.env['pml.eco.stage'].search([], order='sequence', limit=1)

    @api.model
    def _read_group_stage_ids(self, stages, domain):
        return self.env['pml.eco.stage'].search([])

    # ─── Constraints ───────────────────────────────────────────────────────────

    @api.constrains('eco_type', 'bill_of_material_id')
    def _check_bom_required(self):
        for rec in self:
            if rec.eco_type == 'bill_of_material' and not rec.bill_of_material_id:
                raise ValidationError(
                    'Bill of Materials is required when ECO Type is "Bills of Materials".'
                )

    # ─── Onchange ──────────────────────────────────────────────────────────────

    @api.onchange('eco_type')
    def _onchange_eco_type(self):
        if self.eco_type != 'bill_of_material':
            self.bill_of_material_id = False

    @api.onchange('user_id')
    def _onchange_user_id(self):
        if not self.user_id:
            self.user_id = self.env.user

    # ─── Computes ──────────────────────────────────────────────────────────────

    @api.depends('approval_ids', 'approval_ids.status')
    def _compute_approval_count(self):
        for rec in self:
            rec.approval_count = len(rec.approval_ids)
            rec.pending_approval_count = len(
                rec.approval_ids.filtered(lambda a: a.status == 'pending')
            )

    @api.depends('status')
    def _compute_state_color(self):
        mapping = {
            'approved': 'green',
            'done': 'green',
            'canceled': 'red',
        }
        for rec in self:
            rec.state_color = mapping.get(rec.status, 'white')

    # ─── Actions ───────────────────────────────────────────────────────────────

    def action_start(self):
        """Start the ECO - validate mandatory fields then lock them."""
        for rec in self:
            if not rec.name:
                raise UserError('Title is required before starting.')
            if not rec.eco_type:
                raise UserError('ECO Type is required before starting.')
            if not rec.pml_product_id:
                raise UserError('Product is required before starting.')
            if not rec.user_id:
                raise UserError('User is required before starting.')
            if rec.eco_type == 'bill_of_material' and not rec.bill_of_material_id:
                raise UserError('Bill of Materials is required before starting.')

            # Load approvals from current stage rules
            rec._load_stage_approvals()

            rec.write({'status': 'in_progress'})

    def action_approve(self):
        """Approve button - only the designated approver can click."""
        self.ensure_one()
        my_approval = self.approval_ids.filtered(
            lambda a: a.user_id.id == self.env.uid and a.status == 'pending'
        )
        if not my_approval:
            raise UserError(
                'You are not an approver for this ECO or you have already approved it.'
            )
        my_approval.action_approve()

    def action_validate(self):
        """No-approval path: directly validate/done."""
        for rec in self:
            rec._apply_eco()

    def action_cancel(self):
        for rec in self:
            rec.write({'status': 'canceled'})

    def action_reset_draft(self):
        for rec in self:
            rec.write({'status': 'draft'})
            rec.approval_ids.unlink()

    def action_view_bill_of_materials(self):
        self.ensure_one()
        if not self.bill_of_material_id:
            raise UserError('No Bill of Materials linked to this ECO.')
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'pml.bom',
            'res_id': self.bill_of_material_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_view_product(self):
        self.ensure_one()
        if not self.pml_product_id:
            raise UserError('No PML Product linked to this ECO.')
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'pml.product',
            'res_id': self.pml_product_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_view_changes(self):
        self.ensure_one()
        if not self.changes_id:
            self.env['pml.eco.changes'].create({'eco_id': self.id})
        changes = self.changes_id[0]
        return {
            'type': 'ir.actions.act_window',
            'name': '%s — ECO Changes' % self.name,
            'res_model': 'pml.eco.changes',
            'res_id': changes.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_view_approvals(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Approvals',
            'res_model': 'pml.eco.approval',
            'view_mode': 'list,form',
            'domain': [('eco_id', '=', self.id)],
            'context': {'default_eco_id': self.id},
        }

    # ─── Business Logic ────────────────────────────────────────────────────────

    def _load_stage_approvals(self):
        """Create approval records from the stage's approval rules."""
        self.ensure_one()
        if not self.stage_id:
            return
        existing_users = self.approval_ids.mapped('user_id')
        for rule in self.stage_id.approval_ids:
            if rule.user_id not in existing_users:
                self.env['pml.eco.approval'].create({
                    'eco_id': self.id,
                    'stage_id': self.stage_id.id,
                    'user_id': rule.user_id.id,
                    'approval_type': rule.approval_type,
                    'status': 'pending',
                })

    def _check_approvals(self):
        """Called after an approval action - check if all required approvals are done."""
        self.ensure_one()
        required = self.approval_ids.filtered(
            lambda a: a.approval_type == 'required'
        )
        all_approved = all(a.status == 'approved' for a in required)
        if all_approved and required:
            self.write({'status': 'approved'})
            self.message_post(body='All required approvals received. ECO is Approved.')

    def _apply_eco(self):
        """Apply the ECO: create new version, archive old, set effective date."""
        self.ensure_one()
        now = fields.Datetime.now()

        if self.eco_type == 'bill_of_material' and self.bill_of_material_id:
            old_bom = self.bill_of_material_id

            if self.version_update:
                # CREATE new BoM as copy of old
                new_bom = old_bom.copy({
                    'version': old_bom.version + 1,
                    'status': 'active',
                })
                # ARCHIVE old BoM
                old_bom.write({'status': 'archived'})
                # Point ECO to new BoM
                self.write({'bill_of_material_id': new_bom.id})

                if self.changes_id:
                    changes = self.changes_id[0]

                    for change_line in changes.bom_component_change_ids:
                        # Find matching component in new BoM
                        matching = new_bom.component_ids.filtered(
                            lambda c: c.product_id.id == change_line.product_id.id
                        )
                        if change_line.change_type == 'removed':
                            # Delete component from new BoM
                            matching.unlink()

                        elif change_line.change_type == 'added':
                            # Add new component to new BoM
                            if not matching:
                                self.env['pml.bom.component'].create({
                                    'bom_id': new_bom.id,
                                    'product_id': change_line.product_id.id,
                                    'quantity': change_line.new_qty,
                                    'uom_id': change_line.uom_id.id,
                                })

                        elif change_line.change_type == 'modified':
                            # Update quantity in new BoM
                            if matching:
                                matching.write({'quantity': change_line.new_qty})

                    for op_line in changes.bom_operation_change_ids:
                        # Find matching operation in new BoM
                        matching_op = new_bom.operation_ids.filtered(
                            lambda o: o.name == op_line.operation_name
                        )
                        if op_line.change_type == 'removed':
                            matching_op.unlink()

                        elif op_line.change_type == 'added':
                            if not matching_op:
                                self.env['pml.bom.operation'].create({
                                    'bom_id': new_bom.id,
                                    'name': op_line.operation_name,
                                    'duration': op_line.new_duration,
                                })

                        elif op_line.change_type == 'modified':
                            if matching_op:
                                matching_op.write({'duration': op_line.new_duration})
            else:
                # No version update — just keep same BoM active
                old_bom.write({'status': 'active'})

        elif self.eco_type == 'product' and self.pml_product_id:
            old_product = self.pml_product_id

            if self.version_update:
                # CREATE new Product as copy of old
                new_product = old_product.copy({
                    'version': old_product.version + 1,
                    'status': 'active',
                })
                # ARCHIVE old Product
                old_product.write({'status': 'archived'})
                # Point ECO to new Product
                self.write({'pml_product_id': new_product.id})

                if self.changes_id:
                    changes = self.changes_id[0]
                    update_vals = {}

                    for change_line in changes.product_change_ids:
                        if change_line.change_type == 'modified':
                            if change_line.field_label == 'Sales Price':
                                update_vals['sales_price'] = float(
                                    change_line.new_value or 0
                                )
                            elif change_line.field_label == 'Cost Price':
                                update_vals['cost_price'] = float(
                                    change_line.new_value or 0
                                )
                    if update_vals:
                        new_product.write(update_vals)
            else:
                old_product.write({'status': 'active'})

        self.write({
            'status': 'done',
            'effective_date': now,
            'eco_applied': True,
        })
        self.message_post(
            body='ECO Applied. Effective Date: %s' % now
        )

    def approve_eco(self):
        """Legacy method - kept for backward compatibility."""
        self.action_approve()
