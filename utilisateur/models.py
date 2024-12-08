import random
import string
import uuid

from django.contrib.auth.models import AbstractUser, Permission, Group
from django.db import models


# Create your models here.
class Utilisateur(AbstractUser):
    ADMIN = 1
    EDITOR = 2
    AUTHOR = 3
    VISITOR = 4

    choice = (
        (ADMIN, "Admin"),
        (EDITOR, "Editor"),
        (AUTHOR, "Author"),
        (VISITOR, "Visitor"),
    )

    created_by = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL,
                                   related_name='created_users')

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    avatar = models.ImageField(null=True, blank=True)
    numero = models.CharField(max_length=200, unique=True)
    pays = models.CharField(max_length=100, blank=True, null=True)

    is_admin = models.BooleanField(default=False)
    email_user = models.EmailField(blank=True, null=True)

    role = models.PositiveSmallIntegerField(choices=choice, null=True, blank=True)

    # boutiques = models.ManyToManyField('Boutique', related_name='utilisateurs',
    #                                    blank=True)  # Relation optionnelle

    def __str__(self):
        return f"{self.first_name} ({self.username})"

    def save(self, *args, **kwargs):

        # CREATION / RECUPERATION DES GROUPS
        admin_group, create_ad = Group.objects.get_or_create(name="Admin")
        editor_group, create_ed = Group.objects.get_or_create(name="Editor")
        author_group, create_auth = Group.objects.get_or_create(name="Author")
        visitor_group, create_vis = Group.objects.get_or_create(name="Visitor")

        # RECUPERATION DES GROUPS
        admin_permission = [
            Permission.objects.get(codename="view_categorie"),
            Permission.objects.get(codename="add_categorie"),
            Permission.objects.get(codename="delete_categorie"),
            Permission.objects.get(codename="change_categorie"),

            Permission.objects.get(codename="view_souscategorie"),
            Permission.objects.get(codename="add_souscategorie"),
            Permission.objects.get(codename="delete_souscategorie"),
            Permission.objects.get(codename="change_souscategorie"),

            Permission.objects.get(codename="view_utilisateur"),
            Permission.objects.get(codename="add_utilisateur"),
            Permission.objects.get(codename="delete_utilisateur"),
            Permission.objects.get(codename="change_utilisateur"),
        ]

        editor_permission = [
            Permission.objects.get(codename="view_categorie"),
            Permission.objects.get(codename="add_categorie"),
            Permission.objects.get(codename="delete_categorie"),
            Permission.objects.get(codename="change_categorie"),

            Permission.objects.get(codename="view_souscategorie"),
            Permission.objects.get(codename="add_souscategorie"),
            Permission.objects.get(codename="delete_souscategorie"),
            Permission.objects.get(codename="change_souscategorie"),

        ]

        author_permission = [
            Permission.objects.get(codename="view_categorie"),

            Permission.objects.get(codename="view_souscategorie"),
            Permission.objects.get(codename="add_souscategorie"),
            Permission.objects.get(codename="change_souscategorie"),
            Permission.objects.get(codename="delete_souscategorie"),

        ]

        visitor_permission = [
            Permission.objects.get(codename="view_categorie"),

            Permission.objects.get(codename="view_souscategorie"),

        ]

        admin_group.permissions.add(*admin_permission)
        editor_group.permissions.add(*editor_permission)
        author_group.permissions.add(*author_permission)
        visitor_group.permissions.add(*visitor_permission)

        match self.role:
            case self.ADMIN:
                self.is_staff = True
                self.is_admin = True
                self.is_active = True

                self.groups.add(admin_group)

                return super().save(*args, **kwargs)
            case self.EDITOR:
                self.is_staff = True
                self.is_superuser = False
                self.is_admin = False
                self.is_active = True

                self.groups.add(editor_group)

                return super().save(*args, **kwargs)
            case self.AUTHOR:
                self.is_staff = True
                self.is_superuser = False
                self.is_admin = False
                self.is_active = True

                self.groups.add(author_group)

                return super().save(*args, **kwargs)
            case self.VISITOR:
                self.is_staff = False
                self.is_superuser = False
                self.is_admin = False
                self.is_active = True

                self.groups.add(visitor_group)

                return super().save(*args, **kwargs)
            case _:
                return super().save(*args, **kwargs)

        pass


class Licence(models.Model):
    FREE = 1
    BASIC = 2
    PREMUIM = 3

    TYPE_CHOICES = [
        (FREE, 'Free'),
        (BASIC, 'Basic'),
        (PREMUIM, 'Premium'),
    ]

    type = models.PositiveSmallIntegerField(choices=TYPE_CHOICES, default=FREE)
    date_debut = models.DateField(auto_now_add=True)
    date_expiration = models.DateField()
    active = models.BooleanField(default=True)

    # Ajouter un champ pour la chaîne de caractères de la licence
    code = models.CharField(max_length=14, unique=True, editable=False)

    def save(self, *args, **kwargs):
        # Générer un code unique de 14 caractères alphanumériques pour la licence
        if not self.code:
            self.code = self.generate_licence_code()
        super().save(*args, **kwargs)

    @staticmethod
    def generate_licence_code():
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=14))

    def __str__(self):
        return f"{self.type} - {self.code} - Expire le {self.date_expiration}"


class Token(models.Model):
    user = models.OneToOneField(Utilisateur, on_delete=models.CASCADE)
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Token for {self.user.username}'


class PasswordReset(models.Model):
    utilisateur = models.ForeignKey(Utilisateur, on_delete=models.CASCADE)
    time = models.FloatField()
    utiliser = models.BooleanField(default=False)


class Verification_email(models.Model):
    email = models.EmailField()
    code = models.CharField(max_length=512)

    valide = models.BooleanField(default=True)
    date = models.DateField(auto_now=True)
