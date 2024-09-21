class Config:
    class MONGO:
        USERNAME: str = "USERNAME"
        PWRD: str = "PASSORD"
        DB_NAME: str = "Mnemosyne"
        COLLECTION: str = "medium"
    
    class FIRECRAWL:
        API_KEY: str = "API_KEY"

    class OPENAI:
        API_KEY: str = "API_KEY"

    class LLM:
        MODEL_NAME: str = "gpt-4o"
        TOKEN_LIMIT: int = 125000
        TEMPERATURE: float = 0.01
        OPENAI_TIMEOUT: int = 20