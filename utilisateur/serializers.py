from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers
from django.contrib.auth import authenticate, get_user_model
from .models import Utilisateur

Utilisateur = get_user_model()


class UtilisateurSerializer(serializers.ModelSerializer):
    avatar = serializers.SerializerMethodField()

    class Meta:
        model = Utilisateur
        fields = [
            'avatar',
            'role',
            'uuid',
            'username',
            'id',
            'first_name',
            'last_name',
            'email',
            'email_user',
            'is_admin',
            'is_superuser',
            'numero'
        ]

    def get_avatar(self, obj):
        return obj.avatar.url if obj.avatar else None

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)
    # confirm_password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = Utilisateur
        fields = ["first_name", "last_name", "email", "numero", "pays", "password"]

    def validate_email(self, value):
        if Utilisateur.objects.filter(email=value).exists():
            raise serializers.ValidationError("Cet email est déjà utilisé.")
        return value

    def validate_numero(self, value):
        if Utilisateur.objects.filter(numero=value).exists():
            raise serializers.ValidationError("Ce numéro est déjà utilisé.")
        return value

    # def validate(self, attrs):
    #     if attrs["password"] != attrs["confirm_password"]:
    #         raise serializers.ValidationError({"confirm_password": "Les mots de passe ne correspondent pas."})
    #     return attrs

    def create(self, validated_data):
        # validated_data.pop("confirm_password")

        # Génération automatique du username unique
        base_username = f"{validated_data['first_name'][:2].lower()}0001{validated_data['last_name'][:2].lower()}"
        username = base_username
        counter = 1
        while Utilisateur.objects.filter(username=username).exists():
            counter += 1
            username = f"{validated_data['first_name'][:2].lower()}{counter:04d}{validated_data['last_name'][:2].lower()}"

        validated_data["username"] = username

        # Création de l'utilisateur
        user = Utilisateur.objects.create_user(**validated_data)

        return user


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    username_field = "username"  # champ utilisé par SimpleJWT

    def validate(self, attrs):
        login_input = attrs.get("username")  # peut être username ou numero
        password = attrs.get("password")

        # On cherche par username OU par numero
        try:
            user_obj = Utilisateur.objects.filter(username=login_input).first() \
                       or Utilisateur.objects.filter(numero=login_input).first()
        except Utilisateur.DoesNotExist:
            user_obj = None

        if not user_obj:
            raise serializers.ValidationError({
                "etat": False,
                "message": "Utilisateur introuvable."
            })

            # Authentification Django
        user = authenticate(username=user_obj.username, password=password)
        if not user:
            raise serializers.ValidationError({
                "etat": False,
                "message": "Nom d'utilisateur ou mot de passe incorrect."
            })
        # On laisse SimpleJWT générer les tokens
        data = super().validate({"username": user.username, "password": password})
        data["id"] = str(user.uuid)  # On renvoie aussi l’UUID
        data["username"] = user.username
        data["numero"] = user.numero
        return data
