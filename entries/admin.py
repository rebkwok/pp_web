from django.contrib import admin

from .models import Entry


class EntryAdmin(admin.ModelAdmin):

    list_filter = ("entry_year", "status")

admin.site.register(Entry, EntryAdmin)
