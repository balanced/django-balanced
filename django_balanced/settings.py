import importlib

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


def load_path_attr(path):
    i = path.rfind(".")
    module, attr = path[:i], path[i + 1:]
    try:
        mod = importlib.import_module(module)
    except ImportError, e:
        raise ImproperlyConfigured("Error importing %s: '%s'" % (module, e))
    try:
        attr = getattr(mod, attr)
    except AttributeError:
        raise ImproperlyConfigured(
            "Module '%s' does not define a '%s'" % (module, attr))
    return attr


BALANCED = getattr(settings, 'BALANCED', {})
BALANCED.setdefault('DASHBOARD_URL', 'https://www.balancedpayments.com')
BALANCED.setdefault('API_URL', 'https://api.balancedpayments.com')

installed_apps = getattr(settings, 'INSTALLED_APPS', ())
ctx_processors = getattr(settings, 'TEMPLATE_CONTEXT_PROCESSORS', [])
middlware_clss = getattr(settings, 'MIDDLEWARE_CLASSES', ())

installed_apps += (
    'django_balanced',
)
ctx_processors = [
    'django_balanced.context_processors.balanced_settings',
    'django.contrib.auth.context_processors.auth',
]
middlware_clss += (
    'django_balanced.middleware.BalancedMiddleware',
)

settings.INSTALLED_APPS = installed_apps
settings.TEMPLATE_CONTEXT_PROCESSORS = ctx_processors
settings.MIDDLEWARE_CLASSES = middlware_clss

if not BALANCED.get('API_KEY'):
    raise ImproperlyConfigured('You must set the BALANCED_API_KEY environment '
                               'variable.')
