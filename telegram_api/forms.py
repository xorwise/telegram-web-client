from django import forms
from telegram_api.models import MailingRequest


class PhoneForm(forms.Form):
    phone = forms.CharField(max_length=150)


class ConfirmForm(forms.Form):
    code = forms.IntegerField()
    password = forms.CharField(max_length=255, required=False)


class SearchForm(forms.Form):
    choices = tuple()

    def __init__(self, dialogs: list):
        choices1 = list()
        for dialog in dialogs:
            choices1.append((str(dialog.entity.id), dialog.name))
        self.choices = tuple(choices1)
        super().__init__()

    channels = forms.MultipleChoiceField(choices=choices)
    keywords = forms.CharField(max_length=255)
    groups = forms.CharField(max_length=255)


class MailingForm(forms.ModelForm):

    class Meta:
        model = MailingRequest
        fields = ('message_title', 'message_text', 'message_images', 'message_files', 'groups', 'is_instant', 'send_time')