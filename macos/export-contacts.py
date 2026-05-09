#!/usr/bin/env python3
"""Export macOS Contacts to CSV.

Requires pyobjc-framework-Contacts. On first run, the system will prompt
for permission to access Contacts.
"""

import argparse
import csv
import sys
import threading
from datetime import datetime

import Contacts

KEYS = [
    Contacts.CNContactGivenNameKey,
    Contacts.CNContactMiddleNameKey,
    Contacts.CNContactFamilyNameKey,
    Contacts.CNContactNamePrefixKey,
    Contacts.CNContactNameSuffixKey,
    Contacts.CNContactNicknameKey,
    Contacts.CNContactOrganizationNameKey,
    Contacts.CNContactDepartmentNameKey,
    Contacts.CNContactJobTitleKey,
    Contacts.CNContactEmailAddressesKey,
    Contacts.CNContactPhoneNumbersKey,
    Contacts.CNContactPostalAddressesKey,
    Contacts.CNContactUrlAddressesKey,
    Contacts.CNContactBirthdayKey,
]

CSV_FIELDS = [
    "first_name",
    "middle_name",
    "last_name",
    "prefix",
    "suffix",
    "nickname",
    "organization",
    "department",
    "job_title",
    "emails",
    "phones",
    "addresses",
    "urls",
    "birthday",
]


def request_access(store):
    sem = threading.Semaphore(0)
    granted = [False]

    def handler(g, err):
        granted[0] = g
        sem.release()

    store.requestAccessForEntityType_completionHandler_(Contacts.CNEntityTypeContacts, handler)
    sem.acquire()

    if not granted[0]:
        status = Contacts.CNContactStore.authorizationStatusForEntityType_(Contacts.CNEntityTypeContacts)
        print("Error: access to Contacts was denied.", file=sys.stderr)
        if status == 2:
            print("Go to System Settings > Privacy & Security > Contacts and enable access.", file=sys.stderr)
        else:
            print("If running from an IDE, try running from Terminal.app instead so the permission dialog can appear.", file=sys.stderr)
        sys.exit(1)


def format_address(postal):
    parts = [
        postal.street(),
        postal.city(),
        postal.state(),
        postal.postalCode(),
        postal.country(),
    ]
    return ", ".join(p for p in parts if p)


def nsdate_components_to_str(components):
    if components is None:
        return ""
    year = components.year()
    month = components.month()
    day = components.day()
    if year == 1 << 63:  # NSDateComponentUndefined sentinel
        return f"--{month:02d}-{day:02d}"
    return f"{year:04d}-{month:02d}-{day:02d}"


def fetch_contacts():
    store = Contacts.CNContactStore.alloc().init()
    request_access(store)

    fetch_request = Contacts.CNContactFetchRequest.alloc().initWithKeysToFetch_(KEYS)
    fetch_request.setSortOrder_(Contacts.CNContactSortOrderFamilyName)

    contacts = []

    def enumerator(contact, stop):
        emails = ";".join(e.value() for e in contact.emailAddresses())
        phones = ";".join(p.value().stringValue() for p in contact.phoneNumbers())
        addresses = ";".join(
            format_address(a.value()) for a in contact.postalAddresses()
        )
        urls = ";".join(u.value() for u in contact.urlAddresses())

        contacts.append({
            "first_name": contact.givenName(),
            "middle_name": contact.middleName(),
            "last_name": contact.familyName(),
            "prefix": contact.namePrefix(),
            "suffix": contact.nameSuffix(),
            "nickname": contact.nickname(),
            "organization": contact.organizationName(),
            "department": contact.departmentName(),
            "job_title": contact.jobTitle(),
            "emails": emails,
            "phones": phones,
            "addresses": addresses,
            "urls": urls,
            "birthday": nsdate_components_to_str(contact.birthday()),
        })

    success, err = store.enumerateContactsWithFetchRequest_error_usingBlock_(
        fetch_request, None, enumerator
    )

    if not success:
        print(f"Error fetching contacts: {err}", file=sys.stderr)
        sys.exit(1)

    return contacts


def write_csv(contacts, output_file):
    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(contacts)
    print(f"Exported {len(contacts)} contacts to {output_file}")


def main():
    parser = argparse.ArgumentParser(description="Export macOS Contacts to CSV")
    parser.add_argument(
        "-o", "--output",
        help="Output file path (default: contacts-YYYY-MM-DD.csv)",
    )
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="Print to stdout instead of writing to a file",
    )
    args = parser.parse_args()

    contacts = fetch_contacts()

    if args.stdout:
        writer = csv.DictWriter(sys.stdout, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(contacts)
        return

    date_str = datetime.now().strftime("%Y-%m-%d")
    output_file = args.output or f"contacts-{date_str}.csv"
    write_csv(contacts, output_file)


if __name__ == "__main__":
    main()
