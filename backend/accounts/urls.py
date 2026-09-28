"""AGROTECH accounts — verificación + login/logout/sesión."""

from django.urls import path

from .views import (
    EmailChangeView,
    EmailResendView,
    EmailVerifyView,
    LoginView,
    LogoutView,
    SessionView,
)

urlpatterns = [
    path("email/verify/", EmailVerifyView.as_view(), name="email-verify"),
    path("email/resend/", EmailResendView.as_view(), name="email-resend"),
    path("email/change/", EmailChangeView.as_view(), name="email-change"),
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("session/", SessionView.as_view(), name="session"),
]
