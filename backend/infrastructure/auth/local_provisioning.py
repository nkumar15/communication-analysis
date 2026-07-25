import re
from typing import Optional
from infrastructure.auth.provisioning import TenantProvisioner
from infrastructure.logging import get_logger

logger = get_logger(__name__)


class LocalTenantProvisioner(TenantProvisioner):
    """No-op TenantProvisioner for local/dev use without a real Firebase project.

    Generates a deterministic tenant ID locally instead of calling out to
    Firebase Identity Platform. SSO/OIDC provider configuration isn't
    meaningful without a real identity provider, so it's a no-op.
    """

    def create_tenant(self, company_name: str, domain: str) -> str:
        sanitized = re.sub(r'[^a-z0-9-]', '-', domain.lower())
        tenant_id = f"local-{sanitized}"
        logger.info("local_tenant_created", tenant_id=tenant_id, company_name=company_name)
        return tenant_id

    def configure_oidc_provider(
        self,
        tenant_id: str,
        provider_type: str,
        client_id: str,
        client_secret: str,
        issuer_url: str,
        provider_id_override: Optional[str] = None,
        display_name: Optional[str] = None
    ) -> str:
        provider_id = provider_id_override or f'oidc.{provider_type}'
        logger.info("local_oidc_provider_skipped", tenant_id=tenant_id, provider_id=provider_id)
        return provider_id
