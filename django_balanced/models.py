from __future__ import unicode_literals
from datetime import datetime

import balanced

from django.conf import settings
from django.contrib.auth.models import User
from django.db import models


class BalancedResource(models.Model):
    __resource__ = balanced.Resource
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

    def find(self):
        return self.__resource__.find(self.uri)

    @classmethod
    def sync(cls):
        for resource in cls.__resource__.query:
            try:
                existing = cls.objects.get(uri=resource.uri)
            except cls.DoesNotExist:
                existing = cls()
            existing._sync(resource)
            existing.save()

    def _sync(self, obj):
        for field in self._meta.get_all_field_names():
            has = hasattr(obj, field)
            value = has and getattr(obj, field)
            if has and isinstance(value, (basestring, int, datetime)):
                setattr(self, field, value)


class BankAccount(BalancedResource):
    __resource__ = balanced.BankAccount

    user = models.ForeignKey(User, related_name='bank_accounts', null=True)
    account_number = models.CharField(editable=False, max_length=255)
    name = models.CharField(editable=False, max_length=255)
    routing_number = models.CharField(editable=False, max_length=255)
    bank_name = models.CharField(editable=False, max_length=255)
    type = models.CharField(editable=False, max_length=255)

    class Meta:
#        app_label = 'Balanced'
        db_table = 'balanced_bank_accounts'

    def __unicode__(self):
        return '%s %s %s' % (self.user,
                             self.bank_name,
                             self.account_number)

    def save(self, **kw):
        if not self.uri:
            bank_account = self.__resource__(
                routing_number=self.routing_number,
                account_number=self.account_number,
                name=self.name,
                type=self.type,
            )
        else:
            bank_account = self.find()
        try:
            bank_account.save()
        except balanced.exc.HTTPError as ex:
            raise ex

        self._sync(bank_account)
        super(BankAccount, self).save(**kw)

    def delete(self, using=None):
        bank_account = self.find()
        bank_account.delete()
        super(BankAccount, self).delete(using)

    def credit(self, amount, description=None):
        bank_account = self.find()
        credit = bank_account.credit(amount, description)

        django_credit = Credit()
        django_credit._sync(credit)
        django_credit.bank_account = self
        django_credit.user = self.user
        django_credit.amount /= 100.0
        django_credit.save()


class Credit(BalancedResource):
    __resource__ = balanced.Credit

    user = models.ForeignKey(User,
                             related_name='credits',
                             editable=False,
                             null=True)
    bank_account = models.ForeignKey(BankAccount,
                                     related_name='credits',
                                     editable=False)
    amount = models.DecimalField(editable=False,
                                 decimal_places=2,
                                 max_digits=10)
    description = models.CharField(max_length=255, null=True)
    status = models.CharField(editable=False, max_length=255)

    class Meta:
#        app_label = 'Balanced'
        db_table = 'balanced_credits'

    def save(self, **kwargs):
        if not self.uri:
            bank_account = balanced.BankAccount.find(self.bank_account.uri)
            credit = self.__resource__(
                uri=bank_account.credits_uri,
                amount=self.amount,
                description=self.description,
            )
            try:
                credit.save()
            except balanced.exc.HTTPError as ex:
                raise ex
        else:
            credit = self.find()

        self._sync(credit)
        self.amount = credit.amount / 100.0
        if not self.bank_account_id:
            bank_account = BankAccount.objects.get(pk=credit.bank_account.uri)
            self.bank_account = bank_account

        super(Credit, self).save(**kwargs)

    def delete(self, using=None):
        raise NotImplemented
