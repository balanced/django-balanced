from __future__ import unicode_literals

import balanced
from django.conf import settings
from django.db.models import signals

from django_balanced import models
from django_balanced.models import BankAccount, Credit

__author__ = 'marshall'


def configure_balanced(*args, **kwargs):
    balanced.configure(settings.BALANCED['API_KEY'])


def sync_balanced(app, created_models, verbosity, db, **kwargs):
    BankAccount.sync()
    Credit.sync()

signals.post_syncdb.connect(
    sync_balanced, 
    sender=models, 
    dispatch_uid="django_balanced.management.sync_balanced"
)
# the pre_syncdb signal is supported in a later version
# only connect to it when it exists
if hasattr(signals, 'pre_syncdb'):
    signals.pre_syncdb.connect(
        configure_balanced, 
        sender=models, 
        dispatch_uid="django_balanced.management.pre_syncdb"
    )
else:
    # well... this is a little bit dirty, but it works
    # as syncdb imports management package for all apps
    # before doing syncdb
    configure_balanced()
