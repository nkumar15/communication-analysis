import pytest
import csv
import os
import uuid
from datetime import datetime
from email.utils import parsedate_to_datetime
from sqlalchemy import select
from modules.domains.b2b.bank_surveillance.models.communication import Communication

# Path to the dataset - assuming we are running in a context where this is mounted/available
# If not, we might fail, but this is what the user asked for.
CSV_PATH = "/app/tools/genai_evaluator/datasets/enron/source/emails_small.csv"

@pytest.mark.asyncio
async def test_ingest_csv_to_communication_model(b2b_test_setup):
    """
    Verify that records from the Enron CSV can be mapped to the Communication model
    and persisted to the database.
    """
    setup = b2b_test_setup
    session = setup["session"]
    tenant_id = setup["tenant_id"]

    # Verify file exists
    if not os.path.exists(CSV_PATH):
        pytest.skip(f"CSV dataset not found at {CSV_PATH}")

    # Read and parse CSV
    messages_to_insert = []
    
    # We'll ingest a small batch for verification
    BATCH_SIZE = 5 
    
    with open(CSV_PATH, 'r', encoding='utf-8', errors='replace') as f:
        reader = csv.DictReader(f)
        
        count = 0
        for row in reader:
            if count >= BATCH_SIZE:
                break
                
            # Logic from ingest.py
            try:
                dt = parsedate_to_datetime(row['date'])
            except:
                dt = datetime.now()

            recipients = []
            if row.get('recipients'): recipients.extend(row['recipients'].split(','))
            recipients = [r.strip() for r in recipients if r.strip()]

            # Create Model Instance
            comm = Communication(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                channel="email",
                # sub_channel is now available but optional
                sub_channel="test_ingest", 
                message_id=row['message_id'],
                sender=row['sender'],
                recipients=recipients,
                subject=row['subject'],
                content=row['body'],
                timestamp=dt
            )
            messages_to_insert.append(comm)
            count += 1

    assert len(messages_to_insert) > 0, "No messages parsed from CSV"

    # Persist to DB
    session.add_all(messages_to_insert)
    await session.commit()

    # Verify Retrieval
    for msg in messages_to_insert:
        stmt = select(Communication).where(Communication.id == msg.id)
        result = await session.execute(stmt)
        retrieved = result.scalar_one_or_none()
        
        assert retrieved is not None
        assert retrieved.message_id == msg.message_id
        assert retrieved.sender == msg.sender
        assert retrieved.tenant_id == tenant_id
        # Verify array handling
        assert set(retrieved.recipients) == set(msg.recipients)

    print(f"\nSuccessfully verified ingestion of {len(messages_to_insert)} messages via Communication model.")
