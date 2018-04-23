"""pole_performance URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.9/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf import settings
from django.urls import include, path
from django.conf.urls.static import static
from django.contrib import admin

from accounts.views import CustomLoginView, CustomSignUpView, \
    data_privacy_policy, cookie_policy
from entries.views import permission_denied


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('web.urls')),
    path('entries/', include('entries.urls')),
    path('accounts/login/', CustomLoginView.as_view(), name='login'),
    path('accounts/signup/', CustomSignUpView.as_view(), name='account_signup'),
    path('accounts/', include('accounts.urls')),
    path('accounts/', include('allauth.urls')),
    path(
        'data-privacy-policy/', data_privacy_policy, name='data_privacy_policy'
    ),
    path(
        'cookie-policy/', cookie_policy, name='cookie_policy'
    ),
    path('payments/ipn-paypal-notify/', include('paypal.standard.ipn.urls')),
    path('payments/', include('payments.urls')),
    path('not-available/', permission_denied, name='permission_denied'),

    path('ppadmin/', include('ppadmin.urls')),
]

if settings.HEROKU:  # pragma: no cover
    urlpatterns += static(
        settings.STATIC_URL, document_root=settings.STATIC_ROOT
    )

if settings.DEBUG:  # pragma: no cover
    import debug_toolbar
    urlpatterns.append(path('__debug__/', include(debug_toolbar.urls)))
