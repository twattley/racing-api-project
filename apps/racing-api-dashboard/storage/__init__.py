import atexit
from api_helpers.clients import get_betfair_client, get_postgres_client

# Create clients without connecting at import time to avoid repeated logins
# in dev server reloads or page refreshes. The Betfair client will lazily
# login on first use via check_session() in its methods.
bf_client = get_betfair_client(connect=False)
pg_client = get_postgres_client()

# Ensure we cleanly logout when the process exits.
atexit.register(lambda: bf_client.logout())
