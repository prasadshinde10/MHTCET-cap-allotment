from dataclasses import dataclass, field
from typing import Any


@dataclass
class ParserState:
    current_college_code: str | None = None
    current_college_name: str | None = None
    current_course_code: str | None = None
    current_course_name: str | None = None
    current_seat_section: str | None = None
    current_seat_section_raw: str | None = None
    current_categories: list[str] = field(default_factory=list)
    current_stage: str | None = None
    page_number: int = 0
    colleges_found: set[str] = field(default_factory=set)
    courses_found: set[str] = field(default_factory=set)

    def reset_for_new_college(self) -> None:
        self.current_course_code = None
        self.current_course_name = None
        self.reset_for_new_course()

    def reset_for_new_course(self) -> None:
        self.current_seat_section = None
        self.current_seat_section_raw = None
        self.reset_for_new_section()

    def reset_for_new_section(self) -> None:
        self.current_categories = []
        self.reset_for_new_categories()

    def reset_for_new_categories(self) -> None:
        self.current_stage = None

    def set_college(self, code: str, name: str) -> None:
        self.current_college_code = code
        self.current_college_name = name
        self.colleges_found.add(code)
        self.reset_for_new_college()

    def set_course(self, code: str, name: str) -> None:
        self.current_course_code = code
        self.current_course_name = name
        self.courses_found.add(code)
        self.reset_for_new_course()

    def set_section(self, normalized: str, raw: str) -> None:
        self.current_seat_section = normalized
        self.current_seat_section_raw = raw
        self.reset_for_new_section()

    def set_categories(self, categories: list[str]) -> None:
        self.current_categories = categories
        self.reset_for_new_categories()

    def set_stage(self, stage: str) -> None:
        self.current_stage = stage

    def is_valid_for_cutoff(self) -> bool:
        return bool(
            self.current_college_code
            and self.current_course_code
            and self.current_seat_section
            and self.current_categories
        )

    def to_context_dict(self) -> dict[str, Any]:
        return {
            "college_code": self.current_college_code,
            "college_name": self.current_college_name,
            "course_code": self.current_course_code,
            "course_name": self.current_course_name,
            "seat_section": self.current_seat_section,
            "categories": self.current_categories,
            "stage": self.current_stage,
            "page_number": self.page_number,
        }
