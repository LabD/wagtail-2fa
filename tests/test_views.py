import pytest
from django.core.exceptions import PermissionDenied
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.test import override_settings
from unittest.mock import patch
from django.http.response import Http404

from django.contrib.auth import get_user_model
from django.urls import reverse
from django_otp import DEVICE_ID_SESSION_KEY
from django_otp.plugins.otp_totp.models import TOTPDevice
from wagtail_2fa.views import DeviceListView, DeviceDeleteView, DeviceUpdateView

def test_device_list_view(admin_client, admin_user, django_assert_max_num_queries):
    with override_settings(WAGTAIL_2FA_REQUIRED=True):
        admin_device = TOTPDevice.objects.create(name='Initial', user=admin_user, confirmed=True)

        session = admin_client.session
        session[DEVICE_ID_SESSION_KEY] = admin_device.persistent_id
        session.save()


        with django_assert_max_num_queries(13):
            response = admin_client.get(reverse('wagtail_2fa_device_list',
                                        kwargs={'user_id': admin_user.id}))
            assert response.status_code == 200


def test_device_list_create(admin_client, django_assert_max_num_queries):
    with override_settings(WAGTAIL_2FA_REQUIRED=True):
        with django_assert_max_num_queries(10):
            response = admin_client.get(reverse('wagtail_2fa_device_new'))
            assert response.status_code == 200

        with patch("django_otp.plugins.otp_totp.models.TOTPDevice.verify_token") as fn:
            fn.return_value = True
            response = admin_client.post(
                reverse('wagtail_2fa_device_new'), {
                    'name': 'Test device',
                    'otp_token': '123456',
                    'password': 'password',
                })

        assert response.status_code == 302, response.context['form'].errors
        assert TOTPDevice.objects.filter(confirmed=True).count() == 1


def test_device_list_update(admin_client, monkeypatch):
    with override_settings(WAGTAIL_2FA_REQUIRED=True):
        user = get_user_model().objects.filter(is_staff=True).first()
        instance = TOTPDevice.objects.create(name='Initial', user=user, confirmed=True)

        monkeypatch.setattr(TOTPDevice, 'verify_token', lambda self, value: True)

        # Login with 2fa
        endpoint = reverse('wagtail_2fa_auth')
        response = admin_client.post(endpoint, {'otp_token': '123456', 'next': '/cms/'})
        assert response.status_code == 302,  response.context['form'].errors

        # Get update view
        endpoint = reverse('wagtail_2fa_device_update', kwargs={'pk': instance.pk})
        response = admin_client.get(endpoint)
        assert response.status_code == 200

        # Post new name
        response = admin_client.post(endpoint, {
            'name': 'Test device',
            'password': 'password',
        })
        assert response.status_code == 302, response.context['form'].errors
        assert TOTPDevice.objects.filter(name='Test device').count() == 1


def test_device_qr(admin_client, monkeypatch):
    with override_settings(WAGTAIL_2FA_REQUIRED=True):
        user = get_user_model().objects.filter(is_staff=True).first()
        TOTPDevice.objects.create(name='Initial', user=user, confirmed=False)

        # Get update view
        endpoint = reverse('wagtail_2fa_device_qrcode')
        response = admin_client.get(endpoint)
        assert response.status_code == 200


def test_delete_user_device_as_admin(client, admin_user, user, monkeypatch):
    with override_settings(WAGTAIL_2FA_REQUIRED=True):
        device = TOTPDevice.objects.create(name='Initial', user=user, confirmed=True)

        # verify admin
        admin_device = TOTPDevice.objects.create(name='Initial', user=admin_user, confirmed=True)

        client.login(username="admin", password="password")

        session = client.session
        session[DEVICE_ID_SESSION_KEY] = admin_device.persistent_id
        session.save()

        assert TOTPDevice.objects.all().count() == 2

        endpoint = reverse('wagtail_2fa_device_remove', kwargs={'pk': device.id})
        response = client.post(endpoint, {
            'user_id': user.id
        })
        assert response.status_code == 302
        print(response)
        assert TOTPDevice.objects.all().count() == 1

def test_delete_user_device_as_admin_unverified(admin_client, user, monkeypatch):
    with override_settings(WAGTAIL_2FA_REQUIRED=True):
        user = get_user_model().objects.filter(is_staff=False).first()
        device = TOTPDevice.objects.create(name='Initial', user=user, confirmed=True)

        endpoint = reverse('wagtail_2fa_device_remove', kwargs={'pk': device.id})
        response = admin_client.post(endpoint, {
            'user_id': user.id
        })
        assert response.status_code == 302

        new_device_url = reverse('wagtail_2fa_device_new')
        assert response.url == f"{new_device_url}?next={endpoint}"
        assert TOTPDevice.objects.all().count() == 1


def test_delete_user_device_unauthorized(client, user, monkeypatch):
    with override_settings(WAGTAIL_2FA_REQUIRED=True):
        user = get_user_model().objects.filter(is_staff=False).first()
        device = TOTPDevice.objects.create(name='Initial', user=user, confirmed=True)

        endpoint = reverse('wagtail_2fa_device_remove', kwargs={'pk': device.id})
        response = client.post(endpoint, {
            'user_id': user.id
        })
        assert response.status_code == 302
        assert TOTPDevice.objects.all().count() == 1


class TestViewsChangeUserPermission:
    """Test suite which ensures that:
        - users without the change_user permission cannot manage other users' 2FA devices
        - users can manage their own devices
    """

    def test_verified_user_has_no_change_user_perm(self, verified_user):
        """Sanity check."""
        assert not verified_user.has_perm("user.change_user")

    def test_device_list_view_for_own_user_returns_200(self, verified_user, rf):
        with override_settings(WAGTAIL_2FA_REQUIRED=True):
            request = rf.get('foo')
            request.user = verified_user

            response = DeviceListView.as_view()(request, user_id=verified_user.id)
            assert response.status_code == 200

    def test_device_list_view_for_other_user_raises_error(self, user, verified_user, rf):
        with override_settings(WAGTAIL_2FA_REQUIRED=True):
            request = rf.get('foo')
            request.user = verified_user

            with pytest.raises(PermissionDenied):
                response = DeviceListView.as_view()(request, user_id=user.id)

    def test_device_delete_view_for_own_user_returns_200(self, verified_user, rf):
        with override_settings(WAGTAIL_2FA_REQUIRED=True):
            device = TOTPDevice.objects.devices_for_user(verified_user, confirmed=True).first()
            request = rf.get('foo')
            request.user = verified_user

            response = DeviceDeleteView.as_view()(request, pk=device.id)
            assert response.status_code == 200

    def test_device_delete_view_for_other_user_raises_error(self, user, verified_user, rf):
        with override_settings(WAGTAIL_2FA_REQUIRED=True):
            other_device = TOTPDevice.objects.create(name='Initial', user=user, confirmed=True)

            device = TOTPDevice.objects.devices_for_user(verified_user, confirmed=True).first()
            request = rf.get('foo')
            request.user = verified_user

            with pytest.raises(PermissionDenied):
                response = DeviceDeleteView.as_view()(request, pk=other_device.id)

    def test_device_update_view_for_own_user_returns_200(self, verified_user, rf):
        with override_settings(WAGTAIL_2FA_REQUIRED=True):
            device = TOTPDevice.objects.devices_for_user(verified_user, confirmed=True).first()
            request = rf.get('foo')
            request.user = verified_user

            response = DeviceUpdateView.as_view()(request, pk=device.id)
            assert response.status_code == 200

    def test_device_update_view_for_other_user_raises_error(self, user, verified_user, rf):
        with override_settings(WAGTAIL_2FA_REQUIRED=True):
            other_device = TOTPDevice.objects.create(name='Initial', user=user, confirmed=True)

            device = TOTPDevice.objects.devices_for_user(verified_user, confirmed=True).first()
            request = rf.get('foo')
            request.user = verified_user

            with pytest.raises(Http404):
                response = DeviceUpdateView.as_view()(request, pk=other_device.id)
