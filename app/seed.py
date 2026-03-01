import json
import os
from dateutil import parser
from app.db.database import SessionLocal, Base, engine
from app.models.vinyl import Vinyl

def seed_db():
    # Make sure tables exist
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        if db.query(Vinyl).count() == 0:
            print("Database is empty. Seeding from JSON...")
            import sys
            
            # Usar la ruta absoluta del archivo JSON de datos
            json_path = '/Users/Desarrollos/Web/Angular/music-place-dashboard/vinyls-data.json'
            
            if not os.path.exists(json_path):
                print(f"File not found: {json_path}")
                return
                
            with open(json_path, 'r', encoding='utf-8') as f:
                vinyls_data = json.load(f)
                
                for v in vinyls_data:
                    # Parse ISO strings to datetime objects
                    if 'addedAt' in v:
                        v['addedAt'] = parser.parse(v['addedAt']).replace(tzinfo=None)
                    
                    db_vinyl = Vinyl(**v)
                    db.add(db_vinyl)
                    
                db.commit()
                print(f"Successfully seeded {len(vinyls_data)} vinyls!")
        else:
            print("Database already contains data. Seeding skipped.")
    except Exception as e:
        print(f"Error seeding database: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_db()
