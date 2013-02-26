from __future__ import unicode_literals
from datetime import datetime

import balanced

from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.db.models.signals import post_save


class BalancedException(Exception):
    pass


class BalancedResource(models.Model):
    _resource = balanced.Resource
    id = models.CharField(max_length=255, editable=False)
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
        return self._resource.find(self.uri)

    @classmethod
    def sync(cls):
        for resource in cls._resource.query:
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
    _resource = balanced.BankAccount

    user = models.ForeignKey(User,
                             related_name='bank_accounts',
                             null=True)
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
            bank_account = self._resource(
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

        return django_credit


class Card(BalancedResource):
    _resource = balanced.Card

    user = models.ForeignKey(User,
                             related_name='cards',
                             null=False)
    name = models.CharField(editable=False, max_length=255)
    expiration_month = models.IntegerField(editable=False)
    expiration_year = models.IntegerField(editable=False)
    last_four = models.CharField(editable=False, max_length=4)
    brand = models.CharField(editable=False, max_length=255)

    class Meta:
    #        app_label = 'Balanced'
        db_table = 'balanced_cards'

    @classmethod
    def create_from_card_uri(cls, user, card_uri):
        card = cls(user=user)
        card.save(card_uri)
        return card

    def save(self, card_uri=None, **kwargs):
        # a card must be saved elsewhere since we don't store the data required
        # to create a card from the django object
        if not self.uri:
            account = self.user.balanced_account.find()
            account.add_card(card_uri=card_uri)
            self.uri = card_uri
        card = self.find()
        self._sync(card)

        super(Card, self).save(**kwargs)

    def delete(self, using=None):
        card = self.find()
        card.is_valid = False
        card.save()
        super(Card, self).delete(using)

    def debit(self, amount, description):
        account = self.user.balanced_account
        return account.debit(
            amount=amount,
            description=description,
            card=self,
        )


class Credit(BalancedResource):
    _resource = balanced.Credit

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
            bank_account = self.bank_account.find()
            credit = self._resource(
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


class Debit(BalancedResource):
    _resource = balanced.Debit

    user = models.ForeignKey(User,
                             related_name='debits',
                             null=False)
    amount = models.DecimalField(editable=False,
                                 decimal_places=2,
                                 max_digits=10)
    description = models.CharField(editable=False, max_length=255)
    card = models.ForeignKey(Card,
                             related_name='debits',
                             editable=False)

    class Meta:
    #        app_label = 'Balanced'
        db_table = 'balanced_debits'

    def save(self, **kwargs):
        if not self.uri:
            account = self.user.balanced_account.find()
            try:
                self.card
            except ObjectDoesNotExist:
                self.card = self.user.cards.all()[0]
            debit = account.debit(
                amount=self.amount,
                description=self.description,
                source_uri=self.card.uri,
            )
            try:
                debit.save()
            except balanced.exc.HTTPError as ex:
                raise ex
        else:
            debit = self.find()

        self._sync(debit)
        super(Debit, self).save(**kwargs)

    def delete(self, using=None):
        raise NotImplemented


class Account(BalancedResource):
    _resource = balanced.Account

    user = models.OneToOneField(User, related_name='balanced_account')

    class Meta:
        db_table = 'balanced_accounts'

    def save(self, **kwargs):
        if not self.uri:
            ac = balanced.Account(
                name=self.user.username,
            )
            try:
                ac.save()
            except balanced.exc.HTTPError as ex:
                raise ex
            self._sync(ac)

        super(Account, self).save(**kwargs)

    def debit(self, amount, description, card=None):
        debit = Debit(
            amount=amount,
            description=description,
            user=self.user,
        )
        if card:
            debit.card = card
        debit.save()
        return debit

    def delete(self, using=None):
        raise NotImplemented


# this will create an account per user when they are next saved. subsequent
# saves will not make a network call.
def create_user_profile(sender, instance, created, **kwargs):
    Account.objects.get_or_create(user=instance)


post_save.connect(create_user_profile, sender=User)
