"""
Crea el primer usuario en la base de datos.

Uso:
    python create_user.py --username tu_usuario --password tu_clave_segura

"""
import argparse
import sys
import os

# Ensure app package can be imported
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from app.db.database import SessionLocal, engine
from app.models import vinyl, user as user_model  # Ensure tables are created
from app.db.database import Base
from app.crud.crud_user import get_user_by_username, create_user

def main():
    parser = argparse.ArgumentParser(description="Crear usuario para Music Place Dashboard")
    parser.add_argument("--username", required=True, help="Nombre de usuario")
    parser.add_argument("--password", required=True, help="Contraseña")
    args = parser.parse_args()

    # Auto-create tables if missing
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        existing = get_user_by_username(db, args.username)
        if existing:
            print(f"❌ El usuario '{args.username}' ya existe en la base de datos.")
            sys.exit(1)

        new_user = create_user(db, args.username, args.password)
        print(f"✅ Usuario '{new_user.username}' creado exitosamente.")
        print(f"   ID: {new_user.id}")
    finally:
        db.close()

if __name__ == "__main__":
    main()
