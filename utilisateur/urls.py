from django.urls import path

from .views import api_user_login, api_user_register, deconnxion, api_user_get_profil, api_update_password, \
    api_user_set_profil, api_user_all, api_user_get, api_user_admin_register, del_user, api_forgot_password, \
    update_password

urlpatterns = [
    path("connexion", api_user_login, name="connexion"),
    path("inscription", api_user_register, name="api_user_register"),
    path("admin/inscription", api_user_admin_register, name="api_user_register"),
    path("profile/set", api_user_set_profil, name="api_user_set_profil"),
    path("profile/del", del_user, name="api_user_set_profil"),
    path("get/<uuid:uuid>", api_user_all, name="api_user_get"),
    path("get", api_user_get, name="api_user_get"),
    path("profile/get/<uuid:uuid>", api_user_get_profil, name="api_user_get_profil"),

    path("forgot-password", api_forgot_password, name="forgot_password"),
    path(
        "update-password/<str:token>/<str:uid>/",
        update_password,
        name="update_password",
    ),
    # path(
    #     "update-password",
    #     api_update_password,
    #     name="update_password",
    # ),

    path('deconnxion', deconnxion, name="deconnxion"),
]