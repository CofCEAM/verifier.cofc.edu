from django.contrib import admin
from web.models import Setting


# Register your models here.
@admin.register(Setting)
class SettingAdmin(admin.ModelAdmin):
    pass
