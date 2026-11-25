import os

# The platform tests check the posting mechanism, not the owner's live switches (config "paused_platforms").
os.environ.setdefault("GOLIDE_PAUSED_PLATFORMS", "")
