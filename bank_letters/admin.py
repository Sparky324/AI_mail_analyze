from django.contrib import admin
from .models import Letter, AnalysisResult, GeneratedResponse

@admin.register(Letter)
class LetterAdmin(admin.ModelAdmin):
    list_display = ['id', 'get_short_subject', 'sender', 'classification', 'criticality_level', 'status', 'uploaded_at']
    list_filter = ['status', 'classification', 'criticality_level']
    search_fields = ['subject', 'sender', 'original_text']
    list_display_links = ['id', 'get_short_subject']

admin.site.register(AnalysisResult)
admin.site.register(GeneratedResponse)