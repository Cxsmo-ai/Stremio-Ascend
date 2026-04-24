# OpSec

A Vencord plugin that fixes your grammar, spelling, and punctuation before you send messages. Powered by Claude AI for context-aware correction that understands your intent.

## Features

- AI correction using Claude Haiku via the Anthropic API
- Three correction modes: Light, Medium, and Heavy
- Understands intent so "gonna kill this level" stays exactly that
- Preserves Discord mentions, roles, channels, and custom emoji
- Optional slang expansion (idk, ngl, lol, yk, fr, etc.)
- ALL CAPS preservation toggle
- Comma correction in Medium and Heavy modes
- Offline regex fallback when no API key is configured
- Custom word replacements
- No account data, user IDs, or metadata ever sent to the API

## Installation

1. Clone the Vencord repo and set it up manually if you haven't already
2. Navigate to `src/userplugins` (create the folder if it doesn't exist)
3. Clone this repo into that folder

```
cd Vencord/src/userplugins
git clone https://github.com/1nject-s-Vencord-Plugins/OpSec
```

4. Build and inject

```
cd ../..
pnpm build
pnpm inject
```

5. Open Discord, go to Settings > Vencord > Plugins, enable OpSec

## Setup

To use AI correction, add your Anthropic API key in the plugin settings. You can get one at [console.anthropic.com](https://console.anthropic.com). The key is stored locally in Vencord settings and never sent anywhere except directly to the Anthropic API.

If you leave the key blank the plugin falls back to fast offline regex corrections automatically.

## Settings

| Setting | Description | Default |
|--|--|--|
| Enable | Toggle the plugin on/off | true |
| API Key | Your Anthropic API key | empty |
| Mode | Correction strength (Light / Medium / Heavy) | Light |
| Expand Slang | Expand idk, ngl, lol, yk, fr, etc. to full phrases | false |
| Preserve Caps | Keep ALL CAPS as intentional emphasis | true |
| Fallback to Regex | Use offline corrections when AI is unavailable | true |
| Custom Replacements | Personal word swaps, one per line: `oldword=newword` | empty |

## Modes

**Light** - Fixes obvious typos, missing apostrophes in contractions, double spaces, and missing end punctuation. Nothing else is touched.

**Medium** - Also fixes first-word capitalization, missing commas, and obvious abbreviations. Keeps sentence structure and tone exactly as-is.

**Heavy** - Full grammar pass. Fixes run-ons, punctuation, commas, subject-verb agreement, and word order while strictly preserving your voice and tone. Casual stays casual.

## Slang Expansion

When enabled, common abbreviations are expanded to their full phrases before sending.

| Input | Output |
|--|--|
| `idk` | I don't know |
| `ngl` | not gonna lie |
| `lol` | laughing out loud |
| `lmao` | laughing my ass off |
| `yk` | you know |
| `tbh` | to be honest |
| `fr` | for real |
| `nvm` | never mind |
| `btw` | by the way |
| `omg` | oh my god |
| `brb` | be right back |
| `gtg` | got to go |
| `smh` | shaking my head |
| `imo` | in my opinion |
| `lmk` | let me know |
| `hmu` | hit me up |
| `afk` | away from keyboard |
| `iirc` | if I recall correctly |
| `afaik` | as far as I know |
| `ikr` | I know right |

## Privacy

Before any message is sent to the API, all Discord-specific tokens are stripped and replaced with neutral placeholders:

| Original | Placeholder |
|--|--|
| `<@123456>` | `__USER0__` |
| `<#789>` | `__CHANNEL1__` |
| Custom emoji | `__EMOJI2__` |
| URLs | `__URL3__` |

The AI only ever sees plain anonymous text. After correction the original tokens are restored. No usernames, server names, message IDs, or any other identifying data leave your client.

## Requirements

- Vencord installed from source
- Node.js and pnpm
- Anthropic API key (optional, for AI correction)

## Credits

Original concept by [aurickk](https://github.com/aurickk) and their [OpSec Mod](https://github.com/aurickk/OpSec).

Built on the [Vencord](https://github.com/Vendicated/Vencord) plugin system.
