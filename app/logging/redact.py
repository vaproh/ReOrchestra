def redact_proxy(proxy: str) -> str | None:
    """Return host:port only, strip credentials."""
    if not proxy:
        return None
    parts = proxy.replace("http://", "").split("@")
    return parts[-1] if len(parts) > 1 else proxy


def redact_password(password: str) -> str | None:
    """Show last 2 chars only."""
    if not password:
        return None
    return "****" + password[-2:] if len(password) > 2 else "****"


def redact_sensitive(data: dict) -> dict:
    """Redact sensitive fields from dict for logging."""
    result = dict(data)
    for key in list(result.keys()):
        kl = key.lower()
        if "password" in kl:
            result[key] = redact_password(result[key])
        elif "proxy" in kl and ("user" in kl or "pass" in kl):
            result[key] = "[REDACTED]"
        elif "proxy" in kl:
            result[key] = redact_proxy(result[key])
    return result
