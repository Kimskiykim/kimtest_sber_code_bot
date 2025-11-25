from pydantic import BaseModel, Field, ConfigDict
from app.enums import AgentInputModes


class LLMInput(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    history: list[str] = Field(default_factory=list)
    mode: AgentInputModes = AgentInputModes.ZERO
