"""AGROTECH accounts — User personalizado (FASE 4, decisión B).

Identidad oficial: AbstractBaseUser + PermissionsMixin, email como
USERNAME_FIELD, UUID como PK. account_status es el estado de negocio;
is_active es técnico y se sincroniza: ACTIVE -> True, resto -> False.
"""

import uuid

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models

from .managers import UserManager


class User(AbstractBaseUser, PermissionsMixin):
    class AccountStatus(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        SUSPENDED = "SUSPENDED", "Suspended"
        DEACTIVATED = "DEACTIVATED", "Deactivated"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email_verified = models.BooleanField(default=False)
    account_status = models.CharField(
        max_length=12, choices=AccountStatus.choices, default=AccountStatus.ACTIVE
    )
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    def save(self, *args, **kwargs):
        # Decisión B: sincronizar técnico con negocio.
        self.is_active = self.account_status == self.AccountStatus.ACTIVE
        super().save(*args, **kwargs)

    def __str__(self):
        return self.email


class EmailOTP(models.Model):
    """Desafío OTP de login por correo (feature/auth-email-otp).

    El challenge_id liga el código a UN intento concreto de login
    (tras contraseña válida). Sin sesión Django a medio autenticar:
    la sesión definitiva nace solo en django_login() post-OTP.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    challenge_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="email_otps"
    )
    code_hash = models.CharField(max_length=128)
    expires_at = models.DateTimeField()
    attempts = models.PositiveIntegerField(default=0)
    max_attempts = models.PositiveIntegerField(default=5)
    used_at = models.DateTimeField(null=True, blank=True)
    superseded_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["challenge_id"])]

    @property
    def is_usable(self) -> bool:
        from django.utils import timezone

        return (
            self.used_at is None
            and self.superseded_at is None
            and self.expires_at > timezone.now()
            and self.attempts < self.max_attempts
        )

    def __str__(self):
        return f"OTP {self.challenge_id} ({self.user})"
