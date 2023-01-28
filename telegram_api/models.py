from django.db import models
from django.contrib.postgres.fields import ArrayField
from user.models import CustomUser
from django.conf import settings
from django.core.files import File

class TelegramSession(models.Model):
    """ Model of a Telegram session"""
    phone = models.CharField(max_length=255, primary_key=True)
    session = models.CharField(max_length=1000)


class Channel(models.Model):
    """ Model of a Telegram channel """
    id = models.BigIntegerField(primary_key=True)
    title = models.CharField(max_length=255, blank=True)


class SearchRequest(models.Model):
    """ Model of a search request by keywords """
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, db_column='user', blank=True,
                             null=True)
    client_phone = models.CharField(max_length=15, blank=True)
    channels = ArrayField(models.CharField(max_length=255))
    keywords = ArrayField(models.CharField(max_length=100))
    groups = models.ManyToManyField(Channel, related_name='groups', blank=True)
    is_active = models.BooleanField(default=True)
    added_messages = ArrayField(models.IntegerField(), blank=True, default=list)


class ParsedRequest:
    """ Search request parser to html view """
    id: int
    channels: str
    keywords: str
    groups: str
    last_checked: str
    is_active: bool
    client_phone: str

    def __init__(self, request: SearchRequest, groups):
        self.id = request.id
        self.channels = request.channels
        new_groups = list()
        for group in groups:
            new_groups.append(group.title)
        self.keywords = '; '.join(request.keywords)
        self.groups = '; '.join(new_groups)
        self.is_active = request.is_active
        self.client_phone = request.client_phone


class MailingRequest(models.Model):
    id = models.AutoField(primary_key=True)
    message_title = models.CharField(max_length=100)
    message_text = models.TextField()
    message_images = ArrayField(models.ImageField(), blank=True)
    message_files = ArrayField(models.FileField(), blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    client_phone = models.CharField(max_length=15, blank=True)
    is_active = models.BooleanField(default=True)
    is_instant = models.BooleanField(default=False)
    send_time = ArrayField(models.DateTimeField(), blank=True)

    def __str__(self):
        return self.message_title

    def save(self, *args, **kwargs):
        for file in self.message_files:
            with open(f'/media/{file.name[0]}', 'w') as f:
                file.save(file.filename, File(f))

        for image in self.message_images:
            with open(f'/media/{image.name[0]}', 'w') as f:
                image.save(image.filename, File(f))
        super().save()
