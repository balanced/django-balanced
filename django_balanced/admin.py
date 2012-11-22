from __future__ import unicode_literals

import balanced
from django import forms
from django.contrib import admin
from django.contrib.auth.models import User

from django_balanced.models import BankAccount, Credit

"""
TODO:
    Generate merchant dashboard login links
    Bulk pay a set of bank accounts
    Add account URI onto django users
"""


class BalancedAdmin(admin.ModelAdmin):
    add_exclude = ()
    edit_exclude = ()

    def add_view(self, *args, **kwargs):
        self.exclude = getattr(self, 'add_exclude', self.exclude)
        return super(BalancedAdmin, self).add_view(*args, **kwargs)

    def change_view(self, *args, **kwargs):
        self.exclude = getattr(self, 'edit_exclude', self.exclude)
        return super(BalancedAdmin, self).change_view(*args, **kwargs)


class BankAccountAdminForm(forms.ModelForm):
    name = forms.CharField(max_length=255)
    account_number = forms.CharField(max_length=255)
    routing_number = forms.CharField(max_length=255)
    type = forms.ChoiceField(choices=(
        ('savings', 'savings'), ('checking', 'checking')
        ))
    user = forms.ModelChoiceField(queryset=User.objects, required=False)

    class Meta:
        model = BankAccount

    def clean(self):
        data = self.cleaned_data
        # TODO: validate routing number
        #        routing_number = balanced.BankAccount(
        #            routing_number=data['routing_number'],
        #        )
        #        try:
        #            routing_number.validate()
        #        except balanced.exc.HTTPError as ex:
        #            if 'routing_number' in ex.message:
        #                raise forms.ValidationError(ex.message)
        #            raise
        return data


class BankAccountAdmin(BalancedAdmin):
    fields = ('name', 'account_number', 'routing_number', 'type', 'user')
    edit_exclude = ('name', 'account_number', 'routing_number', 'type')
    list_display = ['account_number', 'created_at', 'user', 'name',
                    'bank_name', 'type', 'dashboard_link']
    search_fields = ['name', 'account_number']
    form = BankAccountAdminForm

    def save_model(self, request, obj, form, change):
        user = form.data['user']
        meta = {}
        if user:
            meta['user'] = user
        if not obj:
            bank_account = balanced.BankAccount(
                routing_number=form.data['routing_number'],
                account_number=form.data['account_number'],
                name=form.data['name'],
                type=form.data['type'],
                meta=meta,
            )
        else:
            bank_account = balanced.BankAccount.find(form.data['uri'])
            bank_account.meta = meta
        try:
            bank_account.save()
        except balanced.exc.HTTPError as ex:
            if 'routing_number' in ex.message:
                raise forms.ValidationError(ex.message)
            raise
        obj.uri = bank_account.uri
        obj.created_at = bank_account.created_at
        obj.account_number = bank_account.account_number
        obj.bank_name = bank_account.bank_name
        obj.routing_number = bank_account.routing_number
        obj.type = bank_account.type
        obj.name = bank_account.name
        obj.save()


class CreditAdminForm(forms.ModelForm):
    amount = forms.DecimalField(max_digits=10, required=True)
    description = forms.CharField(max_length=255, required=False)
    bank_account = forms.ModelChoiceField(queryset=BankAccount.objects)

    class Meta:
        model = Credit

    def clean(self):
        if not self.is_valid():
            return self.cleaned_data
        data = self.cleaned_data
        balanced.bust_cache()
        escrow = balanced.Marketplace.my_marketplace.in_escrow
        amount = int(float(data['amount']) * 100)
        if amount > escrow:
            raise forms.ValidationError('You have insufficient funds to cover '
                                        'this transfer.')
        return data


class CreditAdmin(BalancedAdmin):
    fields = ('amount', 'bank_account', 'description')
    edit_exclude = ('amount', 'bank_account')
    list_display = ['user', 'bank_account', 'amount',
                    'description', 'status', 'dashboard_link']
    search_fields = ['amount', 'description', 'status'],
    form = CreditAdminForm

    def get_form(self, request, obj=None, **kwargs):
        if obj:
            self.exclude = ('amount',)
        return super(CreditAdmin, self).get_form(request, obj=None, **kwargs)

    def save_model(self, request, obj, form, change):
        if not obj:
            amount = int(float(form.data['amount']) * 100)
            bank_account = balanced.BankAccount.find(form.data['bank_account'])
            credit = balanced.Credit(
                uri=bank_account.credits_uri,
                amount=amount,
                description=form.data['description'],
            )
        else:
            credit = balanced.Credit.find(obj.uri)
            credit.description = form.data['description']
        try:
            credit.save()
        except balanced.exc.HTTPError as ex:
            raise ex
        bank_account = BankAccount.objects.get(pk=credit.bank_account.uri)
        obj.amount = credit.amount / 100.0
        obj.created_at = credit.created_at
        obj.description = credit.description
        obj.bank_account = bank_account
        obj.user = bank_account.user
        obj.status = credit.status
        obj.uri = credit.uri
        obj.save()


admin.site.register(BankAccount, BankAccountAdmin)
admin.site.register(Credit, CreditAdmin)
