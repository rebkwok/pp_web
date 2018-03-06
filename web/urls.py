from django.urls import path

from .views import home


app_name = 'web'


urlpatterns = [
    path('', home, name='home'),
]

