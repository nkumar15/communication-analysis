from core.db.base import Base, TimestampMixin
from sqlalchemy import Column, String, text
from sqlalchemy.dialects.postgresql import UUID, JSONB

class PluginTemplate(Base, TimestampMixin):
    """
    Master Templates for System Plugins.
    Blueprints for seeding tenant-specific data during onboarding/activation.
    """
    __tablename__ = "plugin_templates"
    __table_args__ = {'schema': 'b2b'}

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    plugin_slug = Column(String(50), unique=True, nullable=False, index=True)  # e.g. 'geographic_boundaries'
    template_data = Column(JSONB, nullable=False)  # The YAML content parsed into JSON
