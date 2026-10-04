---
name: read-social
description: "Reads a social media post from its link and returns the same structured result for every site: author, date, text, engagement counts, media, and replies when asked. Works with X (Twitter), LinkedIn, Instagram, TikTok, Bluesky, Reddit, Mastodon, Threads, and Hacker News. Use when you have a link to a post and want what it says, who posted it, or how it did. Use when you say \"read this tweet\", \"what does this post say\", \"pull this LinkedIn post\", \"read this thread\", \"get this Reddit thread\", \"fetch this post\", or \"what are people saying in the replies\"."
---

# Read social

Read any social post by URL. Detect the site, try its strategies in order (free first, paid last), and return one JSON shape no matter where the post came from.

## Step 1: Detect the site

| URL pattern | Site |
|---|---|
| `x.com/<user>/status/<id>`, `twitter.com/<user>/status/<id>` | `x` |
| `linkedin.com/posts/<slug>`, `linkedin.com/feed/update/urn:li:activity:<id>` | `linkedin` |
| `linkedin.com/in/<handle>` (profile, recent activity) | `linkedin-profile` |
| `instagram.com/p/<id>`, `instagram.com/reel/<id>` | `instagram` |
| `tiktok.com/@<user>/video/<id>` | `tiktok` |
| `bsky.app/profile/<handle>/post/<rkey>` | `bluesky` |
| `reddit.com/r/<sub>/comments/<id>/...` | `reddit` |
| `<instance>/@<user>/<id>` (mastodon.social, hachyderm.io, and others) | `mastodon` |
| `threads.net/@<user>/post/<id>`, `threads.com/...` | `threads` |
| `news.ycombinator.com/item?id=<id>` | `hn` |
| `youtube.com/watch?v=<id>`, `youtu.be/<id>`, Loom, Vimeo | A video: if `watch-video` is installed, use it. Otherwise say this skill reads posts, not videos. |

No match: offer to read it as a generic page with defuddle (Step 3), or ask which site it is.

## Step 2: Pick the strategy chain

Read `references/strategies.md` for the commands. Summary:

| Site | Free strategies, in order | Paid, only with a key |
|---|---|---|
| bluesky | Public API | none |
| mastodon | Public API, defuddle | none |
| hn | Algolia API | none |
| reddit | `.json` URL, defuddle, Wayback Machine | none |
| x | defuddle, agent-browser, Nitter, Wayback Machine | ScrapeCreators, Apify |
| linkedin | defuddle, agent-browser (dismiss the modal) | ScrapeCreators, Apify |
| instagram, tiktok, threads | Open Graph tags, defuddle | ScrapeCreators, Apify |
| anything else | defuddle | none |

defuddle is a free page reader. It is left out for Bluesky and Hacker News, where it failed in testing and the free APIs already work.

Rules:

- Free first. Paid strategies run only when their key is set, and only after asking: say which service and that it costs money.
- **defuddle** needs Node (`npx`). If `npx` is missing, skip that strategy and go on.
- **agent-browser**: if it is not installed, run the same steps with this session's browser tools (such as Claude in Chrome). If neither exists, skip it.
- A strategy that returns the post but lacks what the person asked for (engagement, replies, the full thread) does not end the chain. Keep the data and try the next strategy for the missing part.

## Step 3: Run the chain

For each strategy: try it. On success, normalize and return. On failure (404, 403, sign-in wall, empty result), note why and try the next.

If every strategy fails, say which ones ran, why each failed, and what would unlock it (for example: "Set `SCRAPECREATORS_API_KEY` for X replies, see `references/auth-keys.md`"). Private and deleted posts cannot be read by any strategy. Offer the Wayback Machine for deleted posts and stop.

## Step 4: Normalize

Return this shape for every site. The full spec and examples are in `references/output-schema.md`.

```json
{
  "platform": "x",
  "url": "https://x.com/example/status/1234567890",
  "fetched_at": "2026-10-04T14:35:00Z",
  "raw_source": "scrapecreators",
  "author": { "handle": "@example", "name": "Example Person", "verified": null },
  "posted_at": "2026-10-03T16:53:00Z",
  "text": "The post text.",
  "media": [],
  "engagement": { "likes": 51, "reposts": 13, "replies": 9, "bookmarks": 7, "views": null },
  "is_thread": false,
  "thread": [],
  "replies": []
}
```

A field the site does not provide is `null`, never `0`. Missing data is not zero data. defuddle returns no engagement, so a defuddle result has `null` engagement.

## Step 5: Options

| Option | What it does |
|---|---|
| `--with-replies` | Also fetch top-level replies (one level). Uses more API quota. |
| `--thread` | Fetch the whole thread when the author posted several in a row. |
| `--raw` | Include the raw response, for debugging. |
| `--media` | Download images and videos to `<folder>/<platform>-<id>/`. |
| `--save` | Save the JSON to `<folder>/<platform>-<id>.json`. |
| `--no-cache` | Skip the cache. |

`<folder>` is `READ_SOCIAL_DIR` if set, else `./social/` in the current folder. Default: the post only, media as URLs, nothing downloaded.

## Step 6: Cache

If `<folder>/_cache/` exists, save each successful result there as `<platform>-<id>.json` and reuse it for 24 hours. Skip the cache with `--no-cache`, `--with-replies`, or `--thread`, since replies change fast.

## Step 7: Report

1. One line: `<author> · <platform> · <date> · "<first 80 characters>..."`.
2. The JSON, inline, for the person or the skill that called this one.
3. The saved path, if `--save` was used.
4. If only part of the data came back, say what is missing and what would get it. Example: "Got the author and text. Replies need `SCRAPECREATORS_API_KEY`."

## Known limits

- **X**: free strategies return the post preview (text, author, sometimes basic engagement). Full threads and replies need `SCRAPECREATORS_API_KEY` or `APIFY_API_TOKEN`.
- **LinkedIn**: profile pages often work in a browser after dismissing the sign-in modal. Single posts often need a paid key.
- **Instagram, TikTok, Threads**: heavy blocking. Expect Open Graph text only without a paid key.
- **Reddit**: blocks anonymous requests from many networks, including some home connections. The Wayback Machine is the free fallback.
- **Bluesky, Mastodon, Hacker News**: free and reliable.
- **Rate limits**: space out requests when reading many posts in a row.
