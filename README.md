# AppTweak Fetch

Fetch top App Store apps for given keywords — metadata + screenshots saved locally.

## Install

```bash
# With API key
curl -fsSL https://raw.githubusercontent.com/akopanev/apptweak-fetch/main/install.sh | bash -s -- .apptweak YOUR_API_KEY

# Without API key (edit .env manually after install)
curl -fsSL https://raw.githubusercontent.com/akopanev/apptweak-fetch/main/install.sh | bash
```

Get your API key at https://app.apptweak.com/apt-api/

## Usage

```bash
.apptweak/fetch.sh "habit tracker,daily habits,routine planner"
```

## Output

```
output/
├── apps.json           # full metadata, screenshots_local = local file paths
├── streaks/
│   ├── screenshot_1.jpg
│   └── screenshot_2.jpg
├── habitify/
│   └── ...
└── ...
```
