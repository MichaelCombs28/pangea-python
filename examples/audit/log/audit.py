import os

import pangea.exceptions as pe
from pangea.config import PangeaConfig
from pangea.services import Audit
from pangea.services.audit.models import Event

token = os.getenv("AUDIT_AUTH_TOKEN")
config_id = os.getenv("AUDIT_CONFIG_ID")
domain = os.getenv("PANGEA_DOMAIN")
config = PangeaConfig(domain=domain, config_id=config_id)
audit = Audit(token, config=config)

# This example shows how to perform an audit log


def main():
    event = Event(
        message="Hello world",
    )

    print(f"Logging: {event.dict(exclude_none=True)}")

    try:
        log_response = audit.log(event=event, verbose=False)
        print(f"Response. Hash: {log_response.result.hash}")
    except pe.PangeaAPIException as e:
        print(f"Request Error: {e.response.summary}")
        for err in e.errors:
            print(f"\t{err.detail} \n")


if __name__ == "__main__":
    main()
