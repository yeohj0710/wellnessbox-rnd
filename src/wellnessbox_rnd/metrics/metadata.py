from wellnessbox_rnd.schemas.recommendation import EngineMetadata


def build_engine_metadata(mode: str = "mock_deterministic_v0") -> EngineMetadata:
    return EngineMetadata(mode=mode)
