from django import forms
from .models import Letter

class LetterUploadForm(forms.ModelForm):
    class Meta:
        model = Letter
        fields = ['sender', 'subject', 'original_text']
        widgets = {
            'sender': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Например: Иванов Иван Иванович или ООО "Ромашка"'
            }),
            'subject': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Краткая тема письма'
            }),
            'original_text': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 10,
                'placeholder': 'Введите полный текст письма...'
            })
        }
        help_texts = {
            'sender': 'Укажите отправителя письма',
            'subject': 'Введите тему письма',
            'original_text': 'Вставьте текст письма для анализа',
        }