from sqlalchemy import Sequence
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.ext.asyncio import AsyncAttrs


class BaseDBT(AsyncAttrs, DeclarativeBase):
    pass


class Users(BaseDBT):
    __tablename__ = "Users_T"
    user_id: Mapped[int] = mapped_column(primary_key=True)
    user_id_seq = Sequence(name="Users_S", metadata=BaseDBT.metadata)


class Polls(BaseDBT):
    __tablename__ = "Polls_T"
    poll_id: Mapped[int] = mapped_column(primary_key=True)
    poll_id_seq = Sequence(name="Polls_S", metadata=BaseDBT.metadata)


class CodeData(BaseDBT):
    __tablename__ = "CodeData_T"
    cd_id: Mapped[int] = mapped_column(primary_key=True)
    cd_id_seq = Sequence(name="CodeData_S", metadata=BaseDBT.metadata)

