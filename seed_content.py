"""Add clearly labelled free self-study guides and resources, not fictitious events."""
from app import SessionLocal, Item, GUIDES
with SessionLocal() as db:
    added=0
    for kind,title,category,location,description in GUIDES:
        if not db.query(Item).filter_by(kind=kind,title=title).first():
            db.add(Item(kind=kind,title=title,category=category,location=location,subtitle='Free self-study guide · not a live class',description=description,price=0,published=True));added+=1
    db.commit()
print(f'Added {added} guides. Existing entries preserved.')
