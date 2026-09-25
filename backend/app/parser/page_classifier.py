from app.parser.patterns import (
    COLLEGE_PATTERN,
    COURSE_PATTERN,
    SEAT_SECTION_PATTERNS,
    CATEGORY_CODE_PATTERN,
    STAGE_PATTERN,
    PAGE_HEADER_PATTERN
)


class PageClassifier:
    @staticmethod
    def classify(text: str) -> list[str]:
        types = set()
        lines = text.strip().split('\n')
        
        if not lines:
            return ['EMPTY']
            
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            if COLLEGE_PATTERN.match(line):
                types.add('COLLEGE_HEADER')
            elif COURSE_PATTERN.match(line):
                types.add('COURSE_HEADER')
            elif any(p.search(line) for p in SEAT_SECTION_PATTERNS.values()):
                types.add('SEAT_SECTION')
            elif PAGE_HEADER_PATTERN.search(line):
                types.add('PAGE_HEADER')
            elif line.startswith("Legend:"):
                types.add('LEGEND')
            elif STAGE_PATTERN.match(line.split()[0]):
                types.add('CUTOFF_DATA')
            else:
                # check if category header
                parts = line.split()
                if parts and all(CATEGORY_CODE_PATTERN.match(p) for p in parts):
                    types.add('CATEGORY_HEADER')
                    
        return list(types) if types else ['CONTINUATION']
