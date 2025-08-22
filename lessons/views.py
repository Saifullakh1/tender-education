from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.views.generic import ListView, DetailView
from django.http import JsonResponse, HttpResponseForbidden
from django.utils import timezone
from django.db.models import Q
from .models import VideoLesson, Category, UserAccess, LessonProgress
from .forms import VideoLessonForm, CategoryForm, UserAccessForm, UserRegistrationForm


class LessonListView(LoginRequiredMixin, ListView):
    """Список доступных уроков"""
    model = VideoLesson
    template_name = 'lessons/lesson_list.html'
    context_object_name = 'lessons'
    paginate_by = 12
    
    def get_queryset(self):
        """Получаем только уроки, к которым у пользователя есть доступ"""
        user = self.request.user
        if user.is_staff:
            # Админы видят все уроки
            return VideoLesson.objects.filter(is_active=True)
        else:
            # Если админ включил глобальный допуск в профиле, показываем все активные уроки
            # Глобальный доступ через запись UserAccess(is_approved=True)
            has_global = UserAccess.objects.filter(
                user=user,
                is_approved=True,
                is_active=True
            ).filter(Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now())).exists()
            if has_global:
                return VideoLesson.objects.filter(is_active=True)

            # Иначе показываем только уроки с явным доступом
            valid_access = UserAccess.objects.filter(
                user=user,
                is_active=True
            ).filter(
                Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now())
            ).values_list('lesson_id', flat=True)

            return VideoLesson.objects.filter(
                id__in=valid_access,
                is_active=True
            )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all()
        context['user_progress'] = {}
        
        if not self.request.user.is_staff:
            # Получаем прогресс пользователя
            progress = LessonProgress.objects.filter(
                user=self.request.user,
                lesson__in=context['lessons']
            )
            for prog in progress:
                context['user_progress'][prog.lesson.id] = prog
        
        return context


class LessonDetailView(LoginRequiredMixin, DetailView):
    """Детальная страница урока"""
    model = VideoLesson
    template_name = 'lessons/lesson_detail.html'
    context_object_name = 'lesson'
    
    def dispatch(self, request, *args, **kwargs):
        """Проверяем доступ к уроку"""
        lesson = self.get_object()
        user = request.user
        
        if user.is_staff:
            return super().dispatch(request, *args, **kwargs)

        # Глобальный доступ через запись UserAccess(is_approved=True)
        has_global = UserAccess.objects.filter(
            user=user,
            is_approved=True,
            is_active=True
        ).filter(Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now())).exists()
        if has_global:
            return super().dispatch(request, *args, **kwargs)
        
        # Проверяем явный доступ
        try:
            access = UserAccess.objects.get(
                user=user,
                lesson=lesson,
                is_active=True
            )
            if not access.is_valid():
                messages.error(request, "Ваш доступ к этому уроку истек.")
                return redirect('lessons:lesson_list')
        except UserAccess.DoesNotExist:
            messages.error(request, "У вас нет доступа к этому уроку.")
            return redirect('lessons:lesson_list')
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        lesson = self.get_object()
        user = self.request.user
        
        # Получаем или создаем прогресс
        progress, created = LessonProgress.objects.get_or_create(
            user=user,
            lesson=lesson
        )
        context['progress'] = progress
        
        return context


@login_required
def update_progress(request, lesson_id):
    """Обновление прогресса просмотра урока"""
    if request.method == 'POST':
        lesson = get_object_or_404(VideoLesson, id=lesson_id)
        watched_seconds = int(request.POST.get('watched_seconds', 0))
        
        # Проверяем доступ
        if not request.user.is_staff:
            try:
                access = UserAccess.objects.get(
                    user=request.user,
                    lesson=lesson,
                    is_active=True
                )
                if not access.is_valid():
                    return HttpResponseForbidden("Доступ истек")
            except UserAccess.DoesNotExist:
                return HttpResponseForbidden("Нет доступа")
        
        # Обновляем прогресс
        progress, created = LessonProgress.objects.get_or_create(
            user=request.user,
            lesson=lesson
        )
        
        progress.watched_seconds = watched_seconds
        
        # Проверяем завершение урока (90% просмотра)
        if watched_seconds >= lesson.duration * 0.9:
            progress.is_completed = True
        
        progress.save()
        
        return JsonResponse({
            'success': True,
            'progress_percentage': progress.get_progress_percentage(),
            'is_completed': progress.is_completed
        })
    
    return JsonResponse({'success': False})


# Админские views
class AdminRequiredMixin(UserPassesTestMixin):
    """Миксин для проверки прав администратора"""
    def test_func(self):
        return self.request.user.is_staff


class AdminLessonListView(AdminRequiredMixin, ListView):
    """Список всех уроков для админа"""
    model = VideoLesson
    template_name = 'lessons/admin/lesson_list.html'
    context_object_name = 'lessons'
    paginate_by = 20


@login_required
def admin_lesson_create(request):
    """Создание нового урока (только для админов)"""
    if not request.user.is_staff:
        messages.error(request, "У вас нет прав для создания уроков.")
        return redirect('lesson_list')
    
    if request.method == 'POST':
        form = VideoLessonForm(request.POST, request.FILES)
        if form.is_valid():
            lesson = form.save()
            messages.success(request, f"Урок '{lesson.title}' успешно создан.")
            return redirect('admin_lesson_list')
    else:
        form = VideoLessonForm()
    
    return render(request, 'lessons/admin/lesson_form.html', {'form': form})


@login_required
def admin_lesson_edit(request, pk):
    """Редактирование урока (только для админов)"""
    if not request.user.is_staff:
        messages.error(request, "У вас нет прав для редактирования уроков.")
        return redirect('lesson_list')
    
    lesson = get_object_or_404(VideoLesson, pk=pk)
    
    if request.method == 'POST':
        form = VideoLessonForm(request.POST, request.FILES, instance=lesson)
        if form.is_valid():
            form.save()
            messages.success(request, f"Урок '{lesson.title}' успешно обновлен.")
            return redirect('admin_lesson_list')
    else:
        form = VideoLessonForm(instance=lesson)
    
    return render(request, 'lessons/admin/lesson_form.html', {'form': form, 'lesson': lesson})


@login_required
def manage_user_access(request, lesson_id):
    """Управление доступом пользователей к уроку"""
    if not request.user.is_staff:
        messages.error(request, "У вас нет прав для управления доступом.")
        return redirect('lesson_list')
    
    lesson = get_object_or_404(VideoLesson, id=lesson_id)
    
    if request.method == 'POST':
        form = UserAccessForm(request.POST)
        if form.is_valid():
            access = form.save(commit=False)
            access.lesson = lesson
            access.granted_by = request.user
            access.save()
            messages.success(request, f"Доступ к уроку '{lesson.title}' предоставлен пользователю {access.user.username}.")
            return redirect('manage_user_access', lesson_id=lesson_id)
    else:
        form = UserAccessForm()
    
    # Получаем текущие доступы
    current_accesses = UserAccess.objects.filter(lesson=lesson).select_related('user')
    
    context = {
        'lesson': lesson,
        'form': form,
        'current_accesses': current_accesses,
    }
    
    return render(request, 'lessons/admin/manage_access.html', context)


@login_required
def revoke_access(request, access_id):
    """Отзыв доступа пользователя"""
    if not request.user.is_staff:
        messages.error(request, "У вас нет прав для отзыва доступа.")
        return redirect('lesson_list')
    
    access = get_object_or_404(UserAccess, id=access_id)
    access.is_active = False
    access.save()
    
    messages.success(request, f"Доступ пользователя {access.user.username} к уроку '{access.lesson.title}' отозван.")
    return redirect('manage_user_access', lesson_id=access.lesson.id)


def register(request):
    """Регистрация нового пользователя"""
    if request.user.is_authenticated:
        return redirect('lessons:lesson_list')
    
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(
                request, 
                f'Аккаунт для пользователя {user.username} успешно создан! '
                'Теперь вы можете войти в систему. Обратитесь к администратору для получения доступа к урокам.'
            )
            return redirect('login')
    else:
        form = UserRegistrationForm()
    
    return render(request, 'registration/register.html', {'form': form})
