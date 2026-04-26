import pytest
from schemas import WorkerOutput


def test_worker_output_validation_rejects_forbidden_language():
    bad = {
        'suggestions': [],
        'differentials': [],
        'summary': 'This is definitely myocardial infarction.',
        'safety_note': 'Clinical decision support only. Doctor remains responsible for judgment.'
    }
    with pytest.raises(Exception):
        WorkerOutput.model_validate(bad)
