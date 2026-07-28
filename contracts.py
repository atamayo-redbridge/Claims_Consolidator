from __future__ import annotations

from copy import deepcopy
from typing import Any


CONTRACTS: dict[str, dict[str, dict[str, Any]]] = {
    "750133": {
        "2024": {
            "company": "International Hospitality Services",
            "deductible": 100000,
            "maximum_liability": 900000,
            "covered_benefits": ["MED", "RX"],
            "member_rules": {
                "23389637700": {
                    "type": "laser",
                    "deductible": 250000,
                },
                "23398547100": {
                    "type": "laser",
                    "deductible": 150000,
                },
            },
        },
        "2025": {
            "company": "International Hospitality Services",
            "deductible": 100000,
            "maximum_liability": 1000000,
            "covered_benefits": ["MED", "RX"],
            "member_rules": {
                "23389637700": {
                    "type": "laser",
                    "deductible": 300000,
                },
                "23400968000": {
                    "type": "laser",
                    "deductible": 200000,
                },
                "23389606301": {
                    "type": "laser",
                    "deductible": 150000,
                },
            },
        },
    },
    "750134": {
        "2024": {
            "company": "CONWASTE",
            "deductible": 150000,
            "maximum_liability": 850000,
            "covered_benefits": ["MED", "RX"],
            "member_rules": {},
        },
        "2025": {
            "company": "CONWASTE",
            "deductible": 150000,
            "maximum_liability": 850000,
            "covered_benefits": ["MED", "RX"],
            "member_rules": {},
        },
    },
    "750102": {
        "2025": {
            "company": "Cardinal Health PR",
            "deductible": 150000,
            "maximum_liability": 850000,
            "covered_benefits": ["MED", "RX"],
            "member_rules": {
                "23325932000": {
                    "type": "laser",
                    "deductible": 500000,
                },
                "23325936302": {
                    "type": "laser",
                    "deductible": 200000,
                },
                "23325938801": {
                    "type": "laser",
                    "deductible": 300000,
                },
                "23321395901": {
                    "type": "laser",
                    "deductible": 225000,
                },
                "23325914301": {
                    "type": "laser",
                    "deductible": 200000,
                },
            },
        },
        "2026": {
            "company": "Cardinal Health PR",
            "deductible": 150000,
            "maximum_liability": 850000,
            "covered_benefits": ["MED", "RX"],
            "member_rules": {
                "23325938801": {
                    "type": "laser",
                    "deductible": 350000,
                },
                "23395124702": {
                    "type": "laser",
                    "deductible": 360000,
                },
                "23395114800": {
                    "type": "laser",
                    "deductible": 250000,
                },
            },
        },
    },
    "750136": {
        "2025": {
            "company": "FENWAL INTERNATIONAL INC",
            "deductible": 125000,
            "maximum_liability": 875000,
            "covered_benefits": ["MED", "RX"],
            "member_rules": {},
            "notes": (
                "A 2025 laser exists, but the Member ID "
                "and amount are pending."
            ),
        },
        "2026": {
            "company": "FENWAL INTERNATIONAL INC",
            "deductible": 125000,
            "maximum_liability": 875000,
            "covered_benefits": ["MED", "RX"],
            "member_rules": {
                "23414805502": {
                    "type": "excluded",
                }
            },
        },
    },
    "750132": {
        "2024": {
            "company": "Grupo Cooperativo Seguros Multiples",
            "deductible": 100000,
            "maximum_liability": 900000,
            "covered_benefits": ["MED", "RX"],
            "member_rules": {
                "23382390001": {
                    "type": "excluded",
                },
                "23382407600": {
                    "type": "laser",
                    "deductible": 150000,
                },
            },
        },
        "2025": {
            "company": "Grupo Cooperativo Seguros Multiples",
            "deductible": 100000,
            "maximum_liability": 900000,
            "covered_benefits": ["MED", "RX"],
            "member_rules": {
                "23382390001": {
                    "type": "excluded",
                },
                "23382407600": {
                    "type": "laser",
                    "deductible": 150000,
                },
            },
        },
    },
    "750101": {
        "2025": {
            "company": "National University College",
            "deductible": 100000,
            "maximum_liability": 900000,
            "covered_benefits": ["MED", "RX"],
            "member_rules": {},
        }
    },
    "750109": {
        "2025": {
            "company": "Oriental Bank",
            "deductible": 175000,
            "maximum_liability": 1000000,
            "covered_benefits": ["MED", "RX", "DENT"],
            "member_rules": {
                "23397560700": {
                    "type": "laser",
                    "deductible": 500000,
                },
                "23397485400": {
                    "type": "laser",
                    "deductible": 500000,
                },
                "23397502801": {
                    "type": "laser",
                    "deductible": 250000,
                },
                "23397483300": {
                    "type": "laser",
                    "deductible": 250000,
                },
            },
        }
    },
    "750093": {
        "2024": {
            "company": "Universal Group",
            "deductible": 150000,
            "maximum_liability": 1000000,
            "covered_benefits": ["MED", "RX"],
            "member_rules": {
                "23383276501": {
                    "type": "excluded",
                }
            },
        },
        "2025": {
            "company": "Universal Group",
            "deductible": 200000,
            "maximum_liability": 2000000,
            "covered_benefits": ["MED", "RX"],
            "member_rules": {
                "23390024204": {
                    "type": "laser",
                    "deductible": 200000,
                },
                "23276817500": {
                    "type": "laser",
                    "deductible": 200000,
                },
                "23408941000": {
                    "type": "laser",
                    "deductible": 500000,
                },
                "23383276501": {
                    "type": "excluded",
                },
            },
        },
    },
    "750096": {
        "2026": {
            "company": "Walmart",
            "deductible": 125000,
            "maximum_liability": 875000,
            "covered_benefits": ["MED", "RX"],
            "member_rules": {},
        }
    },
}


LIBERTY_YEARS = {
    "2024": {
        "company": "Liberty Communications of PR",
        "deductible": 200000,
        "maximum_liability": 800000,
        "covered_benefits": ["MED", "RX"],
        "member_rules": {
            "23409445301": {
                "type": "laser",
                "deductible": 350000,
            },
            "23409212300": {
                "type": "laser",
                "deductible": 350000,
            },
            "23283558500": {
                "type": "laser",
                "deductible": 350000,
            },
        },
    },
    "2025": {
        "company": "Liberty Communications of PR",
        "deductible": 200000,
        "maximum_liability": 800000,
        "covered_benefits": ["MED", "RX"],
        "member_rules": {
            "23277353200": {
                "type": "excluded",
            },
            "23270105604": {
                "type": "excluded",
            },
        },
    },
    "2026": {
        "company": "Liberty Communications of PR",
        "deductible": 200000,
        "maximum_liability": 800000,
        "covered_benefits": ["MED", "RX"],
        "member_rules": {
            "23270105604": {
                "type": "laser",
                "deductible": 400000,
            },
            "23378173801": {
                "type": "laser",
                "deductible": 250000,
            },
            "23282225204": {
                "type": "laser",
                "deductible": 300000,
            },
            "23409521000": {
                "type": "laser",
                "deductible": 250000,
            },
            "23277673401": {
                "type": "laser",
                "deductible": 300000,
            },
            "23270857301": {
                "type": "laser",
                "deductible": 300000,
            },
        },
    },
}


for group in (
    "750123",
    "750124",
    "750125",
    "711205",
):
    CONTRACTS[group] = deepcopy(
        LIBERTY_YEARS
    )


def get_contract(
    group_number: str,
    policy_year: str,
) -> dict[str, Any]:
    group_number = str(
        group_number
    ).strip()

    policy_year = str(
        policy_year
    ).strip()

    if group_number.endswith(".0"):
        group_number = group_number[:-2]

    if group_number not in CONTRACTS:
        raise KeyError(
            f"Group {group_number} is not in the contract catalog."
        )

    if policy_year not in CONTRACTS[group_number]:
        available = (
            ", ".join(
                sorted(CONTRACTS[group_number])
            )
            or "none"
        )

        raise KeyError(
            f"Policy year {policy_year} is not configured "
            f"for group {group_number}. "
            f"Available years: {available}."
        )

    contract = deepcopy(
        CONTRACTS[group_number][policy_year]
    )

    contract["group_number"] = group_number
    contract["policy_year"] = policy_year

    return contract
