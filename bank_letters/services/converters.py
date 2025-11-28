from bank_letters.services.models import *

def llm_category_to_classification_choices_model(category):
    match category:
        case TopicCategory.INFORMATION_REQUEST: return 1
        case TopicCategory.COMPLAINT: return 2
        case TopicCategory.GOVERNMENT_REQUEST: return 3
        case TopicCategory.PARTNER_DEAL: return 4
        case TopicCategory.APPROVAL_REQUEST: return 5
        case TopicCategory.NOTICE:
            return 6
        case _:
            return 7

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