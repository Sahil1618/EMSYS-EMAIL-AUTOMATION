# """
# seed_south_region.py — one-time setup for the South region (SRLDC) plants
# you gave recipient details for. Run this once after deploying the updated
# code:

#     python seed_south_region.py

# It's idempotent — safe to run again later (e.g. after adding a 4th plant to
# this list): it checks each plant's POS Name first and UPDATES the existing
# entity instead of creating a duplicate if it's already registered.

# All three plants share the same 'Scheduling entity' code (PVG_RES_QCA) in
# the actual government files — POS Name is what tells them apart, which is
# exactly why the portal now matches by POS Name rather than entity_key.
# """

# import db

# db.init_db()

# SOUTH_ENTITY_KEY = "PVG_RES_QCA"
# REGION = "SRLDC"

# PLANTS = [
#     {
#         "display_name": "PVG Adani KA Nine + Parampujya",
#         "pos_name": "PVG_AdaniKANine, PVG_PARAMPUJYA",
#         "energy_type": "SOLAR",
#         "smtp_account": "energymeteo_ops1",
#         "to": [
#             "ops_sch@reconnectenergy.com",
#             "ravi.kiran@reconnectenergy.com",
#             "ops_dynamic@reconnectenergy.com",
#         ],
#         "cc": [
#             "Rakesh.Dash@adani.com",
#             "Jairaj.Bayad@adani.com",
#             "Dixit.Pampaniya@adani.com",
#             "sabarigirishan.bhrugubanda@adani.com",
#             "indian-operations@energymeteo.com",
#             "indian-operations3@energymeteo.com",
#         ],
#     },
#     {
#         "display_name": "PVG Avaada Solar",
#         "pos_name": "PVG_AVAADASOLAR",
#         "energy_type": "SOLAR",
#         "smtp_account": "gmail_forecasting2",
#         "to": [
#             "ops_sch@reconnectenergy.com",
#             "ops_dynamic@reconnectenergy.com",
#         ],
#         "cc": [
#             "mohammad.junaid@avaada.com",
#             "basavaraj.pujari@avaada.com",
#             "dhiren.bhatt@avaada.com",
#         ],
#     },
#     {
#         "display_name": "PVG Avaada Solarise",
#         "pos_name": "PVG_AvaadaSolarise",
#         "energy_type": "SOLAR",
#         "smtp_account": "gmail_forecasting2",
#         "to": [
#             "ops_sch@reconnectenergy.com",
#             "ops_dynamic@reconnectenergy.com",
#         ],
#         "cc": [
#             "mohammad.junaid@avaada.com",
#             "basavaraj.pujari@avaada.com",
#             "dhiren.bhatt@avaada.com",
#         ],
#     },
# ]


# def main():
#     for plant in PLANTS:
#         # Match on the FIRST pos_name in the bundle — good enough to detect
#         # "this plant is already registered" for idempotency.
#         first_pos = plant["pos_name"].split(",")[0].strip()
#         existing = db.get_entity_by_pos_name(first_pos)

#         if existing:
#             db.update_entity_meta(
#                 existing["id"], plant["display_name"], REGION,
#                 plant["pos_name"], plant["energy_type"], plant["smtp_account"],
#             )
#             db.replace_recipients(existing["id"], plant["to"], plant["cc"])
#             print(f"Updated existing entity: {plant['display_name']} (id={existing['id']})")
#         else:
#             entity_id = db.create_entity(
#                 entity_key=SOUTH_ENTITY_KEY,
#                 display_name=plant["display_name"],
#                 region=REGION,
#                 to_emails=plant["to"],
#                 cc_emails=plant["cc"],
#                 pos_name=plant["pos_name"],
#                 energy_type=plant["energy_type"],
#                 smtp_account=plant["smtp_account"],
#             )
#             print(f"Created new entity: {plant['display_name']} (id={entity_id})")

#     print("\nDone. Check these under Manage Entities to confirm everything looks right.")


# if __name__ == "__main__":
#     main()


"""
seed_south_region.py — one-time setup for the South region (SRLDC) plants
you gave recipient details for. Run this once after deploying the updated
code:

    python seed_south_region.py

It's idempotent — safe to run again later (e.g. after adding a 4th plant to
this list): it checks each plant's POS Name first and UPDATES the existing
entity instead of creating a duplicate if it's already registered.

All three plants share the same 'Scheduling entity' code (PVG_RES_QCA) in
the actual government files — POS Name is what tells them apart, which is
exactly why the portal now matches by POS Name rather than entity_key.
"""

import db

db.init_db()

SOUTH_ENTITY_KEY = "PVG_RES_QCA"
REGION = "SRLDC"

PLANTS = [
    {
        "display_name": "PVG Adani KA Nine + Parampujya",
        "pos_name": "PVG_AdaniKANine, PVG_PARAMPUJYA",
        "energy_type": "SOLAR",
        "smtp_account": "energymeteo_ops1",
        "to": [
            "ops_sch@reconnectenergy.com",
            "ravi.kiran@reconnectenergy.com",
            "ops_dynamic@reconnectenergy.com",
        ],
        "cc": [
            "Rakesh.Dash@adani.com",
            "Jairaj.Bayad@adani.com",
            "Dixit.Pampaniya@adani.com",
            "sabarigirishan.bhrugubanda@adani.com",
            "indian-operations@energymeteo.com",
            "indian-operations3@energymeteo.com",
        ],
    },
    {
        "display_name": "PVG Avaada Solar",
        "pos_name": "PVG_AVAADASOLAR",
        "energy_type": "SOLAR",
        "smtp_account": "gmail_forecasting2",
        "to": [
            "ops_sch@reconnectenergy.com",
            "ops_dynamic@reconnectenergy.com",
        ],
        "cc": [
            "mohammad.junaid@avaada.com",
            "basavaraj.pujari@avaada.com",
            "dhiren.bhatt@avaada.com",
        ],
    },
    {
        "display_name": "PVG Avaada Solarise",
        "pos_name": "PVG_AvaadaSolarise",
        "energy_type": "SOLAR",
        "smtp_account": "gmail_forecasting2",
        "to": [
            "ops_sch@reconnectenergy.com",
            "ops_dynamic@reconnectenergy.com",
        ],
        "cc": [
            "mohammad.junaid@avaada.com",
            "basavaraj.pujari@avaada.com",
            "dhiren.bhatt@avaada.com",
        ],
    },
]


def main():
    messages = []
    for plant in PLANTS:
        # Match on the FIRST pos_name in the bundle — good enough to detect
        # "this plant is already registered" for idempotency.
        first_pos = plant["pos_name"].split(",")[0].strip()
        existing = db.get_entity_by_pos_name(first_pos)

        if existing:
            db.update_entity_meta(
                existing["id"], plant["display_name"], REGION,
                plant["pos_name"], plant["energy_type"], plant["smtp_account"],
            )
            db.replace_recipients(existing["id"], plant["to"], plant["cc"])
            messages.append(f"Updated existing entity: {plant['display_name']} (id={existing['id']})")
        else:
            entity_id = db.create_entity(
                entity_key=SOUTH_ENTITY_KEY,
                display_name=plant["display_name"],
                region=REGION,
                to_emails=plant["to"],
                cc_emails=plant["cc"],
                pos_name=plant["pos_name"],
                energy_type=plant["energy_type"],
                smtp_account=plant["smtp_account"],
            )
            messages.append(f"Created new entity: {plant['display_name']} (id={entity_id})")

    for m in messages:
        print(m)
    return messages


if __name__ == "__main__":
    main()