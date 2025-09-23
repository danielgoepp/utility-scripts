import requests
import logging
import json
from config import CLOUDFLARE_API_TOKEN, CLOUDFLARE_ZONE_ID

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


def check_and_delete_stale_acme_challenges():
    url = f"https://api.cloudflare.com/client/v4/zones/{CLOUDFLARE_ZONE_ID}/dns_records"
    headers = {
        "Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}",
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        records = response.json()

        with open(
            "/Users/dang/Documents/Development/goepp-lab/cloudflare/cf_clear_stale_acme_backup.json",
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
                    url = f"https://api.cloudflare.com/client/v4/zones/{CLOUDFLARE_ZONE_ID}/dns_records/{record['id']}"
                    response = requests.delete(url, headers=headers)
                    response.raise_for_status()
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
    check_and_delete_stale_acme_challenges()
