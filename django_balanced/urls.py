from django.conf.urls import patterns, url


urlpatterns = patterns(
    'django_balanced.views',
    url(r'^bank_accounts/$', 'bank_account'),
)
