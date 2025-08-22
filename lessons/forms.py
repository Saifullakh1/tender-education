from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import VideoLesson, Category, UserAccess
from django.db.models import Q
from django.utils import timezone


class UserRegistrationForm(UserCreationForm):
    """Форма регистрации пользователей"""
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите ваш email'
        })
    )
    first_name = forms.CharField(
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Имя (необязательно)'
        })
    )
    last_name = forms.CharField(
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Фамилия (необязательно)'
        })
    )
    
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'password1', 'password2')
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Придумайте имя пользователя'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Настраиваем стили для полей паролей
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Придумайте пароль'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Повторите пароль'
        })
        
        # Убираем help_text для полей паролей (он будет показан в шаблоне)
        self.fields['password1'].help_text = ''
        self.fields['password2'].help_text = ''
    
    def clean_email(self):
        """Проверяем уникальность email"""
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('Пользователь с таким email уже существует.')
        return email
    
    def save(self, commit=True):
        """Сохраняем пользователя с дополнительными полями"""
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data.get('first_name', '')
        user.last_name = self.cleaned_data.get('last_name', '')
        
        if commit:
            user.save()
        return user


class VideoLessonForm(forms.ModelForm):
    """Форма для создания/редактирования видео урока"""
    
    class Meta:
        model = VideoLesson
        fields = ['title', 'description', 'video_file', 'thumbnail', 'category', 'duration', 'is_active']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Введите название урока'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Введите описание урока'
            }),
            'video_file': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'video/*'
            }),
            'thumbnail': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
            'category': forms.Select(attrs={
                'class': 'form-control'
            }),
            'duration': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Длительность в секундах'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }
    
    def clean_duration(self):
        """Проверяем, что длительность положительная"""
        duration = self.cleaned_data.get('duration')
        if duration and duration <= 0:
            raise forms.ValidationError("Длительность должна быть больше 0")
        return duration


class CategoryForm(forms.ModelForm):
    """Форма для создания/редактирования категории"""
    
    class Meta:
        model = Category
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Введите название категории'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Введите описание категории'
            })
        }


class UserAccessForm(forms.ModelForm):
    """Форма для предоставления доступа пользователю"""
    
    class Meta:
        model = UserAccess
        fields = ['user', 'expires_at']
        widgets = {
            'user': forms.Select(attrs={
                'class': 'form-control'
            }),
            'expires_at': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Показываем только обычных пользователей (не админов)
        self.fields['user'].queryset = User.objects.filter(is_staff=False).order_by('username')
        self.fields['expires_at'].required = False
    
    def clean_expires_at(self):
        """Проверяем, что дата истечения в будущем"""
        expires_at = self.cleaned_data.get('expires_at')
        if expires_at and expires_at <= timezone.now():
            raise forms.ValidationError("Дата истечения должна быть в будущем")
        return expires_at


class UserSearchForm(forms.Form):
    """Форма для поиска пользователей"""
    search = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Поиск по имени пользователя или email'
        })
    )
    
    def get_users(self):
        """Возвращает отфильтрованных пользователей"""
        search = self.cleaned_data.get('search', '')
        if search:
            return User.objects.filter(
                is_staff=False
            ).filter(
                Q(username__icontains=search) | Q(email__icontains=search)
            ).order_by('username')
        return User.objects.filter(is_staff=False).order_by('username') 