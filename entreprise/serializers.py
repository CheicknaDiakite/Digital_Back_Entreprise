from datetime import datetime, timedelta

from rest_framework import serializers

from utilisateur.models import Licence, Utilisateur
from .models import Categorie, Entreprise, Depense, Sortie, Client, SousCategorie, Entrer, Facture


class EntrepriseSerializer(serializers.ModelSerializer):
    # user_id = serializers.UUIDField(write_only=True)
    type_licence = serializers.IntegerField(write_only=True, default=1)

    class Meta:
        model = Entreprise
        fields = ["id", "nom", "adresse", "numero", "email", "libelle", "type_licence"]

    def create(self, validated_data):
        # On ignore le type_licence envoyé par le client, on le définit selon le typeRole de l'utilisateur
        validated_data.pop("type_licence", None)
        
        request = self.context.get("request")
        user = request.user if request else None

        if not user or not user.is_authenticated:
            raise serializers.ValidationError("Utilisateur non authentifié.")

        # Déterminer le type de licence selon le typeRole de l'utilisateur
        # Simple/1 -> FREE/1, Basic/2 -> BASIC/2, Premium/3 -> PREMIUM/3
        type_licence = user.typeRole if user.typeRole in [1, 2, 3] else 1

        # Vérifier le nombre d’entreprises max
        if user.entreprises.count() >= 10:
            raise serializers.ValidationError("Vous possédez déjà plus de 10 entreprises.")

        # Calcul de la date d’expiration de la licence
        if type_licence == 1: # FREE
            date_expiration = datetime.now().date() + timedelta(days=7)
        elif type_licence == 2: # BASIC
            date_expiration = datetime.now().date() + timedelta(days=180)
        elif type_licence == 3: # PREMIUM
            date_expiration = datetime.now().date() + timedelta(days=365)
        else:
            raise serializers.ValidationError("Type de licence invalide.")

        licence = Licence.objects.create(type=type_licence, date_expiration=date_expiration)

        # Vérification des permissions
        if not user.groups.filter(name="Admin").exists():
            raise serializers.ValidationError("Vous n'avez pas la permission d'ajouter une entreprise.")

        entreprise = Entreprise.objects.create(licence=licence, **validated_data)
        entreprise.utilisateurs.add(user)
        return entreprise


class LicenceSerializer(serializers.ModelSerializer):
    type = serializers.CharField(source="get_type_display", read_only=True)

    class Meta:
        model = Licence
        fields = ["active", "type", "code", "date_expiration"]


class EntrepriseDetailSerializer(serializers.ModelSerializer):
    licence = LicenceSerializer(read_only=True)
    image = serializers.SerializerMethodField()

    class Meta:
        model = Entreprise
        fields = [
            'id', 'uuid', 'nom', 'adresse', 'libelle', 'email',
            'pays', 'coordonne', 'numero', 'image', 'licence'
        ]

    def get_image(self, obj):
        return obj.image.url if obj.image else None


class EntrerSerializer(serializers.ModelSerializer):
    client_id = serializers.UUIDField(required=False, allow_null=True, write_only=True)
    categorie_slug = serializers.UUIDField(write_only=True)
    user_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = Entrer
        fields = [
            "id", "uuid", "slug", "ref", "libelle", "qte", "unite", "pu", "pu_achat",
            "date", "cumuler_quantite", "is_sortie", "is_prix",
            "client_id", "categorie_slug", "user_id"
        ]
        read_only_fields = ["id", "uuid", "slug", "ref"]

    def create(self, validated_data):
        client_id = validated_data.pop("client_id", None)
        categorie_slug = validated_data.pop("categorie_slug")
        user_id = validated_data.pop("user_id")

        # Vérification de l'utilisateur
        admin = Utilisateur.objects.filter(uuid=user_id).first()
        if not admin:
            raise serializers.ValidationError({"user_id": "Utilisateur introuvable"})

        if not (admin.groups.filter(name="Admin").exists() or admin.groups.filter(name="Editor").exists()):
            raise serializers.ValidationError({"user_id": "Permission refusée"})

        # Vérification de la sous-catégorie
        categorie = SousCategorie.objects.filter(uuid=categorie_slug).first()
        if not categorie:
            raise serializers.ValidationError({"categorie_slug": "Sous-catégorie non trouvée"})

        # Création de l'objet
        entrer = Entrer(
            souscategorie=categorie,
            **validated_data
        )

        # Ajout du client s’il existe
        if client_id:
            client = Client.objects.filter(uuid=client_id).first()
            if not client:
                raise serializers.ValidationError({"client_id": "Client non trouvé"})
            entrer.client = client

        # Récupération de l’utilisateur courant pour l’historique
        user = self.context["request"].user if "request" in self.context else None
        entrer.save(user=user)

        return entrer


class SortieSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sortie
        fields = ['id', 'uuid', 'slug', 'qte', 'unite', 'pu', 'entrer', 'client', 'created_by', 'created_at']
        read_only_fields = ['id', 'uuid', 'slug', 'created_at']


class SortieEntrepriseSerializer(serializers.ModelSerializer):
    categorie_libelle = serializers.CharField(source="entrer.souscategorie.libelle", read_only=True)
    client = serializers.CharField(source="client.nom", allow_null=True, read_only=True)
    libelle = serializers.CharField(source="entrer.libelle", read_only=True)
    prix_sortie = serializers.IntegerField(source="entrer.qte", read_only=True)
    image = serializers.SerializerMethodField()

    class Meta:
        model = Sortie
        fields = [
            "id", "uuid", "slug", "pu", "ref", "qte", "unite", "is_remise",
            "categorie_libelle", "client", "libelle", "prix_total", "somme_total",
            "prix_sortie", "image", "created_at"
        ]

    def get_image(self, obj):
        if obj.entrer.souscategorie.image:
            return obj.entrer.souscategorie.image.url
        return None


class FactureSerializer(serializers.ModelSerializer):
    client_nom = serializers.CharField(source='client.nom', read_only=True)
    entreprise_nom = serializers.CharField(source='entreprise.nom', read_only=True)
    created_by_nom = serializers.CharField(source='created_by.username', read_only=True)
    reste_a_payer = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    sorties = SortieEntrepriseSerializer(many=True, read_only=True)

    class Meta:
        model = Facture
        fields = [
            'id', 'uuid', 'code', 'entreprise', 'entreprise_nom', 'client', 'client_nom',
            'montant_total', 'montant_remise', 'montant_paye', 'reste_a_payer',
            'est_solde', 'created_by', 'created_by_nom', 'created_at', 'updated_at',
            'sorties'
        ]
        read_only_fields = ['id', 'uuid', 'code', 'created_at', 'updated_at', 'reste_a_payer']

class ClientSerializer(serializers.ModelSerializer):
    # date = serializers.DateTimeField(source='created_at', format='%Y-%m-%d')

    class Meta:
        model = Client
        fields = [
            'uuid', 'id', 'nom', 'adresse', 'role', 'coordonne',
            'numero', 'libelle', 'email'
        ]
        read_only_fields = ["uuid", "slug", 'id']


class CategorieSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categorie
        fields = ["uuid", "libelle", "image", "entreprise", "slug", "created_at"]
        read_only_fields = ["uuid", "slug", "created_at"]


class DepenseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Depense
        fields = ["id", "uuid", "slug", "libelle", "somme", "date"]