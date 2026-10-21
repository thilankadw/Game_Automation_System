"""ROI set and ROI request and response schemas."""

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.roi import RoiName


class RoiBase(BaseModel):
    """Fields shared by ROI schemas."""

    name: RoiName
    x: int = Field(ge=0)
    y: int = Field(ge=0)
    width: int = Field(gt=0)
    height: int = Field(gt=0)


class RoiCreate(RoiBase):
    """Payload for creating a ROI."""


class RoiRead(RoiBase):
    """ROI returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int


class RoiSetCreate(BaseModel):
    """Payload for creating a ROI set.

    The name is optional so the API can generate ``Option 1``, ``Option 2``,
    and so on when the user does not provide one.
    """

    name: str | None = Field(default=None, min_length=1, max_length=255)
    rois: list[RoiCreate] = Field(default_factory=list)

    @field_validator("rois")
    @classmethod
    def _unique_roi_names(cls, rois: list[RoiCreate]) -> list[RoiCreate]:
        """Reject duplicate ROI names within a single set."""
        names = [roi.name for roi in rois]
        if len(names) != len(set(names)):
            raise ValueError("ROI names must be unique within a set")
        return rois


class RoiSetUpdate(BaseModel):
    """Payload for updating a ROI set. Omitted fields are left unchanged."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    rois: list[RoiCreate] | None = None

    @field_validator("rois")
    @classmethod
    def _unique_roi_names(
        cls, rois: list[RoiCreate] | None
    ) -> list[RoiCreate] | None:
        """Reject duplicate ROI names within a single set."""
        if rois is None:
            return None
        names = [roi.name for roi in rois]
        if len(names) != len(set(names)):
            raise ValueError("ROI names must be unique within a set")
        return rois


class RoiSetRead(BaseModel):
    """ROI set returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    game_provider_id: int
    rois: list[RoiRead]
