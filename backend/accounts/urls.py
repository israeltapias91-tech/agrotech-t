"""AGROTECH accounts — rutas de verificación de email."""

from django.urls import path

from .views import EmailChangeView, EmailResendView, EmailVerifyView

urlpatterns = [
    path("email/verify/", EmailVerifyView.as_view(), name="email-verify"),
    path("email/resend/", EmailResendView.as_view(), name="email-resend"),
    path("email/change/", EmailChangeView.as_view(), name="email-change"),
]
