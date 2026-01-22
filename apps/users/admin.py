from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User, UserProfile


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['username', 'email', 'first_name', 'last_name', 'department', 'position', 'is_active', 'date_joined']
    list_filter = ['is_active', 'department', 'position']
    search_fields = ['username', 'email', 'first_name', 'last_name']
    # 保持与默认UserAdmin相同的字段集，确保密码哈希功能正常工作
    fieldsets = BaseUserAdmin.fieldsets
    add_fieldsets = BaseUserAdmin.add_fieldsets

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'theme', 'language', 'timezone']