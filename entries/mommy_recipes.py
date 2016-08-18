from model_mommy.recipe import Recipe

from allauth.socialaccount.models import SocialApp


fb_app = Recipe(SocialApp, provider='facebook')
