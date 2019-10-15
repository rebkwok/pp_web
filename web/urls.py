from django.urls import path

from .views import placeholder, home2018, home2020


app_name = 'web'


urlpatterns = [
    path('', placeholder, name='placeholder'),
    path('2018', home2018, name='home_2018'),
    path('2020', home2020, name='home'),
]

