# urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.letter_list, name='letter_list'),
    path('upload/', views.upload_letter, name='upload_letter'),
    path('letter/<int:letter_id>/analyze/', views.analyze_letter, name='analyze_letter'),
    path('letter/<int:letter_id>/analysis/', views.analysis_results, name='analysis_results'),
    path('letter/<int:letter_id>/generate-response/', views.generate_responses, name='generate_responses'),
    path('letter/<int:letter_id>/', views.letter_detail, name='letter_detail'),
    path('letter/<int:letter_id>/update-status/', views.update_letter_status, name='update_letter_status'),
    path('statistics/', views.get_letter_statistics, name='letter_statistics'),
    path('classification-settings/', views.classification_settings, name='classification_settings'),
    path('classification-settings/confirm/', views.confirm_classification_change, name='confirm_classification_change'),
    path('classification-settings/reset/', views.reset_to_default_categories, name='reset_to_default_categories'),
    path('classification-settings/reset/confirm/', views.confirm_classification_reset,
         name='confirm_classification_reset'),
    path('letter/<int:letter_id>/ask-question/', views.ask_question, name='ask_question'),
]