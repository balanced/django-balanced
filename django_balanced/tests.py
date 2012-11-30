from __future__ import unicode_literals

import balanced
from django.test import TestCase
import mock

from django_balanced import models


# https://www.balancedpayments.com/docs/testing
FIXTURES = {
    'card': {
        'card_number': 4111111111111111,
        'expiration_month': 12,
        'expiration_year': 2020,
    },
    'bank_account': {
        'account_number': 123123123,
        'routing_number': 321174851,  # SMCU
        'type': 'savings',
        'name': 'dan carter',
    }
}


class ModelsTest(TestCase):

    @classmethod
    def setUpClass(cls):
        with balanced.key_switcher(None):
            cls.api_key = balanced.APIKey().save()
        balanced.configure(cls.api_key.secret)
        cls.marketplace = balanced.Marketplace().save()
        cls.card = balanced.Card(**FIXTURES['card']).save()
        cls.buyer = balanced.Account(card_uri=cls.card.uri).save()
        # put some money in the escrow account
        cls.buyer.debit(100 * 100)  # $100.00

    def setUp(self):
        pass

    def test_create_credit(self):
        pass

    def test_update_credit(self):
        pass

    def test_create_bank_account(self):
        bank_account = models.BankAccount(**FIXTURES['bank_account'])
        bank_account.save()
        self.assertTrue(bank_account.bank_name)
        self.assertTrue(bank_account.uri)

    def test_update_bank_account(self):
        pass
