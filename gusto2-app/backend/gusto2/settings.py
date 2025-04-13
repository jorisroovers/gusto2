"""
Application settings module using Pydantic for configuration management.
This centralizes all environment variables and configuration in one place
with proper typing and validation.
"""
import os
from typing import Optional
from pydantic import BaseModel, Field, validator

class Settings(BaseModel):
    """Application settings loaded from environment variables"""
    
    # OpenAI Configuration
    openai_api_key: Optional[str] = Field(None, description="OpenAI API key")
    openai_model: str = Field("gpt-4-turbo-preview", description="OpenAI model to use")
    openai_base_url: Optional[str] = Field(None, description="Optional base URL for OpenAI API")
    
    # Notion API Configuration
    notion_api_token: Optional[str] = Field(None, description="Notion API token")
    notion_mealplan_page_id: Optional[str] = Field(None, description="Notion meal plan page ID")
    
    # Application Configuration
    debug: bool = Field(False, description="Debug mode flag")
    
    class Config:
        """Pydantic config"""
        case_sensitive = False  # Case-insensitive environment variable names
        
    @validator('openai_api_key', 'notion_api_token', pre=True)
    def check_api_keys(cls, v, values, **kwargs):
        """Validate API keys are provided when needed"""
        if v == "":
            return None
        return v

    def get_openai_client_kwargs(self) -> dict:
        """Get kwargs for initializing the OpenAI client"""
        kwargs = {"api_key": self.openai_api_key}
        if self.openai_base_url:
            kwargs["base_url"] = self.openai_base_url
        return kwargs

# Create a global settings instance
settings = Settings(
    # Load from environment variables with fallbacks
    openai_api_key=os.environ.get("OPENAI_API_KEY"),
    openai_model=os.environ.get("OPENAI_MODEL", "gpt-4-turbo-preview"),
    openai_base_url=os.environ.get("OPENAI_BASE_URL"),
    notion_api_token=os.environ.get("NOTION_API_TOKEN"),
    notion_mealplan_page_id=os.environ.get("NOTION_MEALPLAN_PAGE_ID"),
    debug=os.environ.get("GUSTO2_DEBUG", "").lower() == "true",
)
