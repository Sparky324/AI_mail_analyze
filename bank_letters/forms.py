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
        widgets = {
            'number': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 9}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Введите название категории'}),
            'description': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Необязательное описание категории'}),
        }


class ClassificationCategoriesForm(forms.Form):
    """Форма для множественного ввода категорий через интерактивный интерфейс"""
    categories_json = forms.CharField(
        widget=forms.HiddenInput(),
        required=False
    )

    def clean_categories_json(self):
        categories_json = self.cleaned_data['categories_json']
        if not categories_json:
            raise forms.ValidationError("Должна быть хотя бы одна категория")

        try:
            import json
            categories_data = json.loads(categories_json)

            if len(categories_data) < 2:
                raise forms.ValidationError("Должно быть не менее 2 категорий")
            if len(categories_data) > 9:
                raise forms.ValidationError("Должно быть не более 9 категорий")

            # Проверяем уникальность номеров и названий
            numbers = [cat['number'] for cat in categories_data]
            names = [cat['name'].strip() for cat in categories_data]

            if len(numbers) != len(set(numbers)):
                raise forms.ValidationError("Номера категорий должны быть уникальными")

            if len(names) != len(set(names)):
                raise forms.ValidationError("Названия категорий должны быть уникальными")

            # Проверяем, что номера идут по порядку от 1
            expected_numbers = list(range(1, len(categories_data) + 1))
            if numbers != expected_numbers:
                raise forms.ValidationError("Номера категорий должны идти по порядку от 1")

            # Проверяем, что все названия заполнены
            for i, cat in enumerate(categories_data):
                if not cat['name'].strip():
                    raise forms.ValidationError(f"Название категории {i + 1} не может быть пустым")

            return categories_data

        except json.JSONDecodeError:
            raise forms.ValidationError("Неверный формат данных категорий")