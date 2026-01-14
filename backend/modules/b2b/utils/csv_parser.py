"""
CSV Parser for Bulk User Invitations

Handles parsing and validation of CSV files for bulk user invites.
"""

import csv
import io
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, EmailStr, field_validator
from fastapi import UploadFile, HTTPException
import logging

logger = logging.getLogger(__name__)


class BulkInviteRow(BaseModel):
    """Single row from bulk invite CSV"""
    row_number: int
    email: EmailStr
    role: Optional[str] = None
    team_name: str
    team_role: str
    name: Optional[str] = None
    
    @field_validator('role')
    @classmethod
    def validate_role(cls, v: Optional[str]) -> Optional[str]:
        """Validate role format"""
        if v is None or v.strip() == '':
            return None
        # We allow dynamic custom roles (e.g. surveillance_chief), 
        # so we just normalize to lowercase
        return v.lower().strip()
    
    @field_validator('team_role')
    @classmethod
    def validate_team_role(cls, v: str) -> str:
        """Validate team role if provided"""
        if v is None or v.strip() == '':
            raise ValueError('Team role is required')
        # We allow dynamic custom team roles (e.g. surveillance_lead),
        # so we just normalize to lowercase
        return v.lower().strip()
        # so we just normalize to lowercase
        return v.lower().strip()
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        """Validate and trim name"""
        if v is None or v.strip() == '':
            return None
        v_stripped = v.strip()
        if len(v_stripped) > 255:
            raise ValueError(f"Name too long (max 255 characters)")
        return v_stripped


class ValidationError(BaseModel):
    """CSV validation error"""
    row: int
    field: str
    message: str
    value: Optional[str] = None


class ParsedCSV(BaseModel):
    """Result of CSV parsing"""
    rows: List[BulkInviteRow]
    errors: List[ValidationError]
    total_rows: int
    
    @property
    def is_valid(self) -> bool:
        """Check if CSV has no errors"""
        return len(self.errors) == 0


class BulkInviteCSVParser:
    """Parser for bulk invitation CSV files"""
    
    REQUIRED_COLUMNS = ['email', 'team_name', 'team_role']
    OPTIONAL_COLUMNS = ['role', 'name']
    ALL_COLUMNS = REQUIRED_COLUMNS + OPTIONAL_COLUMNS
    
    MAX_FILE_SIZE = 2 * 1024 * 1024  # 2MB
    MAX_ROWS = 100
    
    async def parse_file(self, file: UploadFile) -> ParsedCSV:
        """
        Parse and validate CSV file.
        
        Args:
            file: Uploaded CSV file
            
        Returns:
            ParsedCSV with rows and any validation errors
            
        Raises:
            HTTPException: For file-level errors (too large, invalid format, etc.)
        """
        # Check file size
        contents = await file.read()
        if len(contents) > self.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size is {self.MAX_FILE_SIZE / (1024*1024)}MB"
            )
        
        # Reset file pointer
        await file.seek(0)
        
        # Decode contents
        try:
            text_content = contents.decode('utf-8')
        except UnicodeDecodeError:
            raise HTTPException(
                status_code=400,
                detail="Invalid file encoding. Please use UTF-8 encoding."
            )
        
        # Parse CSV
        try:
            csv_reader = csv.DictReader(io.StringIO(text_content))
            
            # Validate headers
            if not csv_reader.fieldnames:
                raise HTTPException(
                    status_code=400,
                    detail="CSV file is empty or has no headers"
                )
            
            # Normalize headers (lowercase, strip whitespace)
            headers = [h.lower().strip() for h in csv_reader.fieldnames]
            
            # Check required columns
            missing_columns = set(self.REQUIRED_COLUMNS) - set(headers)
            if missing_columns:
                raise HTTPException(
                    status_code=400,
                    detail=f"Missing required columns: {', '.join(missing_columns)}"
                )
            
            # Parse rows
            rows: List[BulkInviteRow] = []
            errors: List[ValidationError] = []
            seen_emails: Dict[str, int] = {}  # email -> row number
            
            for row_num, row_data in enumerate(csv_reader, start=2):  # Start at 2 (1 is header)
                # Normalize keys
                row_normalized = {k.lower().strip(): v.strip() if v else '' 
                                 for k, v in row_data.items()}
                
                # Skip empty rows
                if all(v == '' for v in row_normalized.values()):
                    continue
                
                # Check row count
                if len(rows) >= self.MAX_ROWS:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Too many rows. Maximum is {self.MAX_ROWS} users per upload"
                    )
                
                # Extract fields
                email = row_normalized.get('email', '').strip()
                role = row_normalized.get('role', '').strip() or None
                team_name = row_normalized.get('team_name', '').strip()
                team_role = row_normalized.get('team_role', '').strip()
                name = row_normalized.get('name', '').strip() or None
                
                # Check for duplicate emails in file
                if email:
                    email_lower = email.lower()
                    if email_lower in seen_emails:
                        errors.append(ValidationError(
                            row=row_num,
                            field='email',
                            message=f"Duplicate email in file (also appears on row {seen_emails[email_lower]})",
                            value=email
                        ))
                        continue
                    seen_emails[email_lower] = row_num
                
                # Validate row
                try:
                    parsed_row = BulkInviteRow(
                        row_number=row_num,
                        email=email,
                        role=role,
                        team_name=team_name,
                        team_role=team_role,
                        name=name
                    )
                    rows.append(parsed_row)
                    
                except Exception as e:
                    # Extract field and message from validation error
                    error_msg = str(e)
                    field = 'unknown'
                    
                    # Parse Pydantic validation error
                    if 'email' in error_msg.lower():
                        field = 'email'
                    elif 'role' in error_msg.lower():
                        field = 'role'
                    elif 'team_name' in error_msg.lower():
                        field = 'team_name'
                    elif 'team_role' in error_msg.lower():
                        field = 'team_role'
                    elif 'name' in error_msg.lower():
                        field = 'name'
                    
                    errors.append(ValidationError(
                        row=row_num,
                        field=field,
                        message=error_msg,
                        value=row_normalized.get(field, '')
                    ))
            
            if not rows and not errors:
                raise HTTPException(
                    status_code=400,
                    detail="CSV file contains no data rows"
                )
            
            return ParsedCSV(
                rows=rows,
                errors=errors,
                total_rows=len(rows) + len(errors)
            )
            
        except csv.Error as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid CSV format: {str(e)}"
            )
    
    async def validate_business_rules(
        self,
        rows: List[BulkInviteRow],
        current_user: dict,
        db,
        tenant_domain: str
    ) -> List[ValidationError]:
        """
        Validate business rules for bulk invite rows.
        
        Args:
            rows: Parsed CSV rows
            current_user: Current user dict
            db: Database session
            tenant_domain: Tenant's email domain
            
        Returns:
            List of validation errors
        """
        from sqlalchemy import select
        from modules.b2b.models import UserModel, InvitationModel
        
        errors: List[ValidationError] = []
        current_user_role = current_user.get('role', '').lower()
        
        for row in rows:
            # Check email domain matches tenant
            email_domain = row.email.split('@')[1].lower()
            if email_domain != tenant_domain.lower():
                errors.append(ValidationError(
                    row=row.row_number,
                    field='email',
                    message=f"Email domain must match tenant domain ({tenant_domain})",
                    value=row.email
                ))
                continue
            
            # Check role hierarchy (admin cannot invite owner)
            if current_user_role == 'admin' and row.role == 'owner':
                errors.append(ValidationError(
                    row=row.row_number,
                    field='role',
                    message="Admins cannot invite users with 'owner' role",
                    value=row.role
                ))
                continue
            
            # Check if user already exists
            result = await db.execute(
                select(UserModel).where(
                    UserModel.email == row.email,
                    UserModel.tenant_id == current_user['tenant_id']
                )
            )
            existing_user = result.scalar_one_or_none()
            if existing_user:
                errors.append(ValidationError(
                    row=row.row_number,
                    field='email',
                    message="User already exists in tenant",
                    value=row.email
                ))
                continue
            
            # Check if invitation already exists (pending = not yet accepted)
            result = await db.execute(
                select(InvitationModel).where(
                    InvitationModel.email == row.email,
                    InvitationModel.tenant_id == current_user['tenant_id'],
                    InvitationModel.accepted_at.is_(None)  # Pending = not accepted
                )
            )
            existing_invitation = result.scalar_one_or_none()
            if existing_invitation:
                errors.append(ValidationError(
                    row=row.row_number,
                    field='email',
                    message="Pending invitation already exists for this email",
                    value=row.email
                ))
                continue
        
        return errors
