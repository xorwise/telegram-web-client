from django.db import models
from django.contrib.postgres.fields import ArrayField
from user.models import CustomUser
from django.conf import settings


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


class File(models.Model):
    file = models.FileField()


class MailingRequest(models.Model):
    id = models.AutoField(primary_key=True)
    message_title = models.CharField(max_length=100)
    message_text = models.TextField()
    message_images = models.ManyToManyField(File, blank=True, related_name='mailing_images')
    message_files = models.ManyToManyField(File, blank=True, related_name='mailing_files')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    client_phone = models.CharField(max_length=15, blank=True)
    is_active = models.BooleanField(default=True)
    is_instant = models.BooleanField(default=False)
    groups = models.ManyToManyField(Channel, blank=True, related_name="mailing_groups")
    send_time = ArrayField(models.DateTimeField(null=True), blank=True, null=True)

    def __str__(self):
        return self.message_title
