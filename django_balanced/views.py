from __future__ import unicode_literals

from django.shortcuts import render


def bank_accounts(request):
    data = {}
    return render(request, 'django_balanced/bank_account_form.html', **data)
