from django.urls import path

from .views import add_entreprise, del_entreprise, get_entreprise, add_categorie, del_categorie, \
    get_categories_utilisateur, get_categorie_un, get_utilisateur_entreprise, get_sous_categories_par_categorie, \
    add_sous_categorie, get_categorie, get_entrers_entreprise, get_sous_categories_utilisateur, add_entre, \
    get_sous_categorie, info_sous_cat, get_sortie, get_sorties_entreprise, add_sortie, get_entreprise_utilisateurs, \
    api_somme_qte_pu_sortie, get_entreprise_un, get_facSorties_utilisateur, get_depenses_entreprise, add_depense, \
    get_depense_un, add_facture_sortie, get_facture_sortie_un, get_facture_entre_un, get_facEntres_utilisateur, \
    add_facture_entre, set_depense, set_facture_entre, set_facture_sortie, del_depense, del_facture_entre, \
    del_facture_sortie, del_entre, get_entre_un, remove_user_from_entreprise, set_entreprise, \
    get_utilisateur_entreprise_historique_supp, get_utilisateur_entreprise_historique, api_client_all, add_client, \
    get_client_un, set_client, set_categorie, del_client, get_entre, get_sortie_un, del_sortie, get_sous_categorie_un, \
    del_sous_categorie, set_sous_categorie, set_entre, ordre_paiement, pay_entreprise_get_historique, \
    paiement_entreprise_callback, add_avis, get_avis, del_avis

urlpatterns = [
    path("add", add_entreprise, name="add_bibliotheque"),
    path("del", del_entreprise, name="add_bibliotheque"),
    path("get", get_entreprise, name="add_bibliotheque"),
    path("set", set_entreprise, name="add_bibliotheque"),
    path("get/<uuid:uuid>", get_entreprise_un, name="get_categorie_un"),
    path("remove_user_from_entreprise", remove_user_from_entreprise, name="add_bibliotheque"),
    path("get_utilisateur_entreprise/<uuid:uuid>", get_utilisateur_entreprise, name="add_bibliotheque"),
    path("get_entreprise_utilisateurs/<uuid:uuid>", get_entreprise_utilisateurs, name="add_bibliotheque"),
    path("api_somme_sortie/<uuid:entreprise_id>/<uuid:user_id>", api_somme_qte_pu_sortie, name="api_somme_sortie"),

    path("client/add", add_client, name="add_bibliotheque"),
    path("client/set", set_client, name="add_bibliotheque"),
    path("client/del", del_client, name="add_bibliotheque"),
    path("client/get_un/<uuid:uuid>", get_client_un, name="get_categorie_un"),
    path("client/get/<uuid:uuid>", api_client_all, name="api_user_get"),

    path("categorie/add", add_categorie, name="add_bibliotheque"),
    path("categorie/del", del_categorie, name="add_bibliotheque"),
    path("categorie/get", get_categorie, name="add_bibliotheque"),
    path("categorie/set", set_categorie, name="add_bibliotheque"),
    path("categorie/get_categories_utilisateur/<uuid:uuid>/<uuid:entreprise_uuid>", get_categories_utilisateur, name="add_bibliotheque"),
    path("categorie/get/<str:slug>", get_categorie_un, name="get_categorie_un"),

    path("sous_categorie/add", add_sous_categorie, name="add_sous_categorie"),
    path("sous_categorie/get", get_sous_categorie, name="get_sous_categorie"),
    path("sous_categorie/set", set_sous_categorie, name="set_sous_categorie"),
    path("sous_categorie/del", del_sous_categorie, name="del_sous_categorie"),
    path("sous_categorie/get/<uuid:uuid>", get_sous_categorie_un, name="get_sous_categorie_un"),
    path("sous_categorie/get_sous_categories_par_categorie/<uuid:uuid>", get_sous_categories_par_categorie, name="get_sous_categorie_un"),
    path("sous_categorie/get_sous_categories_utilisateur/<uuid:uuid>/<uuid:entreprise_id>", get_sous_categories_utilisateur, name="get_sous_categorie_un"),

    path("avis/add", add_avis, name="add_sous_categorie"),
    path("avis/get", get_avis, name="get_sous_categorie"),
    path("avis/del", del_avis, name="del_sous_categorie"),

    path("depense/add", add_depense, name="add_sous_categorie"),
    path("depense/set", set_depense, name="set_sous_categorie"),
    path("depense/del", del_depense, name="del_sous_categorie"),
    path("depense/get/<uuid:uuid>", get_depense_un, name="get_sous_categorie_un"),
    path("depense/get_depenses_entreprise/<uuid:uuid>/<uuid:entreprise_id>", get_depenses_entreprise, name="get_sous_categorie_un"),

    path("entre/add", add_entre, name="add_sous_categorie"),
    path("entre/del", del_entre, name="del_sous_categorie"),
    path("entre/get", get_entre, name="get_sous_categorie"),
    path("entre/set", set_entre, name="set_sous_categorie"),
    path("entre/get/<uuid:uuid>", get_entre_un, name="get_sous_categorie_un"),
    path("entre/get_entrers_entreprise/<uuid:uuid>/<uuid:entreprise_id>", get_entrers_entreprise, name="get_sous_categorie_un"),

    path("sortie/add", add_sortie, name="add_sous_categorie"),
    path("sortie/get", get_sortie, name="get_sous_categorie"),
    path("sortie/del", del_sortie, name="del_sous_categorie"),
    path("sortie/get/<uuid:uuid>", get_sortie_un, name="get_sous_categorie_un"),
    path("sortie/get_sorties_entreprise/<uuid:uuid>", get_sorties_entreprise, name="get_sous_categorie_un"),

    path("facture/entre/add", add_facture_entre, name="add_sous_categorie"),
    path("facture/entre/set", set_facture_entre, name="set_sous_categorie"),
    path("facture/entre/del", del_facture_entre, name="del_sous_categorie"),
    path("facture/entre/get/<uuid:uuid>", get_facture_entre_un, name="get_sous_categorie_un"),
    path("facture/entre/get_facEntersEntreprise_entreprise/<uuid:uuid>/<uuid:entreprise_id>", get_facEntres_utilisateur, name="get_sous_categorie_un"),

    path("facture/sortie/add", add_facture_sortie, name="add_sous_categorie"),
    path("facture/sortie/set", set_facture_sortie, name="set_sous_categorie"),
    path("facture/sortie/del", del_facture_sortie, name="del_sous_categorie"),
    path("facture/sortie/get/<uuid:uuid>", get_facture_sortie_un, name="get_sous_categorie_un"),
    path("facture/sortie/get_facSortiesEntreprise_entreprise/<uuid:uuid>/<uuid:entreprise_id>", get_facSorties_utilisateur, name="get_sous_categorie_un"),

    path('info_sous_cat/get', info_sous_cat, name="info_sous_cat"),
    path('get_utilisateur_entreprise_historique/<uuid:uuid>', get_utilisateur_entreprise_historique, name="info_sous_cat"),
    path('get_utilisateur_entreprise_historique_supp/<uuid:uuid>/<uuid:entreprise_uuid>', get_utilisateur_entreprise_historique_supp, name="info_sous_cat"),

    # pour le paiement
    path("pay", ordre_paiement, name="ordre_paiement"),
    path("pay/get-historique", pay_entreprise_get_historique, name="pay_entreprise_get_historique"),
    # path("pay-verifier",pay_formation_verifier,name="pay_formation_verifier"),

    path("callback/<str:order_id>/validation/achat-entreprise",paiement_entreprise_callback,name="paiement_entreprise_callback"),

]
