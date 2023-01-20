from django.urls import path
from user.views import UserChangeView, LoginView, ProfileView
from django.contrib.auth.views import LogoutView

urlpatterns = [
    path('', UserChangeView.as_view(), name='Главная'),
    path('login/', LoginView.as_view()),
    path('logout/', LogoutView.as_view()),
    path('profile/', ProfileView.as_view()),
]