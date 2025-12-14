import os
import structlog
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

logger = structlog.get_logger(__name__)

def setup_tracing(app, service_name: str, sqlalchemy_engine=None):
    """
    Configure OpenTelemetry Tracing
    
    Args:
        app: FastAPI app instance
        service_name: Name of the service (e.g., 'b2b-api')
        sqlalchemy_engine: Optional SQLAlchemy engine to instrument
    """
    
    otel_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    
    if not otel_endpoint:
        logger.info("Tracing disabled or console-only (OTEL_EXPORTER_OTLP_ENDPOINT not set)")
        # Optionally set up console exporter for local debug if desired,
        # but usually we want to keep logs clean unless debugging.
        return

    logger.info(f"Setting up OTLP Tracing for {service_name} at {otel_endpoint}")

    # 1. Setup Resource (Service Identity)
    resource = Resource.create({
        SERVICE_NAME: service_name,
        "environment": os.getenv("ENVIRONMENT", "local")
    })

    # 2. Setup Provider
    provider = TracerProvider(resource=resource)
    
    # 3. Setup Exporter
    # Use HTTP by default as it's fire-and-forget and easier than gRPC in some setups
    otlp_exporter = OTLPSpanExporter(endpoint=f"{otel_endpoint}/v1/traces")
    
    # 4. Add Processor (Batch is better for prod)
    processor = BatchSpanProcessor(otlp_exporter)
    provider.add_span_processor(processor)
    
    # Set Global Provider
    trace.set_tracer_provider(provider)

    # 5. Instrument FastAPI
    FastAPIInstrumentor().instrument_app(app, tracer_provider=provider)

    # 6. Instrument SQLAlchemy
    if sqlalchemy_engine:
        SQLAlchemyInstrumentor().instrument(
            engine=sqlalchemy_engine,
            tracer_provider=provider
        )
