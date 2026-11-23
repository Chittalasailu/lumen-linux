<svg xmlns="http://www.w3.org/2000/svg" width="1920" height="1080" viewBox="0 0 1920 1080">
  <defs>
    <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0"    stop-color="{{ colors.bg }}"/>
      <stop offset="0.62" stop-color="{{ colors.surface }}"/>
      <stop offset="1"    stop-color="{{ colors.surface_alt }}"/>
    </linearGradient>
    <radialGradient id="sun" cx="0.5" cy="0.5" r="0.5">
      <stop offset="0"   stop-color="{{ colors.accent }}" stop-opacity="1"/>
      <stop offset="0.45" stop-color="{{ colors.accent }}" stop-opacity="0.55"/>
      <stop offset="1"   stop-color="{{ colors.accent }}" stop-opacity="0"/>
    </radialGradient>
  </defs>
  <rect width="1920" height="1080" fill="url(#sky)"/>
  <circle cx="1380" cy="640" r="420" fill="url(#sun)"/>
  <circle cx="1380" cy="640" r="150" fill="{{ colors.accent }}"/>
  <!-- layered ridgelines -->
  <path d="M0 760 C260 700 420 780 640 740 C900 690 1080 800 1320 750 C1560 700 1740 780 1920 730 L1920 1080 L0 1080 Z"
        fill="{{ colors.surface_alt }}" opacity="0.85"/>
  <path d="M0 860 C300 800 520 900 800 850 C1080 800 1300 910 1560 860 C1720 830 1840 850 1920 840 L1920 1080 L0 1080 Z"
        fill="{{ colors.surface }}"/>
  <path d="M0 960 C360 920 640 1000 960 960 C1280 920 1600 1000 1920 950 L1920 1080 L0 1080 Z"
        fill="{{ colors.bg }}"/>
  <!-- teal horizon line -->
  <rect x="0" y="758" width="1920" height="2" fill="{{ colors.accent_alt }}" opacity="0.35"/>
</svg>
