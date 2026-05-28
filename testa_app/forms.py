from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import PDFDocument, Bookmark, BookmarkFolder

class UserRegisterForm(UserCreationForm):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'block w-full pl-12 pr-4 py-3 bg-slate-50 border border-slate-300 rounded-xl text-slate-900 font-poppins',
            'placeholder': 'you@university.edu',
            'autocomplete': 'email',
        }),
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('An account with this email already exists.')
        return email




class PDFUploadForm(forms.ModelForm):
    class Meta:
        model = PDFDocument
        fields = ['file', 'title', 'course', 'difficulty_level']
        widgets = {
            'file': forms.ClearableFileInput(attrs={'multiple': False}),
            'title': forms.TextInput(attrs={'placeholder': 'Document title (optional)'}),
            'course': forms.TextInput(attrs={'placeholder': 'Course name (optional)'}),
            'difficulty_level': forms.Select(attrs={'class': 'form-control'}),
        }

    def clean_file(self):
        file = self.cleaned_data.get('file')
        allowed_extensions = ['pdf', 'docx', 'pptx', 'txt']
        extension = file.name.split('.')[-1].lower()
        if extension not in allowed_extensions:
            raise forms.ValidationError('File type not supported.')
        return file


class BookmarkForm(forms.ModelForm):
    class Meta:
        model = Bookmark
        fields = ['title', 'notes', 'folder', 'tags']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Bookmark title'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Personal notes...'}),
            'folder': forms.Select(attrs={'class': 'form-control'}),
        }


class BookmarkFolderForm(forms.ModelForm):
    class Meta:
        model = BookmarkFolder
        fields = ['name', 'description', 'color', 'icon']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Folder name'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Optional description'}),
            'color': forms.TextInput(attrs={'class': 'form-control', 'type': 'color'}),
            'icon': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '📁 Emoji icon'}),
        }
