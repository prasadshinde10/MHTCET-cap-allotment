from app.parser.patterns import COURSE_PATTERN


class CourseParser:
    @staticmethod
    def parse_line(line: str) -> tuple[str, str] | None:
        """
        Extracts course code and name from a line.
        Returns (code, name) or None if no match.
        """
        match = COURSE_PATTERN.match(line.strip())
        if match:
            code = match.group(1).strip()
            name = match.group(2).strip()
            return code, name
        return None
