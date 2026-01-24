import os
import email
from email.policy import default
from datetime import datetime
from typing import List, Optional

import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from modules.domains.b2b.bank_surveillance.services.rag import communication_rag_service # Forward ref, will rename next
from modules.domains.b2b.bank_surveillance.models.communication import Communication

# We will use pydantic models inline or generic ones if needed, but for now let's keep it simple
from pydantic import BaseModel

class EmailParsedData(BaseModel):
    message_id: str
    sender: str
    recipients: List[str]
    subject: str
    body: str
    date: datetime

class CommunicationIngestionService:
    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    def parse_email_content(self, content: str) -> Optional[EmailParsedData]:
        """Parses a raw email string into structured data."""
        try:
            msg = email.message_from_string(content, policy=default)
            
            # Extract basic headers
            sender = msg.get("From", "unknown")
            recipients = []
            if msg.get("To"):
                recipients.extend([addr.strip() for addr in msg.get("To").split(",")])
            if msg.get("Cc"):
                recipients.extend([addr.strip() for addr in msg.get("Cc").split(",")])
            if msg.get("Bcc"):
                recipients.extend([addr.strip() for addr in msg.get("Bcc").split(",")])
            
            # Fallback if no recipients
            if not recipients:
                recipients = ["unknown"]

            subject = msg.get("Subject", "")
            message_id = msg.get("Message-ID", "").strip()
            
            # Date parsing (naive)
            date_str = msg.get("Date")
            email_date = datetime.now()
            if date_str:
                try:
                    # Example Standard email date: Mon, 14 May 2001 16:39:00 -0700
                    from email.utils import parsedate_to_datetime
                    email_date = parsedate_to_datetime(date_str)
                except Exception:
                    pass

            # Body extraction
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                         body += part.get_content()
            else:
                body = msg.get_content()

            return EmailParsedData(
                message_id=message_id,
                sender=sender,
                recipients=recipients,
                subject=subject,
                body=body,
                date=email_date
            )
        except Exception as e:
            print(f"Error parsing email: {e}")
            return None

    async def ingest_message(self, email_data: EmailParsedData, tenant_id: uuid.UUID, source_ref: str = None) -> bool:
        """Core logic to save a parsed message to DB and index it."""
        try:
            # Check duplicates (Message-ID)
            stmt = select(Communication).where(Communication.message_id == email_data.message_id)
            result = await self.db.execute(stmt)
            if result.scalar_one_or_none():
                return False # Skip duplicate

            db_comm = Communication(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                channel="email",
                message_id=email_data.message_id,
                sender=email_data.sender,
                recipients=email_data.recipients,
                subject=email_data.subject,
                recipients=email_data.recipients,
                subject=email_data.subject,
                # content=NULL (Stored in ES only)
                timestamp=email_data.date,
                es_document_id=email_data.message_id # Link to ES Document
            )
            self.db.add(db_comm)
            
            # --- PLUGIN DETECTION: Set region and classification ---
            try:
                from modules.domains.b2b.bank_surveillance.services.plugin_detection import PluginDetectionService
                plugin_service = PluginDetectionService(self.db, tenant_id)
                
                # Detect and set region
                region_id = await plugin_service.detect_region(db_comm)
                if region_id:
                    db_comm.data_region_id = region_id
                
                # Detect and set classification
                level_id = await plugin_service.detect_classification(db_comm)
                if level_id:
                    db_comm.sensitivity_level_id = level_id
            except Exception as plugin_err:
                # Log but don't fail ingestion if plugin detection fails
                print(f"Plugin detection warning: {plugin_err}")
            
            # RAG Indexing is handled by the caller (batch or individual) to avoid double-indexing
            # when running bulk ingestion.
            
            return True
        except Exception as e:
            print(f"Failed to ingest message {email_data.message_id}: {e}")
            return False


    async def ingest_file(self, file_path: str, tenant_id: uuid.UUID) -> bool:
        """Reads a file, parses it, saves to DB as Communication, and indexes specific to RAG."""
        try:
            # Use standard open, for small files in script context this is acceptable
            # For high throughput in async app, use run_in_executor
            with open(file_path, mode='r', errors='ignore') as f:
                content = f.read()
                
            email_data = self.parse_email_content(content)
            if not email_data:
                return False

            # Specific data folder-based heuristic for tenant separation
            derived_tenant_id = tenant_id
            username = "unknown"
            parts = file_path.split("/")
            if "maildir" in parts:
                idx = parts.index("maildir")
                if idx + 1 < len(parts):
                    username = parts[idx + 1]
                    derived_tenant_id = uuid.uuid5(uuid.NAMESPACE_DNS, username)

            success = await self.ingest_message(email_data, derived_tenant_id, source_ref=file_path)
            
            if success:
                # Index to ES immediately for single files
                try:
                    from modules.domains.b2b.bank_surveillance.services.rag import communication_rag_service
                    metadata = {
                        "sender": email_data.sender,
                        "recipients": ",".join(email_data.recipients),
                        "subject": email_data.subject,
                        "date": str(email_data.date),
                        "message_id": email_data.message_id,
                        "tenant_id": str(derived_tenant_id)
                    }
                    full_text = f"Subject: {email_data.subject}\n\n{email_data.body}"
                    await communication_rag_service.index_text(full_text, metadata, doc_id=email_data.message_id)
                except Exception as e:
                    print(f"Failed to index file {file_path}: {e}")
                    
            return success
            
        except Exception as e:
            print(f"Failed to ingest file {file_path}: {e}")
            return False

    async def bulk_ingest(self, file_paths: List[str], base_tenant_id: uuid.UUID = uuid.uuid4(), batch_size: int = 100) -> int:
        """Ingests a list of files in batches."""
        count = 0
        batch_count = 0
        
        for file_path in file_paths:
            success = await self.ingest_file(file_path, base_tenant_id)
            if success:
                count += 1
                batch_count += 1
            
            if batch_count >= batch_size:
                await self.db.commit()
                batch_count = 0
                
        if batch_count > 0:
            await self.db.commit()
            
        return count
