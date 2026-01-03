import os
import email
from email.policy import default
from datetime import datetime
from typing import List, Optional
import aiofiles
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from backend.modules.domains.enron.services.rag import enron_rag_service

from backend.modules.domains.enron.models import EnronEmail
from backend.modules.domains.enron.schemas import EnronEmailCreate

class EnronIngestionService:
    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    def parse_email_content(self, content: str) -> Optional[EnronEmailCreate]:
        """Parses a raw email string into an EnronEmailCreate object."""
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

            return EnronEmailCreate(
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

    async def ingest_file(self, file_path: str) -> bool:
        """Reads a file, parses it, saves to DB, and indexes specific to RAG."""
        try:
            async with aiofiles.open(file_path, mode='r', errors='ignore') as f:
                content = await f.read()
                
            email_data = self.parse_email_content(content)
            if not email_data:
                return False
                
            # Check duplicates (Message-ID)
            stmt = select(EnronEmail).where(EnronEmail.message_id == email_data.message_id)
            result = await self.db.execute(stmt)
            if result.scalar_one_or_none():
                return False # Skip duplicate

            # Save to Postgres
            db_email = EnronEmail(**email_data.dict())
            self.db.add(db_email)
            
            # --- RAG Indexing ---
            # Generate deterministic Tenant ID from "maildir/{username}" if possible, else default
            # heuristic: path contains .../maildir/username/...
            username = "unknown"
            parts = file_path.split("/")
            if "maildir" in parts:
                idx = parts.index("maildir")
                if idx + 1 < len(parts):
                    username = parts[idx + 1]
            
            tenant_id = uuid.uuid5(uuid.NAMESPACE_DNS, username)
            
            metadata = {
                "sender": email_data.sender,
                "recipients": ",".join(email_data.recipients),
                "subject": email_data.subject,
                "date": str(email_data.date),
                "message_id": email_data.message_id,
                "original_filename": file_path,
                "content_hash": email_data.message_id # Use Message-ID as unique hash for dedup in RAG
            }

            try:
                await enron_rag_service.ingest_document(
                    db=self.db,
                    tenant_id=tenant_id,
                    file_path=file_path,
                    document_metadata=metadata
                )
            except Exception as rag_err:
                # Log but don't fail the DB insert? Or fail? 
                # For POC, let's print and continue, effectively "soft fail" on RAG
                print(f"RAG Indexing warning for {file_path}: {rag_err}")

            return True
            
        except Exception as e:
            print(f"Failed to ingest {file_path}: {e}")
            return False

    async def bulk_ingest(self, file_paths: List[str], batch_size: int = 100) -> int:
        """Ingests a list of files in batches."""
        count = 0
        batch_count = 0
        
        for file_path in file_paths:
            success = await self.ingest_file(file_path)
            if success:
                count += 1
                batch_count += 1
            
            if batch_count >= batch_size:
                await self.db.commit()
                batch_count = 0
                
        if batch_count > 0:
            await self.db.commit()
            
        return count
