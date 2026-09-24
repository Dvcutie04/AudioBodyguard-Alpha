from dataclasses import fields

from src.extensions.gateway import ExtensionGateway
from src.extensions.proposal import ExtensionProposal
from src.control.authorized_intent import SignedActionIntent

def test_extension_proposal_cannot_satisfy_signed_intent_contract():
    proposal_fields={f.name for f in fields(ExtensionProposal)}
    intent_fields={f.name for f in fields(SignedActionIntent)}
    authority_fields={
        "issuer_id",
        "policy_digest",
        "capability_lease_digest",
        "created_at",
        "expires_at",
        "nonce",
        "transaction_id",
        "protocol_version",
        "signature",
    }
    assert authority_fields.issubset(intent_fields)
    assert proposal_fields.isdisjoint(authority_fields)

def test_extension_gateway_exposes_no_authority_minting_surface():
    exposed={name for name in dir(ExtensionGateway) if not name.startswith("_")}
    forbidden={
        "sign",
        "authorize",
        "mint_intent",
        "create_signed_intent",
        "issue_capability_lease",
        "commit",
        "actuate",
        "execute_intent",
        "bypass_firewall",
    }
    assert exposed.isdisjoint(forbidden)
