# -*- coding: utf-8 -*-
{
    'name': 'PML Engineering Change Orders',
    'version': '18.0.0.1',
    'category': 'Manufacturing',
    'summary': 'Manage Engineering Change Orders for Products and Bills of Materials',
    'author': 'PML',
    'depends': ['base', 'mail', 'auth_signup','uom'],
    'data': [
        'security/pml_security.xml',
        'security/ir.model.access.csv',
        'data/pml_sequence_data.xml',
        'data/pml_eco_stage_data.xml',
        'data/server_action.xml',
        'views/pml_product_views.xml',
        'views/pml_bom_views.xml',
        'views/pml_eco_stage_views.xml',
        'views/pml_eco_approval_views.xml',
        'views/pml_eco_views.xml',
        'views/pml_eco_changes_views.xml',
        'views/pml_menu_views.xml',
        'views/pml_report_views.xml',

    ],
    'demo': [
        'demo/pml_product_demo.xml',
        'demo/pml_bom_demo.xml',
        'demo/pml_eco_demo.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
