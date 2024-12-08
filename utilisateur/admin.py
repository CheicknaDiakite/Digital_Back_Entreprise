from django.contrib import admin
from django.contrib.auth.hashers import make_password

from .models import Utilisateur, Token, Licence


# Register your models here.
class UtilisateurAdmin(admin.ModelAdmin):

    def save_model(self, request, obj, form, change):

        if change:
            old_password = Utilisateur.objects.get(pk=obj.id).password
            password = obj.password
            if old_password != password:
                obj.password = make_password(password)
        return super().save_model(request, obj, form, change)

    pass


class LicenceAdmin(admin.ModelAdmin):
    pass


class TokenAdmin(admin.ModelAdmin):
    pass


admin.site.register(Licence, LicenceAdmin)
admin.site.register(Token, TokenAdmin)
admin.site.register(Utilisateur, UtilisateurAdmin)
