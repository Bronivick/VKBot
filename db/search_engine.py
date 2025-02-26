# db/async_search_engine.py
import torch
from db.models.models import Photo
from logger import logger
from sqlalchemy.future import select

def compute_distance(emb1, emb2):
    emb1_tensor = torch.tensor(emb1)
    emb2_tensor = torch.tensor(emb2)
    distance = torch.norm(emb1_tensor - emb2_tensor).item()
    logger.debug(f"Computed distance: {distance}")
    return distance

async def search_face(input_embedding, session):
    input_emb_list = input_embedding[0].tolist()
    matches = []
    result = await session.execute(select(Photo))
    photos = result.scalars().all()
    for photo in photos:
        stored_emb = photo.embedding
        distance = compute_distance(input_emb_list, stored_emb)
        if distance < 0.9:  # порог, возможно, подберется экспериментально
            matches.append((photo, distance))
    return sorted(matches, key=lambda x: x[1])
