from django.conf.urls import url

from .views import entries_home

urlpatterns = [
    url(r'^$', entries_home, name='entries_home'),
]