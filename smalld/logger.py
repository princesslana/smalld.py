import contextlib
import logging

logger = logging.getLogger("smalld")

redactions = []


def redact_from_logging(to_redact):
    redactions.append(to_redact)


def redact_from(s):
    redacted = str(s)

    for redaction in redactions:
        if redaction in redacted:
            redacted = redacted.replace(redaction, "[[ REDACTED ]]")

    return redacted


class RedactingFilter(logging.Filter):
    def filter(self, record):
        record.msg = redact_from(record.msg)

        if isinstance(record.args, dict):
            record.args = {k: redact_from(v) for k, v in record.args.items()}
        else:
            record.args = tuple(redact_from(arg) for arg in record.args)

        return True


logger.addFilter(RedactingFilter())


@contextlib.contextmanager
def suppress_logging(name):
    suppress = logging.getLogger(name)
    suppress.disabled = True
    yield
    suppress.disabled = False
