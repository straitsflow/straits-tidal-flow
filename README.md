# Straits Tidal Flow

Tidal current viewer for the Singapore Strait, Johor Strait and approaches. Prototype, not for navigation.

**Open it:** https://kaixiang1988.github.io/straits-tidal-flow/

## Data
- **Currents:** MPA Digital Tidal Atlas hourly predictions (Sudong points A–D and ADCP, Eastern Bunkering points A and B). These are model predictions published monthly, not live measurements.
- **Tide heights:** Tanjong Pagar HW/LW predictions (MPA, published by NEA).
- **Johor Strait:** estimated in the app with a tidal-prism (continuity) model. No official data is available there.
- Outside the published range, the app uses harmonic fits to the MPA data, and the badge says so.

## Auto-update
`.github/workflows/update.yml` runs at 09:00 SGT on the 1st to 5th and the 15th of each month, and also on demand from the Actions tab. It downloads the previous, current and next month from MPA, refreshes the tide tables, refits, rebuilds `site/index.html` and publishes it to GitHub Pages.

## Layout
- `src/app.src.html`: the app source.
- `src/vendor/`: Leaflet 1.9.4 and Chart.js 4.4.1.
- `data/`: data files.
- `scripts/`: fetch, fit and build scripts.
