from __future__ import unicode_literals

import balanced

from django.conf import settings
from django.contrib.auth.models import User
from django.db import models


class BalancedResource(models.Model):
    uri = models.CharField(primary_key=True, max_length=255, editable=False)
    created_at = models.DateTimeField(auto_created=True, editable=False)

    class Meta:
        abstract = True

    def dashboard_link(self):
        return '<a href="%s%s" target="_blank">View on Balanced</a>' % (
            settings.BALANCED['DASHBOARD_URL'],
            self.uri[3:]
        )
    dashboard_link.allow_tags = True

    def sync(self):
        pass


class BankAccount(BalancedResource):
    user = models.ForeignKey(User, related_name='bank_accounts', null=True)
    account_number = models.CharField(editable=False, max_length=255)
    name = models.CharField(editable=False, max_length=255)
    routing_number = models.CharField(editable=False, max_length=255)
    bank_name = models.CharField(editable=False, max_length=255)
    type = models.CharField(editable=False, max_length=255)

    class Meta:
        app_label = 'Balanced'
        db_table = 'balanced_bank_accounts'

    def __unicode__(self):
        return '%s %s %s' % (self.user.username,
                             self.bank_name,
                             self.account_number)


class Credit(BalancedResource):
    user = models.ForeignKey(User,
                             related_name='credits',
                             editable=False)
    bank_account = models.ForeignKey(BankAccount,
                                     related_name='credits',
                                     null=True,
                                     editable=False)
    amount = models.DecimalField(editable=False,
                                 decimal_places=2,
                                 max_digits=10)
    description = models.CharField(max_length=255, null=True)
    status = models.CharField(editable=False, max_length=255)

    class Meta:
        app_label = 'Balanced'
        db_table = 'balanced_credits'

    def sync(self):
        ba = balanced.BankAccount.find(self.uri)
        self.status = ba.status
