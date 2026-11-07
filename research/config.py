"""Shared constants for the 30-minute research publisher."""

SCAN_INTERVAL_SECONDS = 30 * 60
PUBLIC_URL = "https://joeypbrrr.github.io/fomo-world/"
USER_AGENT = (
    "fomo-world-research/0.1 "
    "(concept research; +https://github.com/joeypbrrr/fomo-world)"
)
# Applied when a cluster has no sourced story. Unclear trends stay on the
# board but sort below anything we can actually explain.
CONTEXT_SCORE_FACTOR = 0.45
IMAGE_PX = 1000
DEFAULT_IMAGE_INBOX = "/workspace/fomo-world/generated"
