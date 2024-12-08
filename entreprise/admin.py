from django.contrib import admin

from .models import Entrer, HistoriqueEntrer, Categorie, SousCategorie, Depense, Entreprise, Sortie, HistoriqueSortie, \
    Client, FactEntre, FactSortie


# Register your models here.
class CategorieAdmin(admin.ModelAdmin):
    pass


class EntrepriseAdmin(admin.ModelAdmin):
    pass


class ClientAdmin(admin.ModelAdmin):
    pass


class SousCategorieAdmin(admin.ModelAdmin):
    pass


class DepenseAdmin(admin.ModelAdmin):
    pass


class EntrerAdmin(admin.ModelAdmin):
    pass


class HistoriqueEntrerAdmin(admin.ModelAdmin):
    pass


class SortieAdmin(admin.ModelAdmin):
    pass


class HistoriqueSortieAdmin(admin.ModelAdmin):
    pass


class FactEntreAdmin(admin.ModelAdmin):
    pass


class FactSortieAdmin(admin.ModelAdmin):
    pass


admin.site.register(Entreprise, EntrepriseAdmin)
admin.site.register(Client, ClientAdmin)
admin.site.register(Categorie, CategorieAdmin)
admin.site.register(SousCategorie, SousCategorieAdmin)
admin.site.register(Depense, DepenseAdmin)
admin.site.register(Entrer, EntrerAdmin)
admin.site.register(HistoriqueEntrer, HistoriqueEntrerAdmin)
admin.site.register(Sortie, SortieAdmin)
admin.site.register(HistoriqueSortie, HistoriqueSortieAdmin)
admin.site.register(FactEntre, FactEntreAdmin)
admin.site.register(FactSortie, FactSortieAdmin)
