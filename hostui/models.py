from django.conf import settings
from django.db import models


class Tenant(models.Model):
    name = models.CharField("Назва громади", max_length=200)
    slug = models.SlugField("Код", max_length=50, unique=True)
    is_active = models.BooleanField("Активна", default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Громада"
        verbose_name_plural = "Громади"

    def __str__(self):
        return self.name


class UserProfile(models.Model):
    class Role(models.TextChoices):
        SECRETAR = "secretar", "Секретар"
        LAWYER = "lawyer", "Юрист"
        VIEWER = "viewer", "Перегляд"
        ADMIN_GROMADA = "admin_gromada", "Адмін громади"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.PROTECT,
        related_name="users",
        verbose_name="Громада",
    )
    role = models.CharField(
        max_length=32,
        choices=Role.choices,
        default=Role.VIEWER,
    )

    class Meta:
        verbose_name = "Профіль користувача"
        verbose_name_plural = "Профілі користувачів"

    def __str__(self):
        return f"{self.user.username} @ {self.tenant.slug} ({self.role})"