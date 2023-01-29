from django import forms


class RegisterForm(forms.Form):
    email = forms.EmailField()
    phone = forms.CharField(max_length=15)
    password1 = forms.CharField(max_length=100, widget=forms.PasswordInput)
    password2 = forms.CharField(max_length=100, widget=forms.PasswordInput)


class ProfileForm(forms.Form):
    email = forms.EmailField(required=False)
    first_name = forms.CharField(max_length=100, required=False)
    last_name = forms.CharField(max_length=100, required=False)
    phone = forms.CharField(max_length=15, required=False)
    telegram = forms.CharField(max_length=100, required=False)

