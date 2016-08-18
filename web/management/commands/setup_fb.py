from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from allauth.socialaccount.models import SocialApp

class Command(BaseCommand):

    def handle(self, *args, **options):

        self.stdout.write("Configuring facebook social app for test site")

        site = Site.objects.get(id=1)
        site.name = "pole_performance"
        site.save()

        sapp, _ = SocialApp.objects.get_or_create(name="pole_performance",
                                        provider="facebook",
                                        client_id="306248973045529",
                                        secret="31421ec7c8808453bc0d996c829c040e")
        sapp.save()
        sapp.sites.add(1)
