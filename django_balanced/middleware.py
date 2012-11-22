from __future__ import unicode_literals

import balanced
from django.conf import settings


class BalancedMiddleware(object):

    def process_request(*_):
        balanced.configure(settings.BALANCED['API_KEY'])
