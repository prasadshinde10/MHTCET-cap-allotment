"""
Cutoff record parser for MHT-CET CAP cutoff PDFs.

CRITICAL: The actual PDF uses a VERTICAL layout, not horizontal.

The structure within a section (after categories are listed) is:

  [Stage line]          e.g. "  I"
  [merit_1]             e.g. "34692"
  [(percentile_1)]      e.g. "(91.7858261)"
  [merit_2]             e.g. "59898"
  [(percentile_2)]      e.g. "(85.6921506)"
  ...
  "Stage"               (end marker)

The merit/percentile pairs are listed vertically IN ORDER of the
category codes listed above. So merit_1/(percentile_1) corresponds
to categories[0], merit_2/(percentile_2) to categories[1], etc.

Multi-stage example (from page 201):
  I
  200707
  (34.7115718)
  220146
  (17.7299217)
  ...
  II
  210732
  (27.2101033)
  Stage

Here Stage II only has ONE value (for the first category that has
Stage II data), but Stage I has values for all categories.
"""
from dataclasses import dataclass, field
from decimal import Decimal
from app.parser.patterns import (
    STAGE_PATTERN,
    MERIT_NUMBER_PATTERN,
    PERCENTILE_PATTERN,
    STAGE_LABEL_PATTERN,
)


@dataclass
class CutoffRecord:
    """A single parsed cutoff record."""
    category_code: str
    stage: str
    merit_number: int | None
    percentile: Decimal | None


@dataclass
class CutoffBlockParser:
    """
    Parses a vertical block of cutoff data.

    The parser operates as a state machine over lines:
    1. Detect stage line (e.g., "  I")
    2. Consume alternating merit/percentile lines
    3. Map each pair to the next category in order
    4. When a new stage is detected, reset category index
    5. When "Stage" label is detected, the block is complete
    """
    categories: list[str] = field(default_factory=list)
    records: list[CutoffRecord] = field(default_factory=list)

    _current_stage: str | None = None
    _category_index: int = 0
    _pending_merit: int | None = None
    _expecting_percentile: bool = False

    def feed_line(self, line: str) -> bool:
        """
        Feed a line to the parser.
        Returns True if the block is complete (Stage label found).
        Returns False to continue feeding lines.
        """
        stripped = line.strip()

        # Check for the "Stage" end marker
        if STAGE_LABEL_PATTERN.match(line):
            # Flush any pending merit without percentile
            self._flush_pending()
            return True  # Block complete

        # Check for a new stage (Roman numeral with leading whitespace)
        stage_match = STAGE_PATTERN.match(line)
        if stage_match:
            # Flush pending data from previous stage
            self._flush_pending()
            self._current_stage = stage_match.group(1).strip()
            self._category_index = 0
            self._pending_merit = None
            self._expecting_percentile = False
            return False

        if not self._current_stage:
            # Haven't seen a stage yet — skip
            return False

        # Check for percentile line (must come right after a merit number)
        if self._expecting_percentile:
            perc_match = PERCENTILE_PATTERN.match(line)
            if perc_match:
                percentile = Decimal(perc_match.group(1))
                if self._pending_merit is not None and self._category_index <= len(self.categories):
                    cat_idx = self._category_index - 1  # Already incremented
                    if 0 <= cat_idx < len(self.categories):
                        self.records.append(CutoffRecord(
                            category_code=self.categories[cat_idx],
                            stage=self._current_stage,
                            merit_number=self._pending_merit,
                            percentile=percentile,
                        ))
                self._pending_merit = None
                self._expecting_percentile = False
                return False

        # Check for merit number line
        merit_match = MERIT_NUMBER_PATTERN.match(line)
        if merit_match:
            # Flush any previous merit that didn't get a percentile
            self._flush_pending()

            self._pending_merit = int(merit_match.group(1))
            self._category_index += 1
            self._expecting_percentile = True
            return False

        return False

    def _flush_pending(self):
        """Flush a pending merit number that didn't get a percentile."""
        if self._pending_merit is not None and self._expecting_percentile:
            cat_idx = self._category_index - 1
            if 0 <= cat_idx < len(self.categories):
                self.records.append(CutoffRecord(
                    category_code=self.categories[cat_idx],
                    stage=self._current_stage or "",
                    merit_number=self._pending_merit,
                    percentile=None,
                ))
            self._pending_merit = None
            self._expecting_percentile = False

    def get_records(self) -> list[CutoffRecord]:
        """Get all parsed records."""
        self._flush_pending()
        return self.records

    def reset(self, categories: list[str] | None = None):
        """Reset the parser for a new block."""
        if categories is not None:
            self.categories = categories
        self.records = []
        self._current_stage = None
        self._category_index = 0
        self._pending_merit = None
        self._expecting_percentile = False
