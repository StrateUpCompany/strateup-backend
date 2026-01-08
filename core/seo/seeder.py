
import slugify
from backend.core.database import db

# Lists of targets
NICHES = [
    "Imobiliária", "Dentista", "Advogado", "Energia Solar", "Estética", 
    "Academia", "Pet Shop", "Contabilidade", "Marketing Digital", "E-commerce",
    "Pizzaria", "Concessionária", "Seguros", "Arquitetura", "Fotografia"
]

LOCATIONS = [
    "São Paulo", "Rio de Janeiro", "Belo Horizonte", "Curitiba", "Brasília", "Porto Alegre"
]

def seed_niches():
    print("🌱 Seeding Niche Pages...")
    count = 0
    for niche in NICHES:
        # Vector A: "Funnel for X"
        keyword = f"Funil de Vendas para {niche}"
        slug = slugify.slugify(keyword)
        
        data = {
            "slug": slug,
            "keyword": keyword,
            "category": "niche",
            "title": f"O Melhor Funil de Vendas para {niche} (Template Grátis)",
            "meta_description": f"Descubra como atrair mais clientes para sua {niche} usando automação e inteligência artificial. Copie este funil validado.",
            "status": "draft",
            "content": {"h1": keyword, "intro": "Generating..."}
        }
        
        try:
            # Upsert (ignore if exists)
            db.table("seo_pages").upsert(data, on_conflict="slug").execute()
            print(f"   + {slug}")
            count += 1
        except Exception as e:
            print(f"Error seeding {slug}: {e}")
            
    print(f"✅ Seeded {count} Niche Pages.")

def run():
    seed_niches()

if __name__ == "__main__":
    run()
