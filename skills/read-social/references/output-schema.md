# Output schema

The same shape for every site. A field the site does not provide is `null`, never `0` or `""`. Missing data is not zero data.

## Schema

```typescript
{
  "platform": "x" | "linkedin" | "linkedin-profile" | "instagram" | "tiktok"
    | "bluesky" | "reddit" | "mastodon" | "threads" | "hn" | string,  // string = domain, for other pages
  "url": string,                  // canonical URL of the post
  "fetched_at": ISO8601,
  "raw_source":                   // which strategy succeeded
    "direct-api" | "defuddle" | "agent-browser" | "open-graph" | "nitter"
    | "wayback" | "scrapecreators" | "apify",

  "author": {
    "handle": string | null,      // @username
    "name": string | null,        // display name
    "verified": boolean | null,
    "follower_count": number | null,
    "profile_url": string | null,
    "avatar_url": string | null
  },

  "posted_at": ISO8601 | null,
  "edited_at": ISO8601 | null,

  "text": string,                 // post body, plain text or Markdown
  "html": string | null,          // original HTML when the source gives it (Mastodon)
  "language": string | null,      // ISO 639-1

  "media": Array<{
    "type": "image" | "video" | "gif" | "audio",
    "url": string,
    "alt": string | null,
    "width": number | null,
    "height": number | null,
    "duration_seconds": number | null
  }>,

  "engagement": {
    "likes": number | null,       // Reddit: upvotes. HN: points
    "reposts": number | null,     // retweets, shares, reblogs
    "replies": number | null,
    "bookmarks": number | null,
    "views": number | null,
    "quotes": number | null
  },

  "links": Array<{ "url": string, "expanded_url": string, "title": string | null }>,
  "mentions": string[],
  "hashtags": string[],

  "is_reply": boolean,
  "reply_to": { "url": string, "author_handle": string } | null,

  "is_thread": boolean,           // part of a run of posts by the same author
  "thread": Array<{ "url": string, "text": string, "posted_at": ISO8601 }>,   // excludes this post, in order

  "replies": Array<{              // only with --with-replies
    "url": string,
    "author": { "handle": string, "name": string | null },
    "text": string,
    "posted_at": ISO8601 | null,
    "engagement": { "likes": number | null, "replies": number | null }
  }>,

  "raw": object | null            // only with --raw
}
```

## What each strategy usually returns

| Field | bluesky | mastodon | hn | reddit | x (free) | x (paid) | defuddle | open-graph | linkedin (browser) | paid (ig, tiktok, threads, linkedin) |
|---|---|---|---|---|---|---|---|---|---|---|
| author.handle | yes | yes | yes | yes | yes | yes | partial | partial | yes | yes |
| author.follower_count | yes | yes | no | no | no | yes | no | no | no | yes |
| posted_at | yes | yes | yes | yes | yes | yes | partial | no | partial | yes |
| text | yes | yes | yes | yes | partial | yes | yes | partial | partial | yes |
| media | yes | yes | no | yes | no | yes | partial | image only | no | yes |
| engagement | yes | yes | likes, replies | likes, replies | partial | yes | no | no | no | yes |
| replies | yes | yes | yes | yes | no | yes | no | no | no | partial |
| thread | yes | yes | n/a | n/a | no | yes | no | no | no | partial |

`partial` means it depends on the post and the page.

## Examples

### bluesky, full

```json
{
  "platform": "bluesky",
  "url": "https://bsky.app/profile/example.com/post/3kabc",
  "raw_source": "direct-api",
  "author": { "handle": "@example.com", "name": "Example", "verified": null, "follower_count": 5012 },
  "posted_at": "2026-09-15T14:23:00Z",
  "text": "We're rolling out video posts.",
  "media": [],
  "engagement": { "likes": 1245, "reposts": 234, "replies": 89, "bookmarks": null, "views": null, "quotes": 12 }
}
```

### x, from defuddle

```json
{
  "platform": "x",
  "url": "https://x.com/jack/status/20",
  "raw_source": "defuddle",
  "author": { "handle": "@jack", "name": null, "verified": null, "follower_count": null },
  "posted_at": "2006-03-21T00:00:00Z",
  "text": "just setting up my twttr",
  "engagement": { "likes": null, "reposts": null, "replies": null, "bookmarks": null, "views": null, "quotes": null }
}
```

Engagement is all `null` because defuddle does not return it. If the person asked for engagement, try the next strategy.

### hn, with replies

```json
{
  "platform": "hn",
  "url": "https://news.ycombinator.com/item?id=8863",
  "raw_source": "direct-api",
  "author": { "handle": "dhouston" },
  "text": "My YC app: Dropbox - Throw away your USB drive",
  "links": [{ "url": "http://www.getdropbox.com/u/2/screencast.html", "expanded_url": "http://www.getdropbox.com/u/2/screencast.html", "title": null }],
  "engagement": { "likes": 104, "replies": 71 },
  "replies": [
    { "url": "https://news.ycombinator.com/item?id=8952", "author": { "handle": "BrandonM" }, "text": "...", "engagement": { "likes": null, "replies": 3 } }
  ]
}
```
