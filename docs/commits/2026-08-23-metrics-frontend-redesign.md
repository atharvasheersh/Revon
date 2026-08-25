# White metrics frontend redesign

Date: 2026-08-23

## Summary

Replaced the sidebar-led product dashboard with a minimalist, white,
metrics-first research workspace.

## Changes

- Converted the dark sidebar into a compact white top navigation.
- Added a functional benchmark workload selector for 10, 100, 10K, 100K, and
  1M records.
- Added a selected-workload metric while keeping repository measurements
  explicitly separated from configuration so unmeasured results are never
  implied.
- Reorganized the leading viewport around workload scale, HEAD, versions,
  storage, node reuse, history, comparison work, and integrity.
- Adopted high-contrast black typography, thin rules, square metric cards, and
  restrained cobalt accents on an all-white surface.
- Preserved repository creation, import, atomic commit, checkout, comparison,
  API configuration, responsive behavior, and accessibility states.
- Replaced the social-preview image and metadata to match the new metrics-led
  visual identity.

## Verification

- `npm run lint`: passed.
- `npm test`: production build passed and 2 rendered-page tests passed.
