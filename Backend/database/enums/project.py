from enum import Enum


class InformationGatheringConversationStatus(str, Enum):
    """Status enum for information gathering agent conversations."""
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
