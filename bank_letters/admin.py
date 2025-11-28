from django.contrib import admin
from .models import Letter, AnalysisResult, GeneratedResponse


@admin.register(Letter)
class LetterAdmin(admin.ModelAdmin):
    list_display = ['id', 'subject', 'sender', 'classification', 'criticality_level', 'status', 'uploaded_at']
    list_filter = ['status', 'classification', 'criticality_level']
    search_fields = ['subject', 'sender', 'original_text']
    list_display_links = ['id', 'subject']

    def get_short_subject(self, obj):
        return obj.get_short_subject()

    get_short_subject.short_description = 'Тема'


@admin.register(AnalysisResult)
class AnalysisResultAdmin(admin.ModelAdmin):
    list_display = ['id', 'letter', 'created_at']
    list_filter = ['created_at']


@admin.register(GeneratedResponse)
class GeneratedResponseAdmin(admin.ModelAdmin):
    list_display = ['id', 'letter', 'response_style', 'is_selected', 'generated_at']
    list_filter = ['response_style', 'is_selected']