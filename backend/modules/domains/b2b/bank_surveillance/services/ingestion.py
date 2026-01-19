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
                    # Example Enron date: Mon, 14 May 2001 16:39:00 -0700 (PDT)
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
                content=email_data.body,
                timestamp=email_data.date
                # data_region_id and sensitivity_level_id would be set by PolicyAgent or Default
            )
            self.db.add(db_comm)
            
            # --- RAG Indexing ---
            metadata = {
                "sender": email_data.sender,
                "recipients": ",".join(email_data.recipients),
                "subject": email_data.subject,
                "date": str(email_data.date),
                "message_id": email_data.message_id,
                "original_filename": source_ref or "unknown",
                "content_hash": email_data.message_id
            }

            try:
                # Using the renamed service (imported as 'communication_rag_service')
                from modules.domains.b2b.bank_surveillance.services.rag import communication_rag_service
                # Hack: ingest_document expects a file path usually, but we might verify if it handles text/metadata only
                # For now, if we have a file path (source_ref), pass it. If it's a CSV row, we might not have a file.
                # If RAG service requires a file, this might need adjustment.
                # Assuming RAG service reads the file content from disk.
                # If we are ingesting from CSV, we have the content in memory. 
                # Let's Skip RAG for CSV flow IF RAG service strictly needs file path.
                # OR we implement text-based ingestion in RAG service.
                # For this refactor step, let's assume source_ref is valid or we skip RAG if invalid.
                if source_ref and os.path.exists(source_ref):
                    await communication_rag_service.ingest_document(
                        db=self.db,
                        tenant_id=tenant_id,
                        file_path=source_ref,
                        document_metadata=metadata
                    )
                else:
                    # TODO: Support direct text ingestion in RAG service
                    pass
            except Exception as rag_err:
                print(f"RAG Indexing warning for {source_ref}: {rag_err}")

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

            # Enron specific heuristic for tenant separation (username based)
            derived_tenant_id = tenant_id
            username = "unknown"
            parts = file_path.split("/")
            if "maildir" in parts:
                idx = parts.index("maildir")
                if idx + 1 < len(parts):
                    username = parts[idx + 1]
                    derived_tenant_id = uuid.uuid5(uuid.NAMESPACE_DNS, username)

            return await self.ingest_message(email_data, derived_tenant_id, source_ref=file_path)
            
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
