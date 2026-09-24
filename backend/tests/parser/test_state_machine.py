import pytest
from app.parser.state_machine import ParserState

def test_initial_state():
    state = ParserState()
    assert state.current_college_code is None
    assert state.current_course_code is None
    assert state.current_categories == []

def test_set_college_resets_downstream():
    state = ParserState()
    state.set_college("01002", "College A")
    state.set_course("0100219110", "Course A")
    
    state.set_college("12345", "College B")
    assert state.current_college_code == "12345"
    assert state.current_course_code is None

def test_set_course_resets_downstream():
    state = ParserState()
    state.set_course("0100219110", "Course A")
    state.set_section("STATE_LEVEL", "Raw")
    state.set_categories(["GOPENS"])
    
    state.set_course("1234567890", "Course B")
    assert state.current_course_code == "1234567890"
    assert state.current_seat_section is None
    assert state.current_categories == []

def test_is_valid_for_cutoff():
    state = ParserState()
    assert not state.is_valid_for_cutoff()
    
    state.set_college("01002", "College A")
    state.set_course("0100219110", "Course A")
    state.set_section("STATE_LEVEL", "Raw")
    state.set_categories(["GOPENS"])
    
    assert state.is_valid_for_cutoff()

def test_to_context_dict():
    state = ParserState()
    state.set_college("01002", "College A")
    d = state.to_context_dict()
    assert d["college_code"] == "01002"
    assert d["college_name"] == "College A"
