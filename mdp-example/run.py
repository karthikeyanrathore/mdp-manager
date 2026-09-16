#!/usr/bin/env python3
import json
import urllib.request
import re

from policies import ROUTING_POLICIES

# [3/8/23, 00:00:37] Sender Name: message text
HEADER_RE = re.compile(
    r"^\[(\d{1,2}/\d{1,2}/\d{2,4}), (\d{1,2}:\d{2}(?::\d{2})?)\] ([^:]+?): ?(.*)$"
)

# Bidi/joiner marks WhatsApp sprinkles around system messages and phone numbers.
INVISIBLE = dict.fromkeys(
    map(ord, "​‌‍‎‏‪‫‬‭‮️"),
    None,
)

EMOJI_RE = re.compile(
    "["
    "\U0001f000-\U0001faff"  # emoji, pictographs, symbols, flags
    "\U00002190-\U000021ff"  # arrows
    "\U00002300-\U000023ff"
    "\U000024c2"
    "\U000025a0-\U000027bf"  # geometric shapes, dingbats
    "\U00002b00-\U00002bff"
    "\U00003030\U0000303d\U00003297\U00003299"
    "\U0000fe00-\U0000fe0f"  # variation selectors
    "\U0001f1e6-\U0001f1ff"  # regional indicators
    "\U000e0020-\U000e007f"  # tag characters
    "]+"
)

BASE = "http://localhost:8000/api"


def post(path, payload):
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        return json.load(resp)


def get(path):
    with urllib.request.urlopen(BASE + path) as resp:
        return json.load(resp)


def find_by_name(path, name):
    """Walk a paginated list endpoint looking for an object with this name."""
    url = BASE + path
    while url:
        with urllib.request.urlopen(url) as resp:
            page = json.load(resp)
        for existing in page["results"]:
            if existing["name"] == name:
                return existing
        url = page["next"]
    return None


def get_or_create(path, payload):
    """Names are unique here, so reuse the object if a previous run created it."""
    return find_by_name(path, payload["name"]) or post(path, payload)


# Attachment placeholders left behind by a "without media" export.
OMITTED_RE = re.compile(
    r"\s*\b(?:image|document|sticker|video|audio|GIF)\s+omitted\b", re.IGNORECASE
)


# The filename an attachment was exported under, e.g.
# "WhatsApp Image 2025-12-26 at 21.08.45.jpeg" — only dropped when it was the
# whole caption of an omitted attachment, so filenames inside real messages stay.
FILENAME_RE = re.compile(
    r".*\.(?:jpe?g|png|gif|webp|pdf|docx?|pptx?|xlsx?|mp3|mp4|opus|zip)"
    r"(?:\s*\u2022\s*\d+\s*(?:pages?|slides?|[KMG]B))?",
    re.IGNORECASE,
)

# "This message was deleted.", plus the "... by admin ~ Name." variant.
DELETED_RE = re.compile(r"^(?:This message was deleted|You deleted this message)\b")


def clean_message(text):
    text = EMOJI_RE.sub("", text).replace("\u00a0", " ").replace("\u202f", " ")
    stripped = OMITTED_RE.sub("", text)
    if stripped != text and FILENAME_RE.fullmatch(stripped.strip()):
        stripped = ""
    elif DELETED_RE.match(stripped.strip()):
        stripped = ""
    return re.sub(r"[ \t]{2,}", " ", stripped).strip()


def parse_chat(path, keep_empty=False):
    """Yield (date, time, sender, message) with emojis and bidi marks removed."""
    with open(path, encoding="utf-8") as fh:
        current = None
        for raw in fh:
            line = raw.translate(INVISIBLE).rstrip("\r\n")
            match = HEADER_RE.match(line)
            if match:
                if current and (keep_empty or current[3]):
                    yield current
                date, time, sender, body = match.groups()
                current = (date, time, sender.strip(), clean_message(body))
            elif current:
                # continuation line of a multi-line message
                joined = (current[3] + "\n" + clean_message(line)).strip()
                current = current[:3] + (joined,)
        if current and (keep_empty or current[3]):
            yield current


def messages(path):
    """Just the message bodies, as strings."""
    return [msg for _, _, _, msg in parse_chat(path)]


if __name__ == "__main__":

    # for msg in messages("witthoutmedia_chat_20Aug2026.txt"):
    # print(msg)
    # print("/n")

    # MDP
    project = get_or_create("/projects/", {"name": "Uni-Messages"})
    project_id = project["id"]

    msg_3 = """
        Does anybody know the time and place for BCI?
    """
    markdown_1 = post(
        "/markdowns/?skip_embed=true/",
        {
            "project": project_id,
            "title": "message 1, Author Name: X",
            "text": msg3,
        },
    )

    policies = [
        get_or_create(f"/projects/{project_id}/routing-policies/", policy)
        for policy in ROUTING_POLICIES
    ]

    routing_policy = get(f"/markdowns/{markdown_1['id']}/routing-policy/")

    # print(json.dumps(project, indent=2))
    # print(json.dumps(markdown, indent=2))
    # print(json.dumps(policies, indent=2))
    print(json.dumps(routing_policy, indent=2))
