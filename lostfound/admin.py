
from django.contrib import admin
from .models import Category, Item, Claim, ItemStatusHistory, Notification


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'report_type', 'category', 'user', 'status', 'created_at')
    list_filter = ('report_type', 'status', 'category')
    search_fields = ('name', 'description', 'location')


@admin.register(Claim)
class ClaimAdmin(admin.ModelAdmin):
    list_display = ('id', 'item', 'claimant', 'status', 'reviewed_by', 'created_at')
    list_filter = ('status',)
    search_fields = ('item__name', 'claimant__username')


@admin.register(ItemStatusHistory)
class ItemStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'item', 'old_status', 'new_status', 'changed_by', 'changed_at')


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'message', 'is_read', 'created_at')
    list_filter = ('is_read',)
