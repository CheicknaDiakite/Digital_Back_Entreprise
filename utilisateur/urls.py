from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import api_user_login, api_user_register, deconnxion, api_user_get_profil, api_update_password, \
    api_user_set_profil, api_user_all, api_user_get, api_user_admin_register, del_user, api_forgot_password, \
    update_password, api_mes_user_all, api_user_cabinet_register, UserAdminRegisterView
from .voirs import CustomTokenObtainPairView, UserProfileView, AllUsersView, RegisterView, UserGetAPIView, UserUnView

urlpatterns = [
    path("register", RegisterView.as_view(), name="register"),
    path("login", CustomTokenObtainPairView.as_view(), name="connexion"),
    path("token/refresh", TokenRefreshView.as_view(), name="token_refresh"),
    path("user/profil", UserProfileView.as_view(), name="user-profile"),
    path("user/<uuid:uuid>", UserUnView.as_view(), name="user-profile"),
    path("user/all", AllUsersView.as_view(), name="all-users"),
    # path("get", UserGetAPIView.as_view(), name="api_user_get"),

    path("connexion", api_user_login, name="connexion"),
    path("inscription", api_user_register, name="api_user_register"),
    path("admin/inscription", UserAdminRegisterView.as_view(), name="api_user_register"),
    path("admin/cabinet", api_user_cabinet_register, name="api_user_cabinet_register"),
    path("profile/set", api_user_set_profil, name="api_user_set_profil"),
    path("profile/del", del_user, name="api_user_set_profil"),
    path("get/<uuid:uuid>", api_user_all, name="api_user_get"),
    path("get/mes_user/<uuid:uuid>", api_mes_user_all, name="api_mes_user_all"),
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