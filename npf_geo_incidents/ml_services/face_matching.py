import math
from PIL import Image

def extract_face_vector(image_file) -> list:
    """
    Extracts a 64-dimensional feature vector from an uploaded image.
    Uses PIL to resize the image to 8x8 pixels and convert it to grayscale,
    then normalizes the resulting feature vector to unit length.
    """
    try:
        # Open and load image using Pillow
        with Image.open(image_file) as img:
            # Grayscale & resize to 8x8 grid
            img_resized = img.convert('L').resize((8, 8))
            pixels = list(img_resized.getdata())
            
            # Normalize vector to unit length (for fast cosine similarity dot product)
            vec = [float(p) for p in pixels]
            magnitude = math.sqrt(sum(v*v for v in vec))
            if magnitude > 0:
                vec = [v / magnitude for v in vec]
            return vec
    except Exception:
        # Fallback: return a zeroed or mock vector if image read fails
        return [0.0] * 64

def calculate_face_similarity(vec1: list, vec2: list) -> float:
    """
    Calculates cosine similarity percentage between two feature vectors.
    Returns a score between 0.0 and 100.0.
    """
    if len(vec1) != len(vec2) or len(vec1) == 0:
        return 0.0
    
    mag1 = math.sqrt(sum(v*v for v in vec1))
    mag2 = math.sqrt(sum(v*v for v in vec2))
    
    if mag1 == 0 or mag2 == 0:
        return 0.0
        
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    cosine = dot_product / (mag1 * mag2)
    cosine = max(-1.0, min(1.0, cosine))
    
    # Scale from [-1, 1] range to [0, 100]% similarity score
    score = (cosine + 1.0) / 2.0 * 100.0
    return round(score, 2)
