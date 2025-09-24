import requests
import config

HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json",
    "Authorization": f"Bearer {config.GRAFANA_API_KEY}",
}


def fetch_datasources():
    grafana_url = f"{config.GRAFANA_URL}/api/datasources"
    response = requests.get(grafana_url, headers=HEADERS)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error fetching datasources: {response.status_code}")
        return []


def validate_datasources(datasources):
    datasources = []
    for ds in datasources:
        datasources.append(
            {
                "id": ds.get("id"),
                "uid": ds.get("uid"),
                "name": ds.get("name"),
                "type": ds.get("type"),
            }
        )
    return datasources


if __name__ == "__main__":
    datasources = fetch_datasources()
    print(f"Fetched {len(datasources)} datasources.")
    if not datasources:
        print("No datasources found or error fetching datasources.")

    valid_datasources = validate_datasources(datasources)
    if valid_datasources:
        print("Valid datasources found:")
        for ds in valid_datasources:
            print(
                f"ID: {ds['id']}, UID: {ds['uid']}, Name: {ds['name']}, Type: {ds['type']}"
            )
    else:
        print("All datasources are valid.")
