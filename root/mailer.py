from django.core.mail import send_mail

from .settings import EMAIL_HOST_USER

"""
Pour envoyer des email
email_liste est une liste ou un tuple
"""


def send(sujet="", message="", email_liste=[], html_message=None, from_mail=None):
    if from_mail == None:
        from_mail = f"Diakite Digital <{EMAIL_HOST_USER}>"
    try:
        send_mail(
            sujet,
            message,
            from_mail,
            email_liste,
            html_message=html_message
        )


        return True
    except:
        return False
