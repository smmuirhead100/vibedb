import re


class QueryCache:
    """Caches agent-written query handlers keyed by a natural-language template.

    Each entry maps a natural-language template (with `{placeholder}` slots) to the
    source of an async `handler(execute_query, params)` function. When a future message
    matches a template, the placeholder values are extracted into `params` and handed to
    the handler, which runs the query and reshapes the result — no LLM needed.
    """

    def __init__(self) -> None:
        # natural_language_template -> handler source code
        self.cache: dict[str, str] = {}

    def add(self, natural_language_template: str, handler_source: str) -> None:
        self.cache[natural_language_template] = handler_source

    def _template_to_regex(self, template: str) -> tuple[re.Pattern, list[str]]:
        """
        Convert a template string into a regex pattern with named groups.
        e.g. "Add new user with name {name} and email {email}"
          -> r"^Add new user with name (?P<name>.+?) and email (?P<email>.+?)$"
        Returns the compiled pattern and the ordered list of placeholder names.
        """
        placeholder_re = re.compile(r"\{(\w+)\}")
        placeholders = placeholder_re.findall(template)

        # Escape everything outside the placeholders, replace placeholders with named groups
        parts = placeholder_re.split(template)
        # split() interleaves literal parts and captured group names:
        # "Hello {name}, you are {age}" -> ["Hello ", "name", ", you are ", "age", ""]
        pattern_parts = []
        for i, part in enumerate(parts):
            if i % 2 == 0:
                # Literal text segment — escape for regex
                pattern_parts.append(re.escape(part))
            else:
                # Placeholder name — emit a named capture group
                # Use a non-greedy match that also captures quoted values (with or without quotes)
                pattern_parts.append(rf"['\"]?(?P<{part}>.+?)['\"]?")

        pattern = "^" + "".join(pattern_parts) + "$"
        return re.compile(pattern), placeholders

    def get_cached_query(
        self, natural_language_query: str
    ) -> tuple[str, dict[str, str]] | None:
        """
        Try to match natural_language_query against all cached templates.

        Returns (handler_source, params) if a match is found, or None if no template
        matches. `params` is the dict of values extracted from the message, ready to be
        passed straight to the cached handler.

        Example:
            cache: {"Get user with id {id}": "<handler source>"}
            query: "Get user with id 7"
            returns: ("<handler source>", {"id": "7"})
        """
        for template, handler_source in self.cache.items():
            pattern, _ = self._template_to_regex(template)
            match = pattern.match(natural_language_query)
            if match:
                return handler_source, match.groupdict()

        return None
