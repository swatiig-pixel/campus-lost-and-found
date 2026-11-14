from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):

    class Role(models.TextChoices):
        STUDENT = 'STUDENT', 'Student'
        ADMIN = 'ADMIN', 'Admin'

    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.STUDENT
    )

    # Student profile fields
    full_name = models.CharField(max_length=200, blank=True)
    usn = models.CharField(
        max_length=20,
        unique=True,
        blank=True,
        null=True,
        verbose_name='USN'
    )
    phone_number = models.CharField(max_length=15, blank=True)
    department = models.CharField(max_length=100, blank=True)
    semester = models.PositiveSmallIntegerField(null=True, blank=True)

    def __str__(self):
        return self.username

    @property
    def is_student(self):
        return self.role == self.Role.STUDENT

    @property
    def is_admin_user(self):
        return self.role == self.Role.ADMIN or self.is_staff or self.is_superuser

    class Meta:
        db_table = 'accounts_user'
        indexes = [
            models.Index(fields=['email'], name='idx_user_email'),
            models.Index(fields=['usn'], name='idx_user_usn'),
            models.Index(fields=['role'], name='idx_user_role'),
        ]