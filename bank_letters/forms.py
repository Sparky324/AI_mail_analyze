from django import forms
from .models import Letter
from .models import ClassificationCategory

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


class ClassificationCategoryForm(forms.ModelForm):
    class Meta:
        model = ClassificationCategory
        fields = ['number', 'name', 'description']


class ClassificationCategoriesForm(forms.Form):
    """Форма для множественного ввода категорий"""
    categories = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 10,
            'placeholder': 'Введите категории в формате:\n1. Название первой категории\n2. Название второй категории\n3. Название третьей категории\n...',
            'class': 'form-control'
        }),
        label='Категории классификации',
        help_text='Введите каждую категорию с новой строки в формате "номер. название". Допустимо от 2 до 9 категорий.'
    )

    def clean_categories(self):
        categories_text = self.cleaned_data['categories']
        lines = [line.strip() for line in categories_text.split('\n') if line.strip()]

        if len(lines) < 2:
            raise forms.ValidationError("Должно быть не менее 2 категорий")
        if len(lines) > 9:
            raise forms.ValidationError("Должно быть не более 9 категорий")

        categories = []
        for line in lines:
            # Парсим строки вида "1. Название категории"
            if '.' in line:
                parts = line.split('.', 1)
                try:
                    number = int(parts[0].strip())
                    name = parts[1].strip()
                    if not name:
                        raise forms.ValidationError(f"Название категории не может быть пустым для номера {number}")
                    categories.append((number, name))
                except (ValueError, IndexError):
                    raise forms.ValidationError(f"Неверный формат строки: {line}. Используйте формат 'номер. название'")
            else:
                raise forms.ValidationError(f"Неверный формат строки: {line}. Используйте формат 'номер. название'")

        # Проверяем уникальность номеров
        numbers = [cat[0] for cat in categories]
        if len(numbers) != len(set(numbers)):
            raise forms.ValidationError("Номера категорий должны быть уникальными")

        return categories