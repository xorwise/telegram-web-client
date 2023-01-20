from django import forms


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

