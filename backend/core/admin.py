from django.contrib import admin
from .models import Event, Announcement, Goal, PaymentSettings, CreatorSupport, ContactSettings, NavigationTab

class OwnContentAdmin(admin.ModelAdmin):
    actions = None
    readonly_fields = ('creator',)
    def has_change_permission(self, request, obj=None):
        return request.user.is_staff if obj is None else obj.creator_id == request.user.id
    def save_model(self, request, obj, form, change):
        if not change: obj.creator = request.user
        super().save_model(request, obj, form, change)

@admin.register(Event)
class EventAdmin(OwnContentAdmin):
    list_display = ('title','starts_at','place','creator')
    search_fields = ('title','place')
    # Images are accepted only through the API, which decodes and reencodes them.
    fields = ('title','description','topic_summary','starts_at','place','anonymous_author','creator')
    def has_delete_permission(self, request, obj=None):
        return request.user.is_staff if obj is None else obj.creator_id == request.user.id

@admin.register(Announcement)
class AnnouncementAdmin(OwnContentAdmin):
    list_display = ('created_at','creator','body')
    def has_delete_permission(self, request, obj=None):
        return request.user.is_staff

@admin.register(Goal)
class GoalAdmin(admin.ModelAdmin):
    list_display = ('title','active','position')

admin.site.register(PaymentSettings)

class SingleSettingAdmin(admin.ModelAdmin):
    """Keep the seeded setting as one editable row while preserving Add in the admin."""
    def get_queryset(self, request):
        queryset = super().get_queryset(request).order_by('pk')
        setting_id = queryset.values_list('pk', flat=True).first()
        return queryset.filter(pk=setting_id) if setting_id else queryset.none()

    def save_model(self, request, obj, form, change):
        if not change:
            existing_id = self.model.objects.order_by('pk').values_list('pk', flat=True).first()
            if existing_id:
                obj.pk = existing_id
                change = True
        super().save_model(request, obj, form, change)

@admin.register(CreatorSupport)
class CreatorSupportAdmin(SingleSettingAdmin):
    list_display = ('label','visible')
    list_display_links = ('label',)
    list_editable = ('visible',)
    ordering = ('pk',)
    @admin.display(description='Ustawienia')
    def label(self, obj): return 'Widoczność i dane wsparcia'

@admin.register(ContactSettings)
class ContactSettingsAdmin(SingleSettingAdmin):
    list_display = ('label','visible')
    list_display_links = ('label',)
    list_editable = ('visible',)
    fields = ('visible','name','email','phone','address')
    @admin.display(description='Ustawienia')
    def label(self, obj): return 'Widoczność zakładki Kontakt'

@admin.register(NavigationTab)
class NavigationTabAdmin(admin.ModelAdmin):
    list_display = ('tab_name','visible')
    list_display_links = ('tab_name',)
    list_editable = ('visible',)
    @admin.display(description='Zakładka')
    def tab_name(self, obj): return obj.get_key_display()
