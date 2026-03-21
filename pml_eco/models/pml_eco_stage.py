# -*- coding: utf-8 -*-
from odoo import fields, models


class PmlEcoStage(models.Model):
    _name = 'pml.eco.stage'
    _description = 'ECO Stage'
    _order = 'sequence, id'

    name = fields.Char(string='Stage Name', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    is_first = fields.Boolean(
        string='Is Starting Stage',
        default=False,
        help='ECOs are always created in this stage.',
    )
    is_done = fields.Boolean(
        string='Is Done Stage',
        default=False,
        help='Marks the ECO as completed when reaching this stage.',
    )
    fold = fields.Boolean(string='Folded in Kanban', default=False)
    description = fields.Text(string='Description')

    # Approval lines for this stage
    approval_ids = fields.One2many(
        'pml.eco.stage.approval',
        'stage_id',
        string='Approvals',
    )


class PmlEcoStageApproval(models.Model):
    _name = 'pml.eco.stage.approval'
    _description = 'ECO Stage Approval Rule'

    stage_id = fields.Many2one(
        'pml.eco.stage',
        string='Stage',
        required=True,
        ondelete='cascade',
    )
    user_id = fields.Many2one(
        'res.users',
        string='User',
        required=True,
    )
    approval_type = fields.Selection([
        ('required', 'Required'),
        ('optional', 'Optional'),
    ], string='Approval Category', required=True, default='required',
        help='Required: approval is mandatory to move to next stage.\n'
             'Optional: approval is not mandatory.')
