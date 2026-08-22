import math
from dataclasses import dataclass
from typing import List, Optional

from .types import SpeakerFeatures

@dataclass
class SpeakerModelConfig:
    embedding_dim: int = 128
    similarity_threshold: float = 0.70

class SpeakerExtractor:
    def __init__(self, config: Optional[SpeakerModelConfig] = None):
        self.config = config or SpeakerModelConfig()
        self.reference_embedding = [0.1] * self.config.embedding_dim

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        dot_prod = sum(a * b for a, b in zip(vec1, vec2))
        norm1_ = math.sqrt(sum(a * a for a in vec1))
        norm2_ = math.sqrt(sum(b * b for b in vec2))
        if norm1_ == 0 or norm2_ == 0:
            return 0.0
        return dot_prod / (norm1_ * norm2_)

    def extract(self, frame: List[float]) -> SpeakerFeatures:
        candidate_embedding = [0.09] * self.config.embedding_dim
        similarity = self._cosine_similarity(candidate_embedding, self.reference_embedding)
        confidence = 0.85 if similarity >= self.config.similarity_threshold else 0.40

        return SpeakerFeatures(
            speaker_embedding=candidate_embedding,
            speix_id="david",
            similarity_score=round(similarity, 2),
            embedding_confidence=confidence
        )

if __name__ == "__main__":
    extractor = SpeakerExtractor()
    features = extractor.extract([0.0] * 160)
    print(f"[Speaker Extractor] ID: {features.speix_id} | Similarity: {features.similarity_score} | Confidence: {features.embedding_confidence}")
