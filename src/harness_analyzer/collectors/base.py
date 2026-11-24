"""数据采集器基类"""
from abc import ABC, abstractmethod
from datetime import datetime
from pydantic import BaseModel, Field


class CollectedData(BaseModel):
    """采集到的数据"""
    source_url: str
    source_type: str
    title: str
    content: str
    collected_at: datetime = Field(default_factory=datetime.now)


class BaseCollector(ABC):
    """采集器基类"""
    @abstractmethod
    async def collect(self, app) -> list[CollectedData]:
        ...
