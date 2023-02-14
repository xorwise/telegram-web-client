from django.db import models
# Create your models here.
from django.contrib.auth.models import AbstractBaseUser
from django.utils import timezone


from django.contrib.auth.base_user import BaseUserManager

from django.contrib.auth.models import PermissionsMixin


class CustomUserManager(BaseUserManager):
    """
    Custom user model manager where email is the unique identifiers
    for authentication instead of usernames.
    """
    def create_user(self, email, password, **extra_fields):
        """
        Create and save a user with the given email and password.
        """
        if not email:
            raise ValueError("The Email must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, email, password, **extra_fields):
        """
        Create and save a SuperUser with the given email and password.
        """
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self.create_user(email, password, **extra_fields)


class CustomUser(AbstractBaseUser, PermissionsMixin):
    """ Model of a custom user """
    id = models.AutoField(primary_key=True)
    email = models.EmailField('Почта', max_length=255, unique=True, blank=False)
    first_name = models.CharField('Имя', max_length=100, default='', blank=True)
    last_name = models.CharField('Фамилия', max_length=100, default='', blank=True)
    telegram = models.CharField('Телеграм', max_length=100, default='', blank=True)
    telegram_sessions = models.ManyToManyField('telegram_api.TelegramSession', db_column='Сессии телеграм', blank=True)
    active_session = models.CharField('Активная телеграм сессия', max_length=1000, default='', blank=True)

    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)
    USERNAME_FIELD = 'email'

    objects = CustomUserManager()

    def __str__(self):
        return self.email
