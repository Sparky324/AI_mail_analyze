from bank_letters.services.llm_client import LLMClient

llm_client = LLMClient()
llm_client.load_txt_files_to_vector_store()