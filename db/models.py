from __future__ import annotations
import datetime


from .database import Base
from sqlalchemy.orm import mapped_column, relationship, Mapped
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.sql import func
from sqlalchemy import Integer, String, Boolean, DateTime, Text, ForeignKey

class User(Base):
    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str | None] = mapped_column(String, nullable=True)
    first_name: Mapped[str] = mapped_column(String, nullable=False)
    last_name: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ref_code: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    count_read_cancel: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    notes: Mapped[list["Note"]] = relationship("Note", back_populates="created_by_user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.user_id}, username={self.username})>"

class Note(Base):
    __tablename__ = "notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    for_user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    fake_is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_by_user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.user_id"), nullable=False)
    created_by_user: Mapped["User"] = relationship("User", back_populates="notes")

    def __repr__(self):
        return f"<Note(id={self.id}, for_user_id={self.for_user_id}, is_read={self.is_read})>"

class AdminPanel(Base):
    __tablename__ = "admin_panel"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    admin_user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.user_id"), nullable=False)
    total_earnings: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_read_cancels_sold: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_restart: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=func.now())

    admin_user: Mapped["User"] = relationship("User")

    def __repr__(self):
        return f"<AdminPanel(id={self.id}, admin_user_id={self.admin_user_id})>"