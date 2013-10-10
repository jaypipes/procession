# Server Specific Configurations
server = {
    'port': '80',
    'host': '0.0.0.0'
}

# Pecan Application Configurations
app = {
    'root': 'procession.api.controllers.RootController',
    'modules': ['procession.api'],
    'static_root': '%(confdir)s/public',
    'template_path': '%(confdir)s/procession/api/templates',
    'debug': False,
    'enable_acl': False,
}
