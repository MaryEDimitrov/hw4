"""Pydantic/PydanticAI structured types for the Campus Customs shop agent."""
from pydantic import BaseModel, Field

class ProductSearchHit(BaseModel):
    product_id: str
    name: str
    garment_type: str
    price: float
    description: str = ''
    image_file_path: str = ''

class ProductDetails(BaseModel):
    product_id: str
    name: str
    garment_type: str
    description: str
    colors: list[str] = Field(default_factory=list)
    price: float
    sizes: list[str] = Field(default_factory=list, description="Every known size with an available quantity or sold-out status.")

class StockLookupResult(BaseModel):
    product_id: str
    requested_size: str | None = None
    stock: list[str] = Field(default_factory=list, description="Exact size quantities, explicitly labeling zero quantities as out of stock.")

class ChatResponse(BaseModel):
    reply: str = Field(description='A concise, friendly answer for the shopper.')
    product_ids: list[str] = Field(default_factory=list, description='Products relevant to the reply.')
    product_matches: list[ProductSearchHit] = Field(default_factory=list, description='Structured product cards for the website to render.')

class AuditTrailEvent(BaseModel):
    """Safe, compact shape written one record per line to the audit JSONL file."""
    time: str
    tool_name: str
    args: dict = Field(default_factory=dict, description='Short, non-sensitive operation metadata only.')
    result: dict = Field(default_factory=dict, description='Short outcome summary; never raw private content.')
    stop_reason: str = Field(description='Why this loop/tool event ended, such as completed, tool_returned, or error.')
