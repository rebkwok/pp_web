from django.conf import settings


def pp_email(request):
    return {'pp_email': settings.DEFAULT_STUDIO_EMAIL}