from pydantic import BaseModel

from agents.builtins.sql.services import DatabaseService


class AgentWithSQLToolsPermissions(BaseModel):
    create: bool = True
    read: bool = True
    update: bool = True
    delete: bool = True


class AgentWithSQLToolsOptions(BaseModel):
    permissions: AgentWithSQLToolsPermissions
