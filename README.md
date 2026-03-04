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
.apptweak/fetch.sh <keywords> [output_dir] [top_n]
```

| Param | Default | Description |
|---|---|---|
| `keywords` | required | Comma-separated search terms |
| `output_dir` | `./output` | Where to save results |
| `top_n` | `5` | Number of top apps to fetch |

### Examples

```bash
# Defaults: ./output, top 5
.apptweak/fetch.sh "habit tracker,daily habits,routine planner"

# Custom output dir and top 3
.apptweak/fetch.sh "photo editor,image filter" ./research 3
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
