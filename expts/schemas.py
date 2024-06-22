from typing import Annotated
from pydantic import BaseModel, AfterValidator
from pydantic.networks import IPvAnyAddress

class IPModel(BaseModel):
    ip: Annotated[IPvAnyAddress, AfterValidator(str)]
