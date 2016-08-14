"""pole_performance URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.9/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls import include, url
from django.conf.urls.static import static
from django.contrib import admin
from accounts.views import CustomLoginView, DisclaimerCreateView, \
    data_protection, subscribe_view

urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'^', include('web.urls', namespace='web')),
    url(
        r'^data-protection-statement/$', data_protection,
        name='data_protection'
    ),
    url(r'^entries/', include('entries.urls', namespace='entries')),
    url(r'^accounts/profile/', include('accounts.urls', namespace='profile')),
    url(r'^accounts/login/$', CustomLoginView.as_view(), name='login'),
    url(
        r'^accounts/disclaimer/$', DisclaimerCreateView.as_view(),
        name='disclaimer_form'
    ),
    url(r'^accounts/', include('allauth.urls')),
    url(r'^payments/ipn-paypal-notify/', include('paypal.standard.ipn.urls')),
]

if settings.HEROKU:
    urlpatterns += static(
        settings.STATIC_URL, document_root=settings.STATIC_ROOT
    )
