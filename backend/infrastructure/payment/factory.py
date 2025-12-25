"""
Payment Provider Factory

Factory pattern for creating payment provider instances.
"""
from typing import Dict, Any
from .provider import PaymentProvider
from .stripe_provider import StripeProvider


class PaymentProviderFactory:
    """
    Factory for creating payment provider instances.
    """
    
    _providers = {
        'stripe': StripeProvider,
        # Add more providers as they're implemented:
        # 'razorpay': RazorpayProvider,
        # 'xendit': XenditProvider,
    }
    
    @classmethod
    def create(cls, provider_name: str, config: Dict[str, Any]) -> PaymentProvider:
        """
        Create a payment provider instance.
        
        Args:
            provider_name: Name of the provider ('stripe', 'razorpay', 'xendit')
            config: Provider-specific configuration
            
        Returns:
            PaymentProvider instance
            
        Raises:
            ValueError: If provider_name is not supported
        """
        provider_class = cls._providers.get(provider_name.lower())
        
        if not provider_class:
            raise ValueError(
                f"Unsupported payment provider: {provider_name}. "
                f"Supported providers: {', '.join(cls._providers.keys())}"
            )
        
        return provider_class(config)
    
    @classmethod
    def list_providers(cls) -> list[str]:
        """
        Get list of supported provider names.
        
        Returns:
            List of provider names
        """
        return list(cls._providers.keys())
