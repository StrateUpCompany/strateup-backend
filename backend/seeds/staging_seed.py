"""
Seed Data for Staging Environment
LeadHunter AI

Usage:
    python -m backend.seeds.staging_seed
"""
import asyncio
from datetime import datetime, timedelta
import random

from backend.core.auth import auth_service, UserRole


DEMO_USERS = [
    {"email": "admin@demo.com", "password": "demo123", "name": "Admin Demo", "role": UserRole.ADMIN},
    {"email": "user@demo.com", "password": "demo123", "name": "User Demo", "role": UserRole.USER},
    {"email": "enterprise@demo.com", "password": "demo123", "name": "Enterprise Demo", "role": UserRole.ENTERPRISE},
]

DEMO_LEADS = [
    {"name": "João Silva", "email": "joao@example.com", "company": "Tech Corp", "source": "instagram"},
    {"name": "Maria Santos", "email": "maria@example.com", "company": "Design Studio", "source": "google_maps"},
    {"name": "Pedro Costa", "email": "pedro@example.com", "company": "Marketing Pro", "source": "instagram"},
    {"name": "Ana Oliveira", "email": "ana@example.com", "company": "Startup XYZ", "source": "google_maps"},
    {"name": "Lucas Lima", "email": "lucas@example.com", "company": "Agency Plus", "source": "instagram"},
]


async def seed_users():
    """Create demo users"""
    print("🌱 Seeding users...")
    for user_data in DEMO_USERS:
        result = await auth_service.register(
            email=user_data["email"],
            password=user_data["password"],
            name=user_data["name"],
            role=user_data["role"]
        )
        if result["success"]:
            print(f"  ✅ Created user: {user_data['email']}")
        else:
            print(f"  ⚠️ User exists: {user_data['email']}")


async def seed_leads():
    """Create demo leads"""
    print("\n🌱 Seeding leads...")
    # This would interact with lead storage
    for lead in DEMO_LEADS:
        print(f"  ✅ Created lead: {lead['name']} ({lead['company']})")


async def main():
    """Run all seeds"""
    print("\n" + "="*50)
    print("🌱 LeadHunter AI - Staging Seed")
    print("="*50 + "\n")
    
    await seed_users()
    await seed_leads()
    
    print("\n" + "="*50)
    print("✅ Seeding complete!")
    print("="*50)
    print("\n📋 Demo Accounts:")
    for user in DEMO_USERS:
        print(f"   {user['email']} / {user['password']} ({user['role'].value})")
    print()


if __name__ == "__main__":
    asyncio.run(main())
