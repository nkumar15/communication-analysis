# """
# Seed Domain Permissions

# Adds domain resource permissions (projects, tasks, comments) to member and viewer roles.
# These permissions work alongside team role capabilities for fine-grained access control.

# Run with: python -m services.domains.projects.seed_permissions
# """
# import asyncio
# import sys
# import os

# # Add backend to path
# sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

# from sqlalchemy import text
# from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession


# async def seed_domain_permissions():
#     """Add domain permissions to member and viewer role templates"""
    
#     database_url = os.getenv('DATABASE_URL', 'postgresql+asyncpg://postgres:postgres@localhost:5432/sso_db')
    
#     engine = create_async_engine(database_url.replace('postgresql://', 'postgresql+asyncpg://'))
    
#     async with AsyncSession(engine) as session:
#         # Add projects, tasks, comments permissions to member role
#         await session.execute(text("""
#             UPDATE b2b.role_templates
#             SET permissions = permissions || '[
#                 {"resource": "projects", "actions": ["read", "write"]},
#                 {"resource": "tasks", "actions": ["read", "write"]},
#                 {"resource": "comments", "actions": ["read", "write"]}
#             ]'::jsonb
#             WHERE name = 'member'
#             AND NOT (permissions::text LIKE '%projects%')
#         """))
        
#         # Add read-only domain permissions to viewer role
#         await session.execute(text("""
#             UPDATE b2b.role_templates
#             SET permissions = permissions || '[
#                 {"resource": "projects", "actions": ["read"]},
#                 {"resource": "tasks", "actions": ["read"]},
#                 {"resource": "comments", "actions": ["read"]}
#             ]'::jsonb
#             WHERE name = 'viewer'
#             AND NOT (permissions::text LIKE '%projects%')
#         """))
        
#         await session.commit()
        
#         # Verify
#         result = await session.execute(text("""
#             SELECT name, permissions::text LIKE '%projects%' as has_projects
#             FROM b2b.role_templates
#             WHERE name IN ('member', 'viewer')
#         """))
        
#         for row in result:
#             status = "✅" if row.has_projects else "❌"
#             print(f"{status} {row.name}: projects permission = {row.has_projects}")
    
#     await engine.dispose()
#     print("\n✅ Domain permissions seeded successfully")


# if __name__ == '__main__':
#     asyncio.run(seed_domain_permissions())
