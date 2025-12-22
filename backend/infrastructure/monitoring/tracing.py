import os
import structlog
from typing import Optional
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

logger = structlog.get_logger(__name__)

def get_tracer_provider(service_name: str) -> Optional[TracerProvider]:
    """Factory to create TracerProvider based on configuration"""
    from core.config import settings
    
    if settings.tracing_provider == "none":
        logger.info("Tracing disabled (tracing_provider='none')")
        return None
        
    logger.info(f"Setting up Tracing with provider: {settings.tracing_provider}")
    
    # 1. Setup Resource
    resource = Resource.create({
        SERVICE_NAME: service_name,
        "environment": os.getenv("ENVIRONMENT", "local")
    })
    
    provider = TracerProvider(resource=resource)
    
    # 2. Setup Exporter
    processor = None
    
    if settings.tracing_provider == "otlp":
        otel_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
        if otel_endpoint:
            otlp_exporter = OTLPSpanExporter(endpoint=f"{otel_endpoint}/v1/traces")
            processor = BatchSpanProcessor(otlp_exporter)
            logger.info(f"OTLP Exporter configured for {otel_endpoint}")
        else:
            logger.warning("tracing_provider='otlp' but OTEL_EXPORTER_OTLP_ENDPOINT not set. Falling back to No-Op.")
            return None
            
    elif settings.tracing_provider == "console":
        console_exporter = ConsoleSpanExporter()
        processor = BatchSpanProcessor(console_exporter)
        logger.info("Console Exporter configured")
        
    else:
        logger.warning(f"Unknown tracing_provider '{settings.tracing_provider}', disabling tracing")
        return None
        
    if processor:
        provider.add_span_processor(processor)
        
    return provider


def setup_tracing(app, service_name: str, sqlalchemy_engine=None):
    """
    Configure OpenTelemetry Tracing using Factory Pattern
    """
    provider = get_tracer_provider(service_name)
    
    if not provider:
        return
        
    # Set Global Provider
    trace.set_tracer_provider(provider)

    # Instrument FastAPI
    FastAPIInstrumentor().instrument_app(app, tracer_provider=provider)

    # Instrument SQLAlchemy
    if sqlalchemy_engine:
        # If it's an AsyncEngine, we must instrument the underlying sync_engine
        engine_to_instrument = getattr(sqlalchemy_engine, "sync_engine", sqlalchemy_engine)
        
        SQLAlchemyInstrumentor().instrument(
            engine=engine_to_instrument,
            tracer_provider=provider
        )
