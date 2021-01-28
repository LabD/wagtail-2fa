import pytest
from django.conf import settings


def pytest_configure():
    settings.configure(
        ROOT_URLCONF='tests.urls',
        MIDDLEWARE=[
            'django.middleware.security.SecurityMiddleware',
            'django.contrib.sessions.middleware.SessionMiddleware',
            'django.middleware.common.CommonMiddleware',
            'django.middleware.csrf.CsrfViewMiddleware',
            'django.contrib.auth.middleware.AuthenticationMiddleware',
            'django.contrib.messages.middleware.MessageMiddleware',
            'django.middleware.clickjacking.XFrameOptionsMiddleware',
            'wagtail_2fa.middleware.VerifyUserMiddleware',
        ],
        STATIC_URL='/static/',
        INSTALLED_APPS=[
            'wagtail.contrib.forms',
            'wagtail.contrib.redirects',
            'wagtail.embeds',
            'wagtail.sites',
            'wagtail.users',
            'wagtail.snippets',
            'wagtail.documents',
            'wagtail.images',
            'wagtail.search',
            'wagtail.admin',
            'wagtail.core',
            'wagtail.contrib.modeladmin',

            'modelcluster',
            'taggit',

            'django.contrib.admin',
            'django.contrib.auth',
            'django.contrib.contenttypes',
            'django.contrib.sessions',
            'django.contrib.messages',
            'django.contrib.staticfiles',

            'wagtail_2fa',
            'django_otp',
            'django_otp.plugins.otp_totp',
        ],
        TEMPLATES=[
            {
                'BACKEND': 'django.template.backends.django.DjangoTemplates',
                'DIRS': [],
                'APP_DIRS': True,
                'OPTIONS': {
                    'context_processors': [
                        'django.template.context_processors.debug',
                        'django.template.context_processors.request',
                        'django.contrib.auth.context_processors.auth',
                        'django.contrib.messages.context_processors.messages',
                    ],
                },
            },
        ],
        CACHES={
            'default': {
                'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
                'LOCATION': 'unique-snowflake',
            }
        },
        DATABASES={
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': 'db.sqlite',
            },
        }
    )


@pytest.fixture()
def rf():
    """A RequestFactory instance."""

    from django.contrib.auth.models import AnonymousUser
    from django.contrib.messages.storage.fallback import FallbackStorage
    from django.contrib.sessions.backends.db import SessionStore
    from django.test.client import RequestFactory as BaseRequestFactory

    class RequestFactory(BaseRequestFactory):

        def request(self, user=None, **request):
            request = super().request(**request)
            request.user = AnonymousUser()
            request.session = SessionStore()
            request._messages = FallbackStorage(request)
            return request

    return RequestFactory()


@pytest.fixture
def user(django_user_model):
    return django_user_model.objects.create(username='test-user')


@pytest.fixture
def verified_user(django_user_model, rf):
    """Create a user and verify it using the OTP middleware. Add a device
    to complete the verification for the user."""
    from django_otp.plugins.otp_totp.models import TOTPDevice
    from django_otp.middleware import OTPMiddleware as _OTPMiddleware
    user = django_user_model.objects.create(username='verified-user')
    device = TOTPDevice.objects.create(user=user, confirmed=True)
    request = rf.get('/foo/')
    request.user = user
    middleware = _OTPMiddleware()
    user = middleware._verify_user(request, user)
    user.otp_device = device
    return user


@pytest.fixture
def superuser(django_user_model):
    return django_user_model.objects.create(
        username='super-user', is_superuser=True, is_staff=True)


@pytest.fixture
def staff_user(django_user_model):
    return django_user_model.objects.create(
        username='staff-user', is_superuser=False, is_staff=True)
