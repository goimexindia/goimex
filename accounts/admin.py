from django.contrib import admin
from buyerseller.models import Product, Category
from .models import Profile, Contactme, ColdCoffe, Subscriber
from mptt.admin import DraggableMPTTAdmin

admin.site.register(Profile)
admin.site.register(Subscriber)
admin.site.register(ColdCoffe)


class ContactmeAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'subject', 'message')


admin.site.register(Contactme, ContactmeAdmin)
