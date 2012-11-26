# django-balanced

## How to send ACH payments in 10 minutes

1. Visit www.balancedpayments.com and get yourself an API key
2. `pip install django-balanced`
3. Edit your `settings.py` and add the API key like so:

        import os

        BALANCED = {
            'API_KEY': os.environ.get('BALANCED_API_KEY'),
        }

4. Add `django_balanced` to your `INSTALLED_APPS` in `settings.py`

        INSTALLED_APPS = (
           ...
           'django.contrib.admin',  # if you want to use the admin interface
           'django_balanced',
           ...
        )

5. Run `BALANCED_API_KEY=YOUR_API_KEY django-admin.py syncdb`
6. Run `BALANCED_API_KEY=YOUR_API_KEY python manage.py runserver`
7. Visit `http://127.0.0.1:8000/admin` and pay some people!
