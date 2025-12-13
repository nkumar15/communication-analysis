"""
Core Tasks Package

Contains Celery task definitions for background processing.
"""

from core.tasks.celery_app import celery_app

__all__ = ['celery_app']
