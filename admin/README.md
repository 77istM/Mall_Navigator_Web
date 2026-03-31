# Admin and Operator Tooling

This folder contains operational tooling introduced for Phase 5.

## Available Tools

- `onboard_store.py`: one-command scaffold for a new mall dataset.

## Streamlit Admin Page

Operator UI is available at `pages/4_Admin_Dashboard.py`.

Features:
- View/edit/delete products and opening hours
- Upload floor plans and auto-generate starter graphs
- Visual graph editor to add/remove nodes and edges
- Analytics and log viewer
- One-click onboarding form for new stores

## Command Example

```bash
python admin/onboard_store.py --store-id my_mall --name "My Mall" --lat 51.5 --lng -0.1
```
