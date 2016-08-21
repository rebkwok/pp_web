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

from accounts.views import CustomLoginView, CustomSignUpView
from entries.views import permission_denied


urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'^', include('web.urls', namespace='web')),
    url(r'^entries/', include('entries.urls', namespace='entries')),
    url(r'^accounts/login/$', CustomLoginView.as_view(), name='login'),
    url(r'^accounts/signup/$', CustomSignUpView.as_view(), name='account_signup'),
    url(r'^accounts/', include('accounts.urls', namespace='accounts')),
    url(r'^accounts/', include('allauth.urls')),
    url(r'^payments/ipn-paypal-notify/', include('paypal.standard.ipn.urls')),
    url(r'payments/', include('payments.urls', namespace='payments')),
    url(r'^not-available/$', permission_denied, name='permission_denied'),
    url(r'ppadmin/', include('ppadmin.urls', namespace='ppadmin')),
]

if settings.HEROKU:  # pragma: no cover
    urlpatterns += static(
        settings.STATIC_URL, document_root=settings.STATIC_ROOT
    )

if settings.DEBUG:  # pragma: no cover
    import debug_toolbar
    urlpatterns.append(url(r'^__debug__/', include(debug_toolbar.urls)))
