"""
Customers app admin configuration
"""
from django.contrib import admin
from .models import Customer, CustomerNote, CustomerMergeHistory


class CustomerNoteInline(admin.TabularInline):
    """Inline customer notes"""
    model = CustomerNote
    extra = 0
    readonly_fields = ('created_at', 'created_by')
    
    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    """Customer admin"""
    list_display = ('name', 'phone', 'email', 'total_orders', 'total_spent', 'last_visit', 'is_active')
    list_filter = ('is_active', 'created_at', 'last_visit')
    search_fields = ('name', 'phone', 'email')
    readonly_fields = ('total_orders', 'total_spent', 'last_visit', 'created_at', 'updated_at')
    inlines = [CustomerNoteInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'phone', 'email', 'address')
        }),
        ('Status', {
            'fields': ('is_active', 'notes')
        }),
        ('Statistics', {
            'fields': ('total_orders', 'total_spent', 'last_visit'),
            'classes': ('collapse',)
        }),
        ('Audit', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
    
    actions = ['update_loyalty_stats']
    
    def update_loyalty_stats(self, request, queryset):
        """Update loyalty statistics for selected customers"""
        count = 0
        for customer in queryset:
            customer.update_loyalty_stats()
            count += 1
        self.message_user(request, f'Updated loyalty stats for {count} customers.')
    update_loyalty_stats.short_description = 'Update loyalty statistics'


@admin.register(CustomerNote)
class CustomerNoteAdmin(admin.ModelAdmin):
    """Customer note admin"""
    list_display = ('customer', 'note_preview', 'created_by', 'created_at')
    list_filter = ('created_at', 'created_by')
    search_fields = ('customer__name', 'note')
    readonly_fields = ('created_at',)
    
    def note_preview(self, obj):
        return obj.note[:50] + '...' if len(obj.note) > 50 else obj.note
    note_preview.short_description = 'Note Preview'
    
    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(CustomerMergeHistory)
class CustomerMergeHistoryAdmin(admin.ModelAdmin):
    """Customer merge history admin"""
    list_display = ('primary_customer', 'merge_reason', 'merged_by', 'merged_at')
    list_filter = ('merged_at', 'merged_by')
    search_fields = ('primary_customer__name', 'merge_reason')
    readonly_fields = ('merged_at',)
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
