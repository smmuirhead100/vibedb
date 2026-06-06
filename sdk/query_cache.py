import re


class QueryCache:
    def __init__(self) -> None:
        self.cache: dict[str, str] = {}

    def add_query_to_cache(self, template: str, corresponding_query: str) -> None:
        self.cache[template] = corresponding_query

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

        Returns (sql_query_with_values_substituted, args_dict) if a match is found,
        or None if no template matches.

        Example:
            cache: {"Add new user with name {name} and email {email}":
                    "INSERT INTO users (name, email) VALUES ('{name}', '{email}')"}
            query: "Add new user with name 'John Doe' and email 'john.doe@example.com'"
            returns: ("INSERT INTO users (name, email) VALUES ('John Doe', 'john.doe@example.com')",
                      {"name": "John Doe", "email": "john.doe@example.com"})
        """
        for template, sql in self.cache.items():
            pattern, placeholders = self._template_to_regex(template)
            match = pattern.match(natural_language_query)
            if match:
                args = match.groupdict()
                # Substitute extracted values into the SQL template
                resolved_sql = sql
                for key, value in args.items():
                    resolved_sql = resolved_sql.replace(f"{{{key}}}", value)
                return resolved_sql, args

        return None
