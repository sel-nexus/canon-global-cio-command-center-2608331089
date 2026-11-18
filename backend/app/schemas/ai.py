"""Define bounded assistant requests and structured provider responses."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Tab = Literal['strategic', 'executive-summary', 'business', 'operations', 'governance', 'innovation', 'partnerships']


class ChatRequest(BaseModel):
    """Accept a concise question scoped to one dashboard tab."""
    model_config = ConfigDict(extra='forbid')
    query: str = Field(min_length=1, max_length=1000)
    context_tab: Tab

    @field_validator('query')
    @classmethod
    def nonblank(cls, value: str) -> str:
        """Reject whitespace-only questions."""
        if not value.strip():
            raise ValueError('Question must not be blank')
        return value.strip()


class Analysis(BaseModel):
    """Validate only a provider-supplied narrative, actions and confidence."""
    model_config = ConfigDict(extra='forbid')
    narrative: str = Field(min_length=1, max_length=5000)
    actions: list[str] = Field(max_length=10)
    confidence: str | None = Field(default=None, max_length=200)

    @field_validator('actions')
    @classmethod
    def bounded_actions(cls, value: list[str]) -> list[str]:
        """Reject empty or excessively long individual actions."""
        if any(not item.strip() or len(item) > 500 for item in value):
            raise ValueError('Invalid action')
        return value


class ChatResponse(Analysis):
    """Identify the response source and include independent limitations."""
    source: Literal['provider', 'mock']
    limitations: list[str]


class Recommendation(BaseModel):
    """Describe a query that can be sent in a known tab context."""
    label: str
    query: str
    context_tab: Tab
