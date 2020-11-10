from functools import partial

import django_otp
from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django.urls import reverse, resolve
from django.utils.functional import SimpleLazyObject
from django_otp.middleware import OTPMiddleware as _OTPMiddleware


class VerifyUserMiddleware(_OTPMiddleware):
    _allowed_url_names = [
        "wagtail_2fa_auth",
        "wagtailadmin_login",
        "wagtailadmin_logout",
    ]

    # These URLs do not require verification if the user has no devices
    _allowed_url_names_no_device = [
        "wagtail_2fa_device_list",
        "wagtail_2fa_device_new",
        "wagtail_2fa_device_qrcode",
    ]

    def __call__(self, request):
        if hasattr(self, 'process_request'):
            response = self.process_request(request)
        if not response:
            response = self.get_response(request)
        if hasattr(self, 'process_response'):
            response = self.process_response(request, response)
        return response

    def process_request(self, request):
        if request.user:
            request.user = SimpleLazyObject(partial(self._verify_user, request, request.user))
        user = request.user
        if self._require_verified_user(request):
            user_has_device = django_otp.user_has_device(user, confirmed=True)

            if user_has_device and not user.is_verified():
                return redirect_to_login(
                    request.get_full_path(), login_url=reverse("wagtail_2fa_auth")
                )

            elif not user_has_device and settings.WAGTAIL_2FA_REQUIRED:
                # only allow the user to visit the admin index page and the
                # admin setup page
                return redirect_to_login(
                    request.get_full_path(), login_url=reverse("wagtail_2fa_device_new")
                )

    def _require_verified_user(self, request):
        user = request.user

        if not settings.WAGTAIL_2FA_REQUIRED:
            # If two factor authentication is disabled in the settings
            return False

        if not user.is_authenticated:
            return False

        # If the user has no access to the admin anyway then don't require a
        # verified user here
        if not (
            user.is_staff
            or user.is_superuser
            or user.has_perms(["wagtailadmin.access_admin"])
        ):
            return False

        # Don't require verification for specified URL names
        request_url_name = resolve(request.path_info).url_name
        if request_url_name in self._allowed_url_names:
            return False

        # If the user does not have a device, don't require verification
        # for the specified URL names
        if request_url_name in self._allowed_url_names_no_device:
            user_has_device = django_otp.user_has_device(user, confirmed=True)
            if not user_has_device:
                return False

        # For all other cases require that the user is verified via otp
        return True


class VerifyUserPermissionsMiddleware(VerifyUserMiddleware):
    """A variant of VerifyUserMiddleware which makes 2FA optional."""

    def process_request(self, request):
        result = super().process_request(request)

        # Add an attribute to the user so we can easily determine if 2FA should
        # be enabled for them.
        request.user.enable_2fa = request.user.has_perms(["wagtailadmin.enable_2fa"])

        return result

    def _require_verified_user(self, request):
        result = super()._require_verified_user(request)

        # Always require verification if the user has a device, even if they have
        # 2FA disabled.
        user_has_device = django_otp.user_has_device(request.user, confirmed=True)
        if not user_has_device and not request.user.has_perms(["wagtailadmin.enable_2fa"]):
            return False

        return result
