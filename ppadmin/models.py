from django.contrib.auth.models import Group, User


def subscribed(self):
    group, _ = Group.objects.get_or_create(name='subscribed')
    return group in self.groups.all()

User.add_to_class("subscribed", subscribed)
