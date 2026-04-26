from safety import contains_forbidden_language, contains_phi_request


def test_safety_helpers():
    assert contains_forbidden_language('Please prescribe medication now')
    assert contains_phi_request('What is your date of birth?')
    assert not contains_forbidden_language('Possible differential hypothesis, needs clarification')
