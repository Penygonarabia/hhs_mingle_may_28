def post_init_hook(env):
    """Set Chart Color Palette to 'custom-1' for all bar and pie charts across all dashboards."""
    chart_types = [
        'ks_bar_chart',
        'ks_horizontalBar_chart',
        'ks_pie_chart',
        'ks_doughnut_chart',
    ]
    items = env['ks_dashboard_ninja.item'].search([
        ('ks_dashboard_item_type', 'in', chart_types),
    ])
    if items:
        items.write({'ks_chart_item_color': 'custom-1'})
