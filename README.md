# spam-domains
Auto updated domain list of known spam domains

## Update

Add upstream sources (one URL per line) to `sources.txt`.

Run locally:

```bash
python3 scripts/update_spamdomains.py --output spamdomains.txt --sources-file sources.txt
```

## GitHub Actions

This repo includes a scheduled GitHub Action that runs the updater and opens a pull request with changes to `spamdomains.txt`.
