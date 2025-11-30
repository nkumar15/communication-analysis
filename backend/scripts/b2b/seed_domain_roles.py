import asyncio
import sys
import os

# Add backend directory to python path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../'))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from core.database import engine
from services.b2b.models.role_template import RoleTemplate

# Domain Specific Roles (Business Logic)
DOMAIN_ROLES = [
    {
        "name": "field_manager",
        "display_name": "Field Manager",
        "description": "Manages field agents and oversees farmer onboarding",
        "is_system_role": True,
        "is_default": True,
        "permissions": [
            {"resource": "dashboard", "actions": ["read"]},
            {"resource": "users", "actions": ["read", "invite"]}, # Can invite agents
            {"resource": "roles", "actions": ["read", "write"]},
            {"resource": "farmers", "actions": ["read", "write", "delete"]},
        ]
    },
    {
        "name": "field_agent",
        "display_name": "Field Agent",
        "description": "Field executive responsible for farmer onboarding",
        "is_system_role": True,
        "is_default": True,
        "permissions": [
            {"resource": "farmers", "actions": ["read", "write"]},
        ]
    }
]

async def seed_domain_roles():
    """
    Seeds domain-specific role templates into the database.
    """
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        print("Seeding domain roles...")
        
        for role_def in DOMAIN_ROLES:
            # Check if role exists
            result = await session.execute(
                select(RoleTemplate).where(RoleTemplate.name == role_def["name"])
            )
            existing_role = result.scalar_one_or_none()
            
            if existing_role:
                print(f"Updating role: {role_def['name']}")
                existing_role.display_name = role_def["display_name"]
                existing_role.description = role_def["description"]
                existing_role.permissions = role_def["permissions"]
                existing_role.is_default = role_def["is_default"]
            else:
                print(f"Creating role: {role_def['name']}")
                new_role = RoleTemplate(
                    name=role_def["name"],
                    display_name=role_def["display_name"],
                    description=role_def["description"],
                    is_system_role=role_def["is_system_role"],
                    permissions=role_def["permissions"],
                    is_default=role_def["is_default"]
                )
                session.add(new_role)
        
        await session.commit()
        print("Domain roles seeded successfully.")

if __name__ == "__main__":
    asyncio.run(seed_domain_roles())
