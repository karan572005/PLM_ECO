# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError


class PmlEcoApproval(models.Model):
    _name = 'pml.eco.approval'
    _description = 'ECO Approval'

    eco_id = fields.Many2one(
        'pml.eco',
        string='ECO',
        required=True,
        ondelete='cascade',
    )
    stage_id = fields.Many2one(
        'pml.eco.stage',
        string='Stage',
        required=True,
    )
    user_id = fields.Many2one(
        'res.users',
        string='Approver',
        required=True,
    )
    approval_type = fields.Selection([
        ('required', 'Required'),
        ('optional', 'Optional'),
    ], string='Approval Category', required=True, default='required')
    status = fields.Selection([
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('refused', 'Refused'),
    ], string='Status', default='pending', required=True)
    date_approved = fields.Datetime(string='Approved On', readonly=True)
    comment = fields.Char(string='Comment')

    def action_approve(self):
        for rec in self:
            if rec.user_id.id != self.env.uid:
                raise UserError('Only %s can approve this.' % rec.user_id.name)
            rec.write({
                'status': 'approved',
                'date_approved': fields.Datetime.now(),
            })
            rec.eco_id._check_approvals()

    def action_refuse(self):
        for rec in self:
            if rec.user_id.id != self.env.uid:
                raise UserError('Only %s can refuse this.' % rec.user_id.name)
            rec.write({'status': 'refused'})
