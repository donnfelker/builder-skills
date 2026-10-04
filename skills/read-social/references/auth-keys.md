# Paid keys

The free strategies cover Bluesky, Mastodon, Hacker News, Reddit, and X post previews. Paid keys add full X data with threads and replies, single LinkedIn posts, Instagram, TikTok, and Threads.

## What each key unlocks

| Key | Unlocks |
|---|---|
| `SCRAPECREATORS_API_KEY` | X (posts, threads, replies), LinkedIn posts, Instagram, TikTok, possibly Threads. Pay per request. |
| `APIFY_API_TOKEN` | Almost any site, through Apify "actors". Priced per actor. |

Check each service's pricing page before setting it up. Prices change, so this file does not list them.

## Setting a key

1. Sign up at https://scrapecreators.com or https://apify.com.
2. Copy the API key (Apify: Settings, then Integrations, then API).
3. Add it to your shell profile (`~/.zshrc` on macOS, `~/.bashrc` on most Linux):
   ```bash
   export SCRAPECREATORS_API_KEY="<your-key>"
   export APIFY_API_TOKEN="<your-token>"
   ```
4. Open a new terminal, or run `source ~/.zshrc`.
5. Check it is set without printing it: `test -n "$SCRAPECREATORS_API_KEY" && echo set`.

In Cowork or other hosted environments, set keys where that environment manages secrets.

## Free-only mode

With no keys set:

- Bluesky, Mastodon, Hacker News: full data.
- X: preview only (text, author, sometimes basic engagement). No thread or replies.
- Reddit: full data when the network is not blocked, else the Wayback Machine copy.
- LinkedIn profiles: recent activity through a browser. Single posts often fail.
- Instagram, TikTok, Threads: Open Graph text and image, or defuddle when it works.

## Spending carefully

- Always ask before a paid request, and say which service it uses.
- Check the cache first.
- `--with-replies` and `--thread` multiply requests. Use them only when asked.
- For many posts from one account, an Apify actor run is usually cheaper per post than single ScrapeCreators calls.
- If the same site falls through to "no paid key" three times in a session, mention once that a key would fix it. Do not repeat it.
