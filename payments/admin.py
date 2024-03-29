from django.contrib import admin
from django.contrib.auth.models import User
from payments.models import PaypalEntryTransaction

from paypal.standard.ipn.models import PayPalIPN
from paypal.standard.ipn.admin import PayPalIPNAdmin


class UserFilter(admin.SimpleListFilter):

    title = 'User'
    parameter_name = 'user'

    def lookups(self, request, model_admin):
        qs = User.objects.all().order_by('first_name')
        return [
            (
                user.id,
                "{} {} ({})".format(
                    user.first_name, user.last_name, user.username
                )
             ) for user in qs
            ]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(entry__user__id=self.value())
        return queryset


class PaypalEntryTransactionAdmin(admin.ModelAdmin):

    list_display = ('id', 'get_user', 'invoice_id',
                    'transaction_id', 'get_entry_id')
    readonly_fields = ('id', 'get_user', 'invoice_id',
                       'get_entry_id')
    list_filter = (UserFilter,)
    list_select_related = ('entry',)

    def get_entry_id(self, obj):
        if obj.entry:
            return obj.entry.id
    get_entry_id.short_description = "Entry id"

    def get_user(self, obj):
        if obj.entry:
            return "{} {}".format(
                obj.entry.user.first_name, obj.entry.user.last_name
            )
    get_user.short_description = "User"


class PayPalAdmin(PayPalIPNAdmin):

    search_fields = [
        "txn_id", "recurring_payment_id", 'custom', 'invoice',
        'first_name', 'last_name'
    ]
    list_display = [
        "txn_id", "flag", "flag_info", "invoice", "custom",
        "payment_status", "buyer", "created_at"
    ]

    def buyer(self, obj):
        return "{} {}".format(obj.first_name, obj.last_name)
    buyer.admin_order_field = 'first_name'


admin.site.register(PaypalEntryTransaction, PaypalEntryTransactionAdmin)
admin.site.unregister(PayPalIPN)
admin.site.register(PayPalIPN, PayPalAdmin)
