"""Tests for provenance field model."""

from datetime import datetime, timezone

from backend.schema.provenance import FieldSource, ProvenanceField


class TestFieldSource:
    def test_enum_values(self) -> None:
        assert FieldSource.USER == "user"
        assert FieldSource.PROVIDED == "provided"
        assert FieldSource.INFERRED == "inferred"
        assert FieldSource.DEFAULT == "default"

    def test_enum_membership(self) -> None:
        assert len(FieldSource) == 4


class TestProvenanceField:
    def test_minimal_construction(self) -> None:
        pf = ProvenanceField(value=42)
        assert pf.value == 42
        assert pf.confidence == 1.0
        assert pf.source == FieldSource.USER
        assert pf.note is None
        assert isinstance(pf.timestamp, datetime)

    def test_full_construction(self) -> None:
        ts = datetime(2026, 1, 15, tzinfo=timezone.utc)
        pf = ProvenanceField(
            value="hello",
            confidence=0.8,
            source=FieldSource.INFERRED,
            timestamp=ts,
            note="AI guess",
        )
        assert pf.value == "hello"
        assert pf.confidence == 0.8
        assert pf.source == FieldSource.INFERRED
        assert pf.timestamp == ts
        assert pf.note == "AI guess"

    def test_confidence_bounds(self) -> None:
        ProvenanceField(value=1, confidence=0.0)
        ProvenanceField(value=1, confidence=1.0)

        import pytest

        with pytest.raises(Exception):
            ProvenanceField(value=1, confidence=-0.1)
        with pytest.raises(Exception):
            ProvenanceField(value=1, confidence=1.1)

    def test_value_types(self) -> None:
        assert ProvenanceField(value=3.14).value == 3.14
        assert ProvenanceField(value="text").value == "text"
        assert ProvenanceField(value=None).value is None
        assert ProvenanceField(value={"a": 1}).value == {"a": 1}
        assert ProvenanceField(value=[1, 2, 3]).value == [1, 2, 3]

    def test_serialization_roundtrip(self) -> None:
        pf = ProvenanceField(
            value=100, confidence=0.9, source=FieldSource.PROVIDED
        )
        data = pf.model_dump(mode="json")
        restored = ProvenanceField.model_validate(data)
        assert restored.value == pf.value
        assert restored.confidence == pf.confidence
        assert restored.source == pf.source

    def test_default_timestamp_is_utc(self) -> None:
        pf = ProvenanceField(value=0)
        assert pf.timestamp.tzinfo is not None
