from __future__ import unicode_literals
import balanced

from django.conf import settings


def balanced_settings(request):
    return {
        'BALANCED': {
            'MARKETPLACE_URI': balanced.Marketplace.my_marketplace.uri,
            'DASHBOARD_URL': settings.BALANCED['DASHBOARD_URL'],
            'API_URL': settings.BALANCED['DASHBOARD_URL'],
        },
    }


def balanced_library(request):
    return {
        'balanced': balanced,
    }
