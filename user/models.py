from django.db import models
# Create your models here.
from django.contrib.auth.models import AbstractUser


class CustomUser(AbstractUser):
    email = models.CharField('Почта', max_length=255, blank=True, unique=True)
    first_name = models.CharField('Имя', max_length=100, default='', blank=True)
    last_name = models.CharField('Фамилия', max_length=100, default='', blank=True)
    phone = models.CharField('Телефон', max_length=15, default='', blank=True)
    telegram = models.CharField('Телеграм', max_length=100, default='', blank=True)
    telegram_session = models.CharField('Телеграм cессия', max_length=1000, blank=True)
