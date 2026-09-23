"""
Set the per-URL autofill behavior on 1Password items.

1Password treats every subdomain of a website as the same site by default, so
logins for many internal hosts under one domain all get offered everywhere on
that domain. This script finds every item with a URL on the configured domains
and sets the autofill behavior of those URLs (by default to "Only on this exact
host"). URLs on other domains are left untouched.

Uses the 1Password Python SDK with desktop app authentication, because the op
CLI cannot read or set autofill behavior. Runs as a dry run unless --apply is
given. After each write, the item is re-read and verified that nothing other
than autofill behavior changed.
"""

import argparse
import asyncio
import hashlib
import json
import sys
from urllib.parse import urlparse

from config import OP_ACCOUNT, OP_AUTOFILL_DOMAINS
from onepassword import AutofillBehavior, Client, DesktopAuth

BEHAVIORS = {
    "exact-host": AutofillBehavior.EXACTDOMAIN,
    "anywhere": AutofillBehavior.ANYWHEREONWEBSITE,
    "never": AutofillBehavior.NEVER,
}


def host_of(url):
    """Return the lowercase hostname of a URL, tolerating a missing scheme."""
    if "://" not in url:
        url = "https://" + url
    return (urlparse(url).hostname or "").lower()


def in_scope(url, domains):
    """Return True if the URL's host is one of the domains or a subdomain of one."""
    host = host_of(url)
    return any(host == d or host.endswith("." + d) for d in domains)


def fingerprint(item):
    """Hash everything about an item except website autofill behavior.

    Used to verify a write changed nothing else, without printing secrets.
    """
    data = {
        "title": item.title,
        "category": str(item.category),
        "notes": item.notes,
        "tags": sorted(item.tags or []),
        "fields": [(f.id, f.title, f.field_type.value, f.section_id, f.value) for f in item.fields],
        "sections": [(s.id, s.title) for s in item.sections],
        "websites": [(w.url, w.label) for w in item.websites],
    }
    return hashlib.sha256(json.dumps(data, sort_keys=True, default=str).encode()).hexdigest()


async def find_items(client, domains, item_filter):
    """Return (vault, item) pairs for items with at least one in-scope URL."""
    found = []
    for vault in await client.vaults.list():
        overviews = await client.items.list(vault.id)
        ids = [
            o.id
            for o in overviews
            if any(in_scope(w.url, domains) for w in (o.websites or []))
            and (not item_filter or o.id in item_filter or o.title in item_filter)
        ]
        for i in range(0, len(ids), 50):
            resp = await client.items.get_all(vault.id, ids[i : i + 50])
            for r in resp.individual_responses:
                if r.content is None:
                    print(f"Error reading item in vault {vault.title}: {r.error}", file=sys.stderr)
                    continue
                found.append((vault, r.content))
    return sorted(found, key=lambda x: (x[0].title, x[1].title.lower()))


async def apply_item(client, vault, item, domains, target):
    """Update one item's in-scope URLs and verify the result. Returns True on success."""
    before = fingerprint(item)
    changed = []
    for w in item.websites:
        if in_scope(w.url, domains) and w.autofill_behavior != target:
            w.autofill_behavior = target
            changed.append(w.url)

    await client.items.put(item)

    after = await client.items.get(vault.id, item.id)
    unchanged = fingerprint(after) == before
    states = {w.url: w.autofill_behavior for w in after.websites}
    return unchanged and all(states.get(u) == target for u in changed)


async def main():
    parser = argparse.ArgumentParser(
        description="Set 1Password URL autofill behavior for items on the configured domains"
    )
    parser.add_argument(
        "--behavior",
        choices=BEHAVIORS,
        default="exact-host",
        help="Autofill behavior to set (default: exact-host)",
    )
    parser.add_argument(
        "--domains",
        help="Comma-separated domains to target (default: OP_AUTOFILL_DOMAINS from .env)",
    )
    parser.add_argument(
        "--item",
        action="append",
        default=[],
        help="Limit to an item ID or exact title (repeatable)",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write changes (default is a dry run)",
    )
    args = parser.parse_args()

    domains = (
        [d.strip().lower() for d in args.domains.split(",") if d.strip()]
        if args.domains
        else OP_AUTOFILL_DOMAINS
    )
    if not OP_ACCOUNT or not domains:
        print("Error: OP_ACCOUNT and OP_AUTOFILL_DOMAINS (or --domains) must be set", file=sys.stderr)
        sys.exit(1)
    target = BEHAVIORS[args.behavior]

    client = await Client.authenticate(
        auth=DesktopAuth(OP_ACCOUNT),
        integration_name="utility-scripts set-autofill-behavior",
        integration_version="v1.0.0",
    )

    items = await find_items(client, domains, set(args.item))
    pending = []
    for vault, item in items:
        needs = any(in_scope(w.url, domains) and w.autofill_behavior != target for w in item.websites)
        if needs:
            pending.append((vault, item))
        for w in item.websites:
            if in_scope(w.url, domains):
                mark = "->" if w.autofill_behavior != target else "  "
                print(f"{mark} {vault.title:<20.20} {item.title:<40.40} {w.autofill_behavior.value:<18} {w.url}")

    print(f"\n{len(items)} items on {', '.join(domains)}; {len(pending)} need changing to {target.value}")

    if not args.apply:
        if pending:
            print("Dry run; re-run with --apply to write changes")
        return

    ok = failed = skipped = 0
    for vault, item in pending:
        try:
            success = await apply_item(client, vault, item, domains, target)
        except Exception as e:
            # e.g. items with legacy saved web-form fields the SDK cannot edit;
            # the write is rejected whole, so the item is left untouched
            skipped += 1
            print(f"SKIP  {item.title} (not editable via SDK, change manually in the app: {e})")
            continue
        if success:
            ok += 1
            print(f"OK    {item.title}")
        else:
            failed += 1
            print(f"FAIL  {item.title} (verification failed; check this item in 1Password)")
    print(f"\n{ok} updated, {skipped} skipped, {failed} failed")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
