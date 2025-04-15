# app/schemas/country.py
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional

class CountryBase(BaseModel):
    name: str 
    code: str  
    flag_url: Optional[str] = None  

class CountryCreate(CountryBase):
    pass

class CountryUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    flag_url: Optional[str] = None

class CountryOut(CountryBase):
    country_id: int
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)