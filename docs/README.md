# OmniClaw Docs

This directory is organized by purpose instead of by audience overlap.

## Start Here

- [SDK Usage Guide](SDK_USAGE_GUIDE.md): practical setup and common workflows
- [API Reference](API_REFERENCE.md): public SDK surface and environment contract
- [Architecture and Features](FEATURES.md): how the SDK is structured internally
- [Cross-Chain Usage](CCTP_USAGE.md): focused guide for `destination_chain` flows

## Reference and Internal Notes

- [ERC-8004 Spec Notes](erc_804_spec.md)
- [Roadmap](../ROADMAP.md)

## What Changed

The docs were consolidated to remove repeated setup, repeated `pay()` examples, and stale environment guidance. The intended split is now:

- `README.md`: project-level entry point
- `SDK_USAGE_GUIDE.md`: workflow guide
- `API_REFERENCE.md`: method reference
- `FEATURES.md`: architecture and concepts

If a topic does not need its own page, it should stay inside one of those four documents.
