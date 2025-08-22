from django.urls import path
from . import views

app_name = 'lessons'

urlpatterns = [
    # Основные страницы
    path('', views.LessonListView.as_view(), name='lesson_list'),
    path('lesson/<int:pk>/', views.LessonDetailView.as_view(), name='lesson_detail'),
    path('lesson/<int:lesson_id>/progress/', views.update_progress, name='update_progress'),
    
    # Админские страницы
    path('admin/lessons/', views.AdminLessonListView.as_view(), name='admin_lesson_list'),
    path('admin/lesson/create/', views.admin_lesson_create, name='admin_lesson_create'),
    path('admin/lesson/<int:pk>/edit/', views.admin_lesson_edit, name='admin_lesson_edit'),
    path('admin/lesson/<int:lesson_id>/access/', views.manage_user_access, name='manage_user_access'),
    path('admin/access/<int:access_id>/revoke/', views.revoke_access, name='revoke_access'),
] 