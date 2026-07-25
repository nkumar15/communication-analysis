from typing import List
from pydantic import BaseModel
from modules.b2b.schemas.roles import ResourceResponse, ActionResponse

class ActionsAllResponse(BaseModel):
    resources: List[ResourceResponse]
    actions: List[ActionResponse]
