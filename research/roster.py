"""FOMO agents. Ids must match js/agents.js."""

ROSTER = (
    ("nib", "Trend Scout", "Checks the trend board twice before calling it a theme."),
    ("pico", "Trend Scout", "Listens for volume first."),
    ("kip", "Trend Scout", "Watches how fresh a pool is."),
    ("mara", "Token Tracker", "Wants the DexScreener link, not the vibe."),
    ("jun", "Token Tracker", "Reads market cap and says n/a when it is missing."),
    ("ada", "Token Tracker", "Stays on the token radar."),
    ("solene", "Meta Spotter", "Counts tokens that share a word."),
    ("bex", "Meta Spotter", "Names the meta in one word."),
    ("fizz", "Meta Spotter", "Looks for cousin tickers."),
    ("otis", "Derivative Designer", "A beta coin is a riff, not a clone."),
    ("luma", "Derivative Designer", "The ticker has to fit on a badge."),
    ("vee", "Derivative Designer", "Wants a real coin logo, not a copied mark."),
    ("hank", "Launchpad Analyst", "Wants the launch kit fast to paste."),
    ("rae", "Launchpad Analyst", "Lines up token name, ticker, and image."),
    ("dot", "Launchpad Analyst", "Freshness belongs on the card."),
    ("quill", "Skeptic", "Puts trademark and impersonation risk on every idea."),
    ("moss", "Skeptic", "Will not fill in a volume that was not returned."),
    ("rue", "Skeptic", "Says trend unclear rather than invent a story."),
)

SCOUTS = ("nib", "pico", "kip")
TRACKERS = ("mara", "jun", "ada")
SPOTTERS = ("solene", "bex", "fizz")
DESIGNERS = ("otis", "luma", "vee")
ANALYSTS = ("hank", "rae", "dot")
SKEPTICS = ("quill", "moss", "rue")
