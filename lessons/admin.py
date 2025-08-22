from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Category, VideoLesson, UserAccess, LessonProgress


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'created_at', 'lesson_count']
    search_fields = ['name', 'description']
    list_filter = ['created_at']
    
    def lesson_count(self, obj):
        return obj.videolesson_set.count()
    lesson_count.short_description = 'Количество уроков'


@admin.register(VideoLesson)
class VideoLessonAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'duration_display', 'is_active', 'created_at', 'access_count']
    list_filter = ['category', 'is_active', 'created_at']
    search_fields = ['title', 'description']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('Основная информация', {
            'fields': ('title', 'description', 'category', 'is_active')
        }),
        ('Медиа файлы', {
            'fields': ('video_file', 'thumbnail', 'duration')
        }),
        ('Метаданные', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def duration_display(self, obj):
        return obj.get_duration_display()
    duration_display.short_description = 'Длительность'
    
    def access_count(self, obj):
        count = obj.useraccess_set.filter(is_active=True).count()
        return format_html(
            '<a href="{}">{} пользователей</a>',
            reverse('admin:lessons_useraccess_changelist') + f'?lesson__id__exact={obj.id}',
            count
        )
    access_count.short_description = 'Доступы'


@admin.register(UserAccess)
class UserAccessAdmin(admin.ModelAdmin):
    list_display = ['user', 'lesson', 'is_approved', 'granted_by', 'granted_at', 'expires_at', 'is_active', 'valid_badge']
    list_filter = ['is_approved', 'is_active', 'granted_at', 'expires_at', 'lesson__category']
    search_fields = ['user__username', 'user__email', 'lesson__title']
    readonly_fields = ['granted_at']
    date_hierarchy = 'granted_at'
    
    fieldsets = (
        ('Доступ', {
            'fields': ('user', 'lesson', 'is_approved', 'is_active')
        }),
        ('Срок действия', {
            'fields': ('expires_at',)
        }),
        ('Служебные', {
            'fields': ('granted_by', 'granted_at')
        })
    )

    def save_model(self, request, obj, form, change):
        if not obj.granted_by:
            obj.granted_by = request.user
        super().save_model(request, obj, form, change)

    def valid_badge(self, obj):
        if obj.is_valid():
            return mark_safe('<span style="color: green;">✓ Действителен</span>')
        else:
            return mark_safe('<span style="color: red;">✗ Истек</span>')
    valid_badge.short_description = 'Статус доступа'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'lesson', 'granted_by')


@admin.register(LessonProgress)
class LessonProgressAdmin(admin.ModelAdmin):
    list_display = ['user', 'lesson', 'progress_percentage', 'is_completed', 'last_watched']
    list_filter = ['is_completed', 'last_watched', 'lesson__category']
    search_fields = ['user__username', 'lesson__title']
    readonly_fields = ['last_watched']
    date_hierarchy = 'last_watched'
    
    def progress_percentage(self, obj):
        percentage = obj.get_progress_percentage()
        color = 'green' if percentage >= 90 else 'orange' if percentage >= 50 else 'red'
        return format_html(
            '<span style="color: {};">{:.1f}%</span>',
            color,
            percentage
        )
    progress_percentage.short_description = 'Прогресс'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'lesson')
