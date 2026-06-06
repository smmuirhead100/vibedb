from pydantic import BaseModel


class AgentWithSQLToolsPermissions(BaseModel):
    create: bool = True
    read: bool = True
    update: bool = True
    delete: bool = True


class AgentWithSQLToolsOptions(BaseModel):
    permissions: AgentWithSQLToolsPermissions
