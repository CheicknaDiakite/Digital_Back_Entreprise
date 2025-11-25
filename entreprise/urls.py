from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import AddEntrepriseView, del_entreprise, get_entreprise, AddCategorieView, del_categorie, \
    CategoriesUserAPIView, CategorieDetailView, get_utilisateur_entreprise, SousCategoriesEntrepriseView, \
    AddSousCategorieAPIView, get_categorie, get_entrers_entreprise, SousCategoriesUtilisateurAPIView, AddEntrerView, \
    get_sous_categorie, InfoSousCatView, get_sortie, get_sorties_entreprise, SortieCreateView, \
    EntrepriseUtilisateursView, \
    api_somme_qte_pu_sortie, get_entreprise_un, FacSortiesUserAPIView, DepensesEntrepriseAPIView, DepenseCreateView, \
    get_depense_un, AddFactureSortieView, get_facture_sortie_un, get_facture_entre_un, FacEntresUserAPIView, \
    AddFactureEntreView, set_depense, set_facture_entre, set_facture_sortie, del_depense, del_facture_entre, \
    del_facture_sortie, del_entre, get_entre_un, remove_user_from_entreprise, set_entreprise, \
    UtilisateurEntrepriseHistoriqueSuppView, UtilisateurEntrepriseHistoriqueView, api_client_all, ClientCreateView, \
    ClientGetAPIView, set_client, set_categorie, del_client, get_entre, get_sortie_un, del_sortie, \
    SousCategorieUnEntrepriseView, \
    del_sous_categorie, set_sous_categorie, set_entre, ordre_paiement, pay_entreprise_get_historique, \
    paiement_entreprise_callback, add_avis, get_avis, del_avis, sous_categories_sorties_par_mois, update_sorties, \
    update_fac_sorties, api_count_sortie_par_utilisateur, get_depenses_somme, EntrerViewSet
from .voirs import CategorieListCreateView, UtilisateurEntreprisesView, EntrepriseDetailView, EntrepriseCreateView, \
    SommeQtePuSortieView, CountSortieParUtilisateurView, DepensesEntrepriseView, DepensesSommeParMoisView, \
    SousCategoriesSortiesParMoisView, SortiesEntrepriseAPIView, ClientListAPIView, EntresEntrepriseAPIView


router = DefaultRouter()
router.register("entrers", EntrerViewSet, basename="entrers")

urlpatterns = [
    path("", include(router.urls)),

    path("cate_api", CategorieListCreateView.as_view()),
    path("user_entreprises", UtilisateurEntreprisesView.as_view(), name="utilisateur-entreprises"),
    path("create_entreprise", EntrepriseCreateView.as_view(), name="utilisateur-entreprises"),
    path("un/<uuid:uuid>", EntrepriseDetailView.as_view(), name="entreprise-detail"),
    path('statistiques/<uuid:entreprise_id>', SommeQtePuSortieView.as_view(), name='statistiques-entreprise'),
    path('count_sortie_par_utilisateur/<uuid:entreprise_id>', CountSortieParUtilisateurView.as_view(), name='count-sortie-par-utilisateur'),
    path("depense/get_depenses_entreprise/<uuid:entreprise_id>", DepensesEntrepriseView.as_view(),
         name="get_sous_categorie_un"),
    path("depense/get_depenses_somme/<uuid:entreprise_id>", DepensesSommeParMoisView.as_view(), name="get_depenses_somme"),
    path('sous-categories-sorties/<uuid:entreprise_uuid>', SousCategoriesSortiesParMoisView.as_view(), name='sous_categories_sorties'),
    path("sortie/get_sorties_entreprise/<uuid:uuid>", SortiesEntrepriseAPIView.as_view(), name="get_sous_categorie_un"),
    path('clients/<uuid:uuid>', ClientListAPIView.as_view(), name='clients-list'),

    path("add", AddEntrepriseView.as_view(), name="add_bibliotheque"),
    path("del", del_entreprise, name="add_bibliotheque"),
    path("get", get_entreprise, name="add_bibliotheque"),
    path("set", set_entreprise, name="add_bibliotheque"),
    path("get/<uuid:uuid>", get_entreprise_un, name="get_categorie_un"),
    path("remove_user_from_entreprise", remove_user_from_entreprise, name="add_bibliotheque"),
    path("get_utilisateur_entreprise/<uuid:uuid>", get_utilisateur_entreprise, name="add_bibliotheque"),
    path("get_entreprise_utilisateurs/<uuid:uuid>", EntrepriseUtilisateursView.as_view(), name="add_bibliotheque"),
    path("api_somme_sortie/<uuid:entreprise_id>/<uuid:user_id>", api_somme_qte_pu_sortie, name="api_somme_sortie"),
    path("api_count_sortie_par_utilisateur/<uuid:entreprise_id>", api_count_sortie_par_utilisateur,
         name="api_count_sortie_par_utilisateur"),

    # path('sous-categories-sorties/<uuid:entreprise_uuid>', sous_categories_sorties_par_mois, name='sous_categories_sorties'),

    path("client/add", ClientCreateView.as_view(), name="add_bibliotheque"),
    path("client/set", set_client, name="add_bibliotheque"),
    path("client/del", del_client, name="add_bibliotheque"),
    path("client/get_un/<uuid:uuid>", ClientGetAPIView.as_view(), name="get_categorie_un"),
    path("client/get/<uuid:uuid>", api_client_all, name="api_user_get"),

    path("categorie/add", AddCategorieView.as_view(), name="add_bibliotheque"),
    path("categorie/del", del_categorie, name="add_bibliotheque"),
    path("categorie/get", get_categorie, name="add_bibliotheque"),
    path("categorie/set", set_categorie, name="add_bibliotheque"),
    path("categorie/get_categories_utilisateur/<uuid:entreprise_uuid>", CategoriesUserAPIView.as_view(), name="add_bibliotheque"),
    path("categorie/<uuid:uuid>", CategorieDetailView.as_view(), name="get_categorie_un"),

    path("sous_categorie/add", AddSousCategorieAPIView.as_view(), name="add_sous_categorie"),
    path("sous_categorie/get", get_sous_categorie, name="get_sous_categorie"),
    path("sous_categorie/set", set_sous_categorie, name="set_sous_categorie"),
    path("sous_categorie/del", del_sous_categorie, name="del_sous_categorie"),
    path("sous_categorie/get/<uuid:uuid>", SousCategorieUnEntrepriseView.as_view(), name="get_sous_categorie_un"),
    path("sous_categorie/get_sous_categories_par_categorie/<uuid:uuid>", SousCategoriesEntrepriseView.as_view(), name="get_sous_categorie_un"),
    path("sous_categorie/get_sous_categories_utilisateur/<uuid:entreprise_id>", SousCategoriesUtilisateurAPIView.as_view(), name="get_sous_categorie_un"),

    path("avis/add", add_avis, name="add_sous_categorie"),
    path("avis/get", get_avis, name="get_sous_categorie"),
    path("avis/del", del_avis, name="del_sous_categorie"),

    path("depense/add", DepenseCreateView.as_view(), name="add_sous_categorie"),
    path("depense/set", set_depense, name="set_sous_categorie"),
    path("depense/del", del_depense, name="del_sous_categorie"),
    path("depense/get/<uuid:uuid>", get_depense_un, name="get_sous_categorie_un"),
    path("depense/get_depenses_entreprise/<uuid:entreprise_id>", DepensesEntrepriseAPIView.as_view(), name="get_sous_categorie_un"),
    path("depense/get_depenses_somme/<uuid:uuid>/<uuid:entreprise_id>", get_depenses_somme, name="get_depenses_somme"),

    path("entre/add", AddEntrerView.as_view(), name="add_sous_categorie"),
    path("entre/del", del_entre, name="del_sous_categorie"),
    path("entre/get", get_entre, name="get_sous_categorie"),
    path("entre/set", set_entre, name="set_sous_categorie"),
    path("entre/get/<uuid:uuid>", get_entre_un, name="get_sous_categorie_un"),
    path("entre/get_entrers_entreprise/<uuid:entreprise_id>", EntresEntrepriseAPIView.as_view(), name="get_sous_categorie_un"),

    path("sortie/add", SortieCreateView.as_view(), name="add_sous_categorie"),
    path("sortie/get", get_sortie, name="get_sous_categorie"),
    path("sortie/set", update_sorties, name="update_sorties"),
    path("sortie/setFac", update_fac_sorties, name="update_sorties"),
    path("sortie/del", del_sortie, name="del_sous_categorie"),
    path("sortie/get/<uuid:uuid>", get_sortie_un, name="get_sous_categorie_un"),
    # path("sortie/get_sorties_entreprise/<uuid:uuid>", get_sorties_entreprise, name="get_sous_categorie_un"),

    path("facture/entre/add", AddFactureEntreView.as_view(), name="add_sous_categorie"),
    path("facture/entre/set", set_facture_entre, name="set_sous_categorie"),
    path("facture/entre/del", del_facture_entre, name="del_sous_categorie"),
    path("facture/entre/get/<uuid:uuid>", get_facture_entre_un, name="get_sous_categorie_un"),
    path("facture/entre/get_facEntersEntreprise_entreprise/<uuid:entreprise_id>", FacEntresUserAPIView.as_view(), name="get_sous_categorie_un"),

    path("facture/sortie/add", AddFactureSortieView.as_view(), name="add_sous_categorie"),
    path("facture/sortie/set", set_facture_sortie, name="set_sous_categorie"),
    path("facture/sortie/del", del_facture_sortie, name="del_sous_categorie"),
    path("facture/sortie/get/<uuid:uuid>", get_facture_sortie_un, name="get_sous_categorie_un"),
    path("facture/sortie/get_facSortiesEntreprise_entreprise/<uuid:entreprise_id>", FacSortiesUserAPIView.as_view(), name="get_sous_categorie_un"),

    path('info_sous_cat/get', InfoSousCatView.as_view(), name="info_sous_cat"),
    path('get_utilisateur_entreprise_historique', UtilisateurEntrepriseHistoriqueView.as_view(), name="info_sous_cat"),
    path('get_utilisateur_entreprise_historique_supp/<uuid:entreprise_uuid>', UtilisateurEntrepriseHistoriqueSuppView.as_view(), name="info_sous_cat"),

    # pour le paiement
    path("pay", ordre_paiement, name="ordre_paiement"),
    path("pay/get-historique", pay_entreprise_get_historique, name="pay_entreprise_get_historique"),
    # path("pay-verifier",pay_formation_verifier,name="pay_formation_verifier"),

    path("callback/<str:order_id>/validation/achat-entreprise",paiement_entreprise_callback,name="paiement_entreprise_callback"),

]
