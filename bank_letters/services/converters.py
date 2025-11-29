from bank_letters.services.models import *

def llm_category_to_classification_choices_model(cat, categories):
    for category in categories:
        if cat == category.get('name'):
            return category.get('number')
    return 1

def llm_response_style_to_model(style):
    match style:
        case ResponseStyle.OFFICIAL: return 1
        case ResponseStyle.CORPORATE: return 2
        case ResponseStyle.CLIENT: return 3
        case _: return 4

def llm_criticality_level_to_model(level):
    match level:
        case CriticalityLevel.LOW: return 1
        case CriticalityLevel.MEDIUM: return 2
        case CriticalityLevel.HIGH: return 3
        case _: return 4