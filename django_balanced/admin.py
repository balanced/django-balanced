from __future__ import unicode_literals

import balanced
from django import forms
from django.conf.urls import patterns, url
from django.contrib import admin
from django.contrib.auth.models import User
from django.core import urlresolvers
from django.shortcuts import render, redirect

from django_balanced.models import BankAccount, Credit

"""
TODO:
    Generate merchant dashboard login links
    Bulk pay a set of bank accounts
    Add account URI onto django users
"""


class BalancedAdmin(admin.ModelAdmin):
    add_fields = ()
    edit_fields = ()

    def add_view(self, *args, **kwargs):
        self.fields = getattr(self, 'add_fields', self.fields)
        return super(BalancedAdmin, self).add_view(*args, **kwargs)

    def change_view(self, *args, **kwargs):
        self.fields = getattr(self, 'edit_fields', self.fields)
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

#
#    def clean(self):
#        data = self.cleaned_data
#        # TODO: validate routing number
#        #        routing_number = balanced.BankAccount(
#        #            routing_number=data['routing_number'],
#        #        )
#        #        try:
#        #            routing_number.validate()
#        #        except balanced.exc.HTTPError as ex:
#        #            if 'routing_number' in ex.message:
#        #                raise forms.ValidationError(ex.message)
#        #            raise
#        return data


class BankAccountAdmin(BalancedAdmin):
    add_fields = ('name', 'account_number', 'routing_number', 'type', 'user')
    edit_fields = ('user',)
    list_display = ['account_number', 'created_at', 'user', 'name',
                    'bank_name', 'type', 'dashboard_link']
    list_filter = ['type', 'bank_name', 'user']
    search_fields = ['name', 'account_number']
    form = BankAccountAdminForm
    actions = ['bulk_pay_action']

    def bulk_pay_action(self, request, queryset):
        return render(request, 'django_balanced/admin_confirm_bulk_pay.html', {
            'bank_accounts': enumerate(queryset),
        }, current_app=self.admin_site.name)

    bulk_pay_action.short_description = 'Credit selected accounts'

    def get_urls(self):
        urls = super(BankAccountAdmin, self).get_urls()
        my_urls = patterns('django_balanced.admin',
                           url(r'^bulk_pay/$',
                               self.admin_site.admin_view(self.bulk_pay_view),
                               name='bank_account_bulk_pay')
                           )
        return my_urls + urls

    def bulk_pay_view(self, request):
        charges = []
        index = 0
        total = 0
        while True:
            prefix = 'bank_account_%s' % index
            uri = request.POST.get(prefix)
            if not uri:
                break
            description = request.POST.get('%s_description' % prefix)
            amount = float(request.POST.get('%s_amount' % prefix))
            amount = int(amount * 100)
            bank_account = BankAccount.objects.get(pk=uri)
            total += amount
            charges.append(
                (bank_account, amount, description)
            )
            index += 1
        balanced.bust_cache()
        escrow = balanced.Marketplace.my_marketplace.in_escrow
        if total > escrow:
            raise Exception('You have insufficient funds.')
        for bank_account, amount, description in charges:
            bank_account.credit(amount, description)
        return redirect(urlresolvers.reverse('admin:index'))

    def save_model(self, request, obj, form, change):
        data = form.data
        obj.name = data['name']
        obj.account_number = data['account_number']
        obj.routing_number = data['routing_number']
        obj.type = data['type']
        if data['user']:
            obj.user = User.objects.get(pk=data['user'])
        super(BalancedAdmin, self).save_model(request, obj, form, change)


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
    add_fields = ('amount', 'bank_account', 'description')
    edit_fields = (None)
    list_display = ['user', 'bank_account', 'amount',
                    'description', 'status', 'dashboard_link']
    search_fields = ['amount', 'description', 'status']
    list_filter = ['user', 'status']
    form = CreditAdminForm

    def get_form(self, request, obj=None, **kwargs):
        if obj:
            self.exclude = ('amount',)
        return super(CreditAdmin, self).get_form(request, obj=None, **kwargs)

    def save_model(self, request, obj, form, change):
        data = form.data
        amount = int(float(data['amount']) * 100)
        bank_account = BankAccount.objects.get(pk=data['bank_account'])
        obj.amount = amount
        obj.bank_account = bank_account
        obj.user = bank_account.user
        obj.description = data['description']
        obj.save()


admin.site.register(BankAccount, BankAccountAdmin)
admin.site.register(Credit, CreditAdmin)
