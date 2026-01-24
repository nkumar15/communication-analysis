"""
Plugin Detection Service - Region and Classification detection strategies.

Loads tenant's ingestion config from database and applies detection strategies
to determine data_region_id and sensitivity_level_id for communications.
"""
import re
import uuid
from typing import Optional, List, Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.logging import get_logger
from modules.domains.b2b.bank_surveillance.models import (
    Communication,
    IngestionConfig,
    IngestionConfigTemplate,
)

logger = get_logger(__name__)


class PluginDetectionService:
    """Service for detecting region and classification during ingestion."""
    
    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id
        self._config: Optional[IngestionConfig] = None
    
    async def load_config(self) -> Optional[IngestionConfig]:
        """Load tenant's ingestion config from database (lazy loaded)."""
        if self._config is None:
            result = await self.db.execute(
                select(IngestionConfig).where(IngestionConfig.tenant_id == self.tenant_id)
            )
            self._config = result.scalar_one_or_none()
        return self._config
    
    async def detect_region(self, communication: Communication) -> Optional[uuid.UUID]:
        """
        Detect data region for a communication based on tenant's configured strategy.
        
        Strategies:
        - default: Return default_region_id
        - sender_lookup: Lookup sender domain in sender_domain_map
        - content_rules: (Future) Use content-based detection
        
        Returns:
            UUID of the detected region, or None if not detected
        """
        config = await self.load_config()
        if not config:
            logger.warning(f"No ingestion config found for tenant {self.tenant_id}")
            return None
        
        strategy = config.region_strategy or "default"
        
        if strategy == "sender_lookup":
            region_id = self._lookup_sender_domain(
                communication.sender, 
                config.sender_domain_map or {}
            )
            if region_id:
                return uuid.UUID(region_id) if isinstance(region_id, str) else region_id
        
        # Fallback to default
        return config.default_region_id or config.fallback_region_id
    
    async def detect_classification(self, communication: Communication) -> Optional[uuid.UUID]:
        """
        Detect sensitivity level for a communication based on tenant's configured strategy.
        
        Strategies:
        - default: Return default_level_id
        - channel_map: Lookup channel type in channel_map
        - content_rules: Match content against regex patterns
        
        Returns:
            UUID of the detected sensitivity level, or None if not detected
        """
        config = await self.load_config()
        if not config:
            logger.warning(f"No ingestion config found for tenant {self.tenant_id}")
            return None
        
        strategy = config.classification_strategy or "default"
        
        if strategy == "channel_map":
            channel = communication.channel.lower() if communication.channel else ""
            channel_map = config.channel_map or {}
            if channel in channel_map:
                level_id = channel_map[channel]
                return uuid.UUID(level_id) if isinstance(level_id, str) else level_id
        
        elif strategy == "content_rules":
            content_rules = config.content_rules or []
            matched_level = self._match_content_rules(communication, content_rules)
            if matched_level:
                return matched_level
        
        # Fallback to default
        return config.default_level_id
    
    def _lookup_sender_domain(self, sender: str, domain_map: Dict[str, str]) -> Optional[str]:
        """Lookup sender's domain in the domain map."""
        if not sender or not domain_map:
            return None
        
        # Extract domain from email
        if "@" in sender:
            domain = "@" + sender.split("@")[-1].lower()
            # Try exact match
            if domain in domain_map:
                return domain_map[domain]
            # Try without @ prefix
            domain_no_at = sender.split("@")[-1].lower()
            if domain_no_at in domain_map:
                return domain_map[domain_no_at]
        
        return None
    
    def _match_content_rules(
        self, 
        communication: Communication, 
        rules: List[Dict[str, Any]]
    ) -> Optional[uuid.UUID]:
        """Match communication content against content rules."""
        content = (communication.content or "").lower()
        subject = (communication.subject or "").lower()
        full_text = f"{subject} {content}"
        
        for rule in rules:
            pattern = rule.get("pattern", "")
            level_id = rule.get("level_id") or rule.get("level")
            
            if not pattern or not level_id:
                continue
            
            try:
                if re.search(pattern, full_text, re.IGNORECASE):
                    # Resolve level name to UUID if needed
                    if isinstance(level_id, str) and not self._is_uuid(level_id):
                        # It's a level name like "restricted", resolve later
                        # For now, skip (would need DB lookup)
                        continue
                    return uuid.UUID(level_id) if isinstance(level_id, str) else level_id
            except re.error as e:
                logger.warning(f"Invalid regex pattern '{pattern}': {e}")
        
        return None
    
    @staticmethod
    def _is_uuid(value: str) -> bool:
        """Check if a string is a valid UUID."""
        try:
            uuid.UUID(value)
            return True
        except (ValueError, AttributeError):
            return False


async def clone_template_for_tenant(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    default_region_id: Optional[uuid.UUID] = None,
    default_level_id: Optional[uuid.UUID] = None,
    template_name: str = None
) -> IngestionConfig:
    """
    Clone an ingestion config template for a new tenant.
    
    Called during tenant onboarding/activation.
    
    Args:
        db: Database session
        tenant_id: Tenant UUID
        default_region_id: Tenant's default region (resolved from tenant data)
        default_level_id: Default sensitivity level (typically "Internal")
        template_name: Optional template name (uses default if not specified)
    
    Returns:
        The created IngestionConfig for the tenant
    """
    # Find template
    if template_name:
        result = await db.execute(
            select(IngestionConfigTemplate).where(IngestionConfigTemplate.name == template_name)
        )
    else:
        result = await db.execute(
            select(IngestionConfigTemplate).where(IngestionConfigTemplate.is_default == True)
        )
    
    template = result.scalar_one_or_none()
    if not template:
        logger.warning("No ingestion config template found, creating with defaults")
        template = IngestionConfigTemplate(name="default", is_default=True)
    
    # Clone to tenant config
    config = IngestionConfig(
        tenant_id=tenant_id,
        template_id=template.id if template.id else None,
        region_strategy=template.region_strategy,
        default_region_id=default_region_id,
        fallback_region_id=None,
        sender_domain_map=template.sender_domain_map or {},
        classification_strategy=template.classification_strategy,
        default_level_id=default_level_id,
        channel_map=template.channel_map or {},
        content_rules=template.content_rules or [],
    )
    
    db.add(config)
    logger.info(f"Created ingestion config for tenant {tenant_id} from template '{template.name}'")
    
    return config
