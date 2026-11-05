from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path(
        "login/",
        views.AccountLoginView.as_view(template_name="accounts/login.html"),
        name="login",
    ),
    path("logout/", views.account_logout, name="logout"),
    path("", views.home, name="home"),
]
