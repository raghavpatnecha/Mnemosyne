class Config:
    class MONGO:
        USERNAME: str = "admin"
        PWRD: str = "admin123"
        DB_NAME: str = "Mnemosyne"
        COLLECTION: str = "medium"
    
    class FIRECRAWL:
        API_KEY: str = "API_KEY"

    class OPENAI:
        API_KEY: str = ""

    class LLM:
        MODEL_NAME: str = "llama3.2" #mistral
        TOKEN_LIMIT: int = 125000
        TEMPERATURE: float = 0.1
        OPENAI_TIMEOUT: int = 20