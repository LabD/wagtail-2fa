from django import forms
from django.contrib.auth import authenticate
from django.utils.translation import gettext_lazy as _
from django_otp.forms import OTPAuthenticationFormMixin
from django_otp.plugins.otp_totp.models import TOTPDevice


class TokenForm(OTPAuthenticationFormMixin, forms.Form):
    otp_token = forms.CharField(required=True)

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

        self.fields["otp_token"].widget.attrs.update(
            {"autofocus": "autofocus", "autocomplete": "off"}
        )

    def clean(self):
        self.clean_otp(self.user)
        return self.cleaned_data


class DeviceForm(forms.ModelForm):
    otp_token = forms.CharField(
        label=_("OTP token"),
        required=True,
        help_text=_(
            "Enter the numeric code displayed on your device after scanning the QR code"
        ),
    )

    name = forms.CharField(
        label=_("Name"),
        required=True,
        help_text=_("The human-readable name of this device."),
    )

    password = forms.CharField(
        label=_("Current password"),
        help_text=_("As an extra security measurement we need your current password"),
        widget=forms.PasswordInput(),
    )

    class Meta:
        model = TOTPDevice
        fields = ["name", "otp_token"]

    def __init__(self, request, **kwargs):
        super().__init__(**kwargs)
        self.fields["otp_token"].widget.attrs.update(
            {"autofocus": "autofocus", "autocomplete": "off"}
        )
        if self.instance.confirmed:
            del self.fields["otp_token"]

        self.request = request

    def clean_otp_token(self):
        token = self.cleaned_data.get("otp_token")

        if token and self.instance.verify_token(token):
            return token

        raise forms.ValidationError(
            _("Invalid token. Please make sure you have entered it correctly."),
            code="invalid",
        )

    def clean_password(self):
        password = self.cleaned_data.get("password")
        if not authenticate(
            self.request, username=self.request.user.get_username(), password=password
        ):
            raise forms.ValidationError(_("Invalid password"))

    def save(self):
        self.instance.confirmed = True
        self.instance.save()
