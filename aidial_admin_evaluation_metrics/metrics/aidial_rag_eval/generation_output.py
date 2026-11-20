"""Output types and helper functions for RAG evaluation generation metrics."""

import json
from typing import Annotated, Literal, TypeVar, cast

import pandas as pd
from pydantic import BaseModel, Field, JsonValue, field_validator

from aidial_admin_evaluation_metrics.metrics.common.types import (
    MetricError,
    MetricOutputField,
)


class InferenceHighlightItem(BaseModel):
    """A segment of the highlighted text with its inference score."""

    text: str = Field(description="Text of the segment.")
    score: float = Field(
        description="Highlight score of the segment: inference - 1 (0 means entailed, negative values mean not entailed). Delimiters have score 0.",
    )
    title: str | None = Field(
        default=None,
        description="Text to display on hover over the segment when the highlight is rendered (the inference score of the segment). Not set for delimiters between segments.",
    )

    @field_validator("title", mode="before")
    @classmethod
    def _title_to_str(cls, value):
        # The library returns the inference score as a number.
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return str(value)
        return value


class InferenceHighlight(BaseModel):
    """Highlighted text showing which segments affected the inference score."""

    corpus: list[InferenceHighlightItem] = Field(
        default=[],
        description="Consecutive segments (and delimiters) of the highlighted text.",
    )


class InferenceDetails(BaseModel):
    """Details about NLI-based inference calculation."""

    json_explanation: Annotated[
        JsonValue,
        Field(
            description="Low level details of the inference calculation as a JSON value. Exact format is an implementation detail of the inference calculation and should not be relied on for any downstream use.",
        ),
    ] = None
    highlight: Annotated[
        InferenceHighlight,
        Field(
            description="Highlighted text showing which segments of the text affected the inference score.",
        ),
    ] = InferenceHighlight()


class InferenceField(MetricOutputField):
    """Metric output field for NLI-based inference score, including details about the inference calculation."""

    details: Annotated[
        InferenceDetails,
        Field(
            description="Details about the inference calculation containing JSON explanation and highlights",
        ),
    ] = InferenceDetails()


GroundTruthToAnswerField = Annotated[
    InferenceField | MetricError,
    Field(
        discriminator="type",
        description="Inference score (0-1) measuring if answer is entailed from ground truth. Score lower than 1 indicates that the answer has some statements that are not supported by the ground truth: statements that contradict the ground truth or extra statements that are not mentioned in the ground truth.",
    ),
]

AnswerToGroundTruthField = Annotated[
    InferenceField | MetricError,
    Field(
        discriminator="type",
        description="Inference score (0-1) measuring if ground truth is entailed from answer. Score lower than 1 indicates that the ground truth has some statements that are not supported by the answer: statements that contradict the answer or statements that are missing in the answer.",
    ),
]

ContextToAnswerField = Annotated[
    InferenceField | MetricError,
    Field(
        discriminator="type",
        description="Inference score (0-1) measuring if answer is entailed by context. Score lower than 1 indicates that the answer has some statements that are not supported by the context: statements that contradict the context or extra statements that are not mentioned in the context (which may or may not be correct, but are not supported by the context).",
    ),
]


def extract_generation_metric(
    row: pd.Series,
    prefix: Literal["gt_ans", "ans_gt", "ctx_ans"],
) -> InferenceField:
    """Utility to extract an InferenceField from a DataFrame row using the specified prefix."""
    return InferenceField(
        value=float(row[f"{prefix}_inference"]),
        details=InferenceDetails(
            json_explanation=json.loads(cast(str, row[f"{prefix}_json"])),
            highlight=InferenceHighlight.model_validate_json(
                cast(str, row[f"{prefix}_highlight"])
            ),
        ),
    )


T = TypeVar("T", bound=BaseModel)


def output_error(e: Exception, outputType: type[T]) -> T:
    """Utility to report an exception as error for all output fields"""
    error = MetricError(message=str(e))

    return outputType.model_validate(
        {
            field_name: error.model_dump()
            for field_name, _ in outputType.model_fields.items()
        }
    )


def extract_row(
    result_df: pd.DataFrame,
) -> pd.Series:
    """Utility to extract a single row from the result DataFrame, ensuring it has exactly one row."""
    if result_df.shape[0] != 1:
        raise ValueError(
            f"Expected result DataFrame to have a single row, but got {result_df.shape[0]} rows."
        )
    return result_df.iloc[0]
