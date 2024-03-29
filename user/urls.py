from django.urls import path
from user.views import LoginView, ProfileView, RegisterView
from django.contrib.auth.views import LogoutView

urlpatterns = [
    path('login/', LoginView.as_view()),
    path('logout/', LogoutView.as_view()),
    path('profile/', ProfileView.as_view()),
    path('register/', RegisterView.as_view()),
]