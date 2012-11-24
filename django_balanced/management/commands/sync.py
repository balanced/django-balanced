from __future__ import unicode_literals

import balanced
from django.conf import settings
from django.core.management.base import BaseCommand

from django_balanced.models import BankAccount, Credit


class Command(BaseCommand):
    help = 'Synchronizes your Balanced credits and bank accounts with your ' \
           'local system'

    def handle(self, *args, **options):
        balanced.configure(settings.BALANCED['API_KEY'])
        BankAccount.sync()
        Credit.sync()
