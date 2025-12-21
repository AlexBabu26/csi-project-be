"""
Seed script to populate Kalamela events from the official event list.
Run this script to delete existing events and add the 45 official events.
"""

import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')

async def seed_events():
    engine = create_async_engine(DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        print("Starting event seeding...")
        
        # Step 1: Delete existing data (in correct order due to foreign keys)
        print("Deleting existing participations...")
        await session.execute(text("DELETE FROM individual_event_participation"))
        await session.execute(text("DELETE FROM group_event_participation"))
        
        print("Deleting existing events...")
        await session.execute(text("DELETE FROM individual_event"))
        await session.execute(text("DELETE FROM group_event"))
        
        print("Deleting existing categories...")
        await session.execute(text("DELETE FROM event_category"))
        
        await session.commit()
        print("Existing data deleted.")
        
        # Step 2: Create event categories
        print("Creating event categories...")
        categories = [
            ("MUSIC", "Music events including solo, group performances, and instrumental"),
            ("FINE ARTS", "Fine arts events including drawing and painting"),
            ("STAGE EVENTS", "Stage performance events including drama and dance"),
            ("LITERARY EVENTS", "Literary events including poetry, essay, and extempore"),
        ]
        
        await session.execute(text("""
            INSERT INTO event_category (name, description) VALUES
            (:name1, :desc1),
            (:name2, :desc2),
            (:name3, :desc3),
            (:name4, :desc4)
        """), {
            "name1": categories[0][0], "desc1": categories[0][1],
            "name2": categories[1][0], "desc2": categories[1][1],
            "name3": categories[2][0], "desc3": categories[2][1],
            "name4": categories[3][0], "desc4": categories[3][1],
        })
        await session.commit()
        
        # Get category IDs
        result = await session.execute(text("SELECT id, name FROM event_category ORDER BY id"))
        category_map = {row[1]: row[0] for row in result.fetchall()}
        print(f"Categories created: {category_map}")
        
        # Step 3: Insert Individual Events (36 events)
        print("Creating individual events...")
        
        individual_events = [
            # MUSIC - Individual (18 events)
            ("Solo Eastern Jr Boys", category_map["MUSIC"], True),
            ("Solo Eastern Jr Girls", category_map["MUSIC"], True),
            ("Solo Eastern Sr Boys", category_map["MUSIC"], True),
            ("Solo Eastern Sr Girls", category_map["MUSIC"], True),
            ("Solo Western Jr Boys", category_map["MUSIC"], True),
            ("Solo Western Jr Girls", category_map["MUSIC"], True),
            ("Solo Western Sr Boys", category_map["MUSIC"], True),
            ("Solo Western Sr Girls", category_map["MUSIC"], True),
            ("Light music Boys", category_map["MUSIC"], True),
            ("Light music Girls", category_map["MUSIC"], True),
            ("Poetry Recitation", category_map["MUSIC"], False),
            ("Classical Music", category_map["MUSIC"], False),
            ("Karoke Song", category_map["MUSIC"], False),
            ("Organ Recital", category_map["MUSIC"], True),
            ("Instrumental Music Wind", category_map["MUSIC"], False),
            ("Instrumental Music String", category_map["MUSIC"], False),
            ("Instrumental Music Percussion", category_map["MUSIC"], False),
            ("Guitar", category_map["MUSIC"], False),
            
            # FINE ARTS - Individual (3 events)
            ("Pencil drawing", category_map["FINE ARTS"], True),
            ("Cartoon", category_map["FINE ARTS"], True),
            ("Water Colour", category_map["FINE ARTS"], True),
            
            # STAGE EVENTS - Individual (3 events)
            ("Fancy Dress", category_map["STAGE EVENTS"], True),
            ("Monoact", category_map["STAGE EVENTS"], True),
            ("Mimicry", category_map["STAGE EVENTS"], True),
            
            # LITERARY EVENTS - Individual (12 events)
            ("Poetry English", category_map["LITERARY EVENTS"], False),
            ("Poetry Malayalam", category_map["LITERARY EVENTS"], False),
            ("Short Story English", category_map["LITERARY EVENTS"], False),
            ("Short Story Malayalam", category_map["LITERARY EVENTS"], False),
            ("Essay Eng Jr", category_map["LITERARY EVENTS"], False),
            ("Essay Mal Jr", category_map["LITERARY EVENTS"], False),
            ("Essay Eng Sr", category_map["LITERARY EVENTS"], False),
            ("Essay Mal Sr", category_map["LITERARY EVENTS"], False),
            ("Extempore Mal Jr", category_map["LITERARY EVENTS"], True),
            ("Extempore Mal Sr", category_map["LITERARY EVENTS"], True),
            ("Extempore Eng Jr", category_map["LITERARY EVENTS"], True),
            ("Extempore Eng Sr", category_map["LITERARY EVENTS"], True),
        ]
        
        for name, cat_id, is_mandatory in individual_events:
            await session.execute(text("""
                INSERT INTO individual_event (name, category_id, is_mandatory, description, created_on)
                VALUES (:name, :cat_id, :is_mandatory, NULL, NOW())
            """), {"name": name, "cat_id": cat_id, "is_mandatory": is_mandatory})
        
        await session.commit()
        print(f"Created {len(individual_events)} individual events.")
        
        # Step 4: Insert Group Events (9 events)
        print("Creating group events...")
        
        # Format: (name, category_id, is_mandatory, min_limit, max_limit, per_unit_limit)
        group_events = [
            # MUSIC - Group (4 events)
            ("Fusion", category_map["MUSIC"], False, 3, 8, 1),
            ("Group Song", category_map["MUSIC"], True, 3, 8, 1),
            ("Quartet", category_map["MUSIC"], True, 4, 4, 1),
            ("Octect", category_map["MUSIC"], False, 8, 8, 1),
            
            # STAGE EVENTS - Group (5 events)
            ("Tableau", category_map["STAGE EVENTS"], False, 4, 8, 1),
            ("Mime", category_map["STAGE EVENTS"], False, 5, 8, 1),
            ("Kadhaprasangam", category_map["STAGE EVENTS"], False, 4, 8, 1),
            ("Skit", category_map["STAGE EVENTS"], False, 5, 10, 1),
            ("Margamkali", category_map["STAGE EVENTS"], False, 5, 9, 1),
        ]
        
        for name, cat_id, is_mandatory, min_limit, max_limit, per_unit in group_events:
            await session.execute(text("""
                INSERT INTO group_event (name, category_id, is_mandatory, min_allowed_limit, max_allowed_limit, per_unit_allowed_limit, description, created_on)
                VALUES (:name, :cat_id, :is_mandatory, :min_limit, :max_limit, :per_unit, NULL, NOW())
            """), {
                "name": name, 
                "cat_id": cat_id, 
                "is_mandatory": is_mandatory,
                "min_limit": min_limit,
                "max_limit": max_limit,
                "per_unit": per_unit
            })
        
        await session.commit()
        print(f"Created {len(group_events)} group events.")
        
        # Summary
        print("\n" + "="*50)
        print("SEEDING COMPLETE!")
        print("="*50)
        print(f"Categories: 4")
        print(f"Individual Events: {len(individual_events)}")
        print(f"Group Events: {len(group_events)}")
        print(f"Total Events: {len(individual_events) + len(group_events)}")
        print("="*50)
        
        # Print summary by category
        result = await session.execute(text("""
            SELECT ec.name, 
                   (SELECT COUNT(*) FROM individual_event ie WHERE ie.category_id = ec.id) as ind_count,
                   (SELECT COUNT(*) FROM group_event ge WHERE ge.category_id = ec.id) as grp_count
            FROM event_category ec
            ORDER BY ec.id
        """))
        
        print("\nEvents by Category:")
        for row in result.fetchall():
            print(f"  {row[0]}: {row[1]} individual, {row[2]} group")


if __name__ == "__main__":
    asyncio.run(seed_events())

