"""
Implements PID parsers.

The base parser handles scheme identification.
"""

import importlib
import typing

import lib_n2t.model
import lib_n2t.pidconfig


def load_parser(class_name):
    pkg, cls = class_name.rsplit(".", 1)
    _module = importlib.import_module(pkg)
    return getattr(_module, cls)


def default(a, b):
    if a is None:
        return b
    return a


class BasePidParser:
    def __init__(self, config: lib_n2t.pidconfig.PidConfig = None):
        if config is None:
            config = lib_n2t.pidconfig.PidConfig()
        self.config = config
        self.sub_match_name = "scheme"

    def _sub_parse(self, pid: lib_n2t.model.ParsedPid) -> lib_n2t.model.ParsedPid:
        """
        Used internally, should never need to call this method.

        Find the next parser from the configuration and hand off for
        further processing.

        Args:
            pid: lib_n2t.model.ParsedPid

        Returns: lib_n2t.model.ParsedPid
        """
        # Which part of the identifier are we matching next?
        sub_match = getattr(pid, self.sub_match_name)
        # Is there a matching entry for it?
        next_config, synonymized_sub_match = self.config.get_entry(sub_match)
        if synonymized_sub_match is not None:
            setattr(pid, self.sub_match_name, synonymized_sub_match)
        if next_config is None:
            # No further processing available
            return pid
        # Prepare for next step and hand off to the dynamically loaded parser
        next_parser_name = next_config.parser
        if next_parser_name is None:
            # No additional parser is configured for this pid,
            # but still need to set the target from the config
            template = next_config.target
            if template is not None:
                pid.target_template = template
            template = next_config.canonical
            if template is not None:
                pid.canon_template = template
            return pid
        # Hand off to the next parser
        next_parser = load_parser(next_parser_name)
        return next_parser(config=next_config).parse(pid)

    def parse(self, pid: lib_n2t.model.ParsedPid) -> lib_n2t.model.ParsedPid:
        """
        Parse the provided identifier string into components represented by a ParsedPid.

        Args:
            pid: ParsedPid, The identifier string to parse

        Returns:

        """
        pid_str = pid.pid.strip()
        parts = pid_str.split(":", 1)
        scheme = parts[0].strip()
        try:
            group_value = parts[1].strip()
            if group_value == "":
                group_value = None
        except IndexError:
            group_value = None
        pid.scheme = scheme
        pid.group_value_raw = group_value
        pid.target_template = self.config.target
        pid.canon_template = self.config.canonical
        if group_value is None:
            # No point in further parsing since there's nothing to parse.
            return pid
        return self._sub_parse(pid)


class GroupParser(BasePidParser):

    def __init__(self, config: lib_n2t.pidconfig.PidConfig = None):
        super().__init__(config=config)
        self.sub_match_name = "group"

    def parse(self, pid: lib_n2t.model.ParsedPid) -> lib_n2t.model.ParsedPid:
        if pid.group_value is None or pid.group_value == '':
            return pid
        group_value = pid.group_value
        _parts = group_value.split("/", 1)
        _group = _parts[0].strip()
        try:
            _value = _parts[1].strip()
        except IndexError:
            _value = None
        _pid = lib_n2t.model.ParsedGroupPid(
            pid=pid.pid,
            scheme=pid.scheme,
            group_value_raw=pid.group_value,
            group_raw=_group,
            value_raw=_value,
            # Get the templates from config or use existing pid templates
            target_template=default(self.config.target, pid.target_template),
            canon_template=default(self.config.canonical, pid.canon_template),
        )
        return self._sub_parse(_pid)


class ArkParser(GroupParser):
    def parse(self, pid: lib_n2t.model.ParsedPid) -> lib_n2t.model.ParsedPid:
        group_value = pid.group_value.lstrip(" /")
        _parts = group_value.split("/", 1)
        _group = _parts[0].strip()
        _group = _group.lower()
        try:
            _value = _parts[1].strip()
            # TODO: adjust this to keep replacing occurences of / and .
            _value = _value.rstrip(" ./")
            _value = _value.replace("//", "/")
            _value = _value.replace("./", ".")
            _value = _value.replace("/.", "/")
        except IndexError:
            _value = None
        _pid = lib_n2t.model.ParsedArkPid(
            pid=pid.pid,
            scheme=pid.scheme,
            group_value_raw=group_value,
            group_raw=_group,
            value_raw=_value,
            # Get the templates from config or use existing pid templates
            target_template=default(self.config.target, pid.target_template),
            canon_template=default(self.config.canonical, pid.canon_template),
        )
        return self._sub_parse(_pid)


class DoiParser(GroupParser):
    def parse(self, pid: lib_n2t.model.ParsedPid) -> lib_n2t.model.ParsedPid:
        group_value = pid.group_value.lstrip(" /")
        _parts = group_value.split("/", 1)
        _group = _parts[0].strip()
        try:
            _value = _parts[1].strip()
        except IndexError:
            _value = None
        _pid = lib_n2t.model.ParsedDoiPid(
            pid=pid.pid,
            scheme=pid.scheme,
            group_value_raw=group_value,
            group_raw=_group,
            value_raw=_value,
            # Get the templates from config or use existing pid templates
            target_template=default(self.config.target, pid.target_template),
            canon_template=default(self.config.canonical, pid.canon_template),
        )
        return self._sub_parse(_pid)

