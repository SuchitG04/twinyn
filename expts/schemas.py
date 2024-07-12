from pydantic import BaseModel
from pydantic.networks import IPv4Address

class IPModel(BaseModel):
    ip: IPv4Address
