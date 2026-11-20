"""One broken rule at one place, as every rule module reports it."""

from __future__ import annotations

import dataclasses


@dataclasses.dataclass(frozen=True, order=True)
class Finding:
    """One place a rule is broken.

    Attributes:
        path: The file's repository path, with forward slashes.
        line: The line, counted from 1, or 0 for the whole file.
        rule: The rule's short name, such as ``tmp-prefix``.
        message: What is wrong and what would fix it.
    """

    path: str
    line: int
    rule: str
    message: str

    def render(self) -> str:
        """Write the finding as the checker prints it.

        Returns:
            ``path:line: rule message``.
        """
        return f"{self.path}:{self.line}: {self.rule} {self.message}"
