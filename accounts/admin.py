from django.contrib import admin

from accounts.models import OnlineDisclaimer


class OnlineDisclaimerAdmin(admin.ModelAdmin):

    readonly_fields = (
        'user', 'emergency_contact_name',
        'emergency_contact_relationship', 'emergency_contact_phone',
        'waiver_terms', 'terms_accepted'
    )


admin.site.register(OnlineDisclaimer, OnlineDisclaimerAdmin)
