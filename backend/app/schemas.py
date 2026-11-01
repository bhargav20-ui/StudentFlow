from pydantic import BaseModel, Field

class QueryRequest(BaseModel):
    question: str = Field(min_length=5, max_length=3000)
    mode: str = Field(default="multi_agent", pattern="^(multi_agent|single_agent)$")

class DocumentRequest(BaseModel):
    title: str = Field(min_length=3, max_length=180)
    source: str = Field(default="user-added", min_length=1, max_length=300)
    text: str = Field(min_length=30, max_length=20000)

class CompareRequest(BaseModel):
    question: str = Field(min_length=5, max_length=3000)
