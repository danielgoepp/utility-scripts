import argparse
import requests
import logging
import json
from config import CLOUDFLARE_API_TOKEN, CLOUDFLARE_ZONE_ID

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


def check_and_delete_stale_acme_challenges(dry_run=False):
    url = f"https://api.cloudflare.com/client/v4/zones/{CLOUDFLARE_ZONE_ID}/dns_records"
    headers = {
        "Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}",
    }

    if dry_run:
        logging.info("DRY RUN mode — no records will be deleted. Use --delete to remove records.")

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        records = response.json()

        with open(
            "/tmp/cf_clear_stale_acme_backup.json",
            "w",
        ) as backup_file:
            json.dump(records, backup_file, indent=2)

        if not records["result"]:
            logging.info("No DNS records found.")
            return

        for record in records["result"]:
            if (
                record["type"] == "TXT"
                and record["name"] == "_acme-challenge.goepp.net"
            ):
                if "content" in record and record["content"] is not None:
                    logging.info(
                        f"Found stale _acme-challenge record for {record['name']}"
                    )
                    if dry_run:
                        logging.info(
                            f"[DRY RUN] Would delete record id={record['id']} for {record['name']}"
                        )
                    else:
                        delete_url = f"https://api.cloudflare.com/client/v4/zones/{CLOUDFLARE_ZONE_ID}/dns_records/{record['id']}"
                        delete_response = requests.delete(delete_url, headers=headers)
                        delete_response.raise_for_status()
                        logging.info(
                            f"Deleted stale _acme-challenge record for {record['name']}"
                        )
                else:
                    logging.debug(
                        f"TXT record for {record['name']} has no content (not a challenge)."
                    )

        logging.info("Stale _acme-challenge check completed.")

    except requests.exceptions.RequestException as e:
        logging.error(f"An error occurred: {e}")
    except KeyError as e:
        logging.error(f"KeyError: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Clear stale ACME challenge DNS records from Cloudflare.")
    parser.add_argument("--delete", action="store_true", help="Actually delete stale records (default is dry-run).")
    args = parser.parse_args()

    check_and_delete_stale_acme_challenges(dry_run=not args.delete)
