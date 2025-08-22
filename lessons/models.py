from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Category(models.Model):
    """Категория видео уроков"""
    name = models.CharField(max_length=100, verbose_name="Название категории")
    description = models.TextField(blank=True, verbose_name="Описание")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Категория"
        verbose_name_plural = "Категории"
        ordering = ['name']
    
    def __str__(self):
        return self.name


class VideoLesson(models.Model):
    """Модель видео урока"""
    title = models.CharField(max_length=200, verbose_name="Название урока")
    description = models.TextField(verbose_name="Описание")
    video_file = models.FileField(upload_to='videos/', verbose_name="Видео файл")
    thumbnail = models.ImageField(upload_to='thumbnails/', blank=True, null=True, verbose_name="Превью")
    category = models.ForeignKey('Category', on_delete=models.CASCADE, verbose_name="Категория")
    duration = models.IntegerField(default=0, verbose_name="Длительность (секунды)")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True, verbose_name="Активен")
    
    class Meta:
        verbose_name = "Видео урок"
        verbose_name_plural = "Видео уроки"
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title
    
    def get_duration_display(self):
        """Возвращает длительность в формате MM:SS"""
        minutes = self.duration // 60
        seconds = self.duration % 60
        return f"{minutes:02d}:{seconds:02d}"


class UserAccess(models.Model):
    """Модель для управления доступом пользователей к урокам
    Если is_approved=True, доступ ко всем урокам (lesson может быть пустым)
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Пользователь")
    lesson = models.ForeignKey(VideoLesson, on_delete=models.CASCADE, verbose_name="Урок", null=True, blank=True)
    is_approved = models.BooleanField(default=False, verbose_name="Допущен к видео")
    granted_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='access_granted',
        verbose_name="Доступ предоставил"
    )
    granted_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата предоставления доступа")
    expires_at = models.DateTimeField(null=True, blank=True, verbose_name="Дата истечения доступа")
    is_active = models.BooleanField(default=True, verbose_name="Активен")
    
    class Meta:
        verbose_name = "Доступ пользователя"
        verbose_name_plural = "Доступы пользователей"
        unique_together = ['user', 'lesson']
    
    def __str__(self):
        target = self.lesson.title if self.lesson else 'Все уроки'
        return f"{self.user.username} - {target}"
    
    def is_valid(self):
        """Проверяет, действителен ли доступ"""
        if not self.is_active:
            return False
        if self.expires_at and timezone.now() > self.expires_at:
            return False
        return True


class LessonProgress(models.Model):
    """Прогресс пользователя по уроку"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Пользователь")
    lesson = models.ForeignKey(VideoLesson, on_delete=models.CASCADE, verbose_name="Урок")
    watched_seconds = models.IntegerField(default=0, verbose_name="Просмотрено секунд")
    is_completed = models.BooleanField(default=False, verbose_name="Завершен")
    last_watched = models.DateTimeField(auto_now=True, verbose_name="Последний просмотр")
    
    class Meta:
        verbose_name = "Прогресс урока"
        verbose_name_plural = "Прогресс уроков"
        unique_together = ['user', 'lesson']
    
    def __str__(self):
        return f"{self.user.username} - {self.lesson.title}"
    
    def get_progress_percentage(self):
        """Возвращает процент просмотра урока"""
        if self.lesson.duration == 0:
            return 0
        return min(100, (self.watched_seconds / self.lesson.duration) * 100)
