# Access Intelligence

A simple Streamlit app for your access-resource master file.

It reads one pipe-delimited master file that contains:
- access pattern mappings
- access resource master rows

## What it does

- pick a module from a dropdown
- pick an access resource from a dropdown
- see every URL or API route that resource controls
- search by activity, URL, or access ID
- export one access resource as CSV

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## GitHub deploy

This is ready for Streamlit Community Cloud or any GitHub-based deploy.

## Files

- `app.py` — Streamlit UI
- `core.py` — parsing and matching logic
- `data/master_access_file.txt` — your master file
- `requirements.txt` — dependencies

## Master file format

The repo uses a single file with two sections:

1. Access pattern section
   - `id`
   - `access_resource_id`
   - `url_pattern`
   - `created`
   - `updated`

2. Access resource section
   - `id`
   - `name`
   - `access_resource_group_id`
   - `level`
   - `created`
   - `updated`

## Good next upgrades

- add a role mapping file
- add "missing access" checker
- add search by user role
- add tree view by module and group
