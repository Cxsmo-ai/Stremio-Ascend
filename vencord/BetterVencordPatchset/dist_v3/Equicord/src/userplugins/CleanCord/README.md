# CleanCord - Server & Folder Hider for Vencord

![Banner](https://repository-images.githubusercontent.com/1027152240/1cae1602-f4be-470b-a213-6f54c31049b0)

CleanCord is a Vencord plugin that allows you to hide specific servers and folders from your Discord server list, for various use cases 🔎 !

## Bookmarks
- [Features](#features)
- [Installation (Desktop)](#installation-desktop-version)
- [Installation (Web)](#installation-web-version)
- [Usage](#usage)
- [Options](#options)
- [FAQ](#faq)
- [Screenshots](#screenshots)
- [Support](#support)
- [Credits](#credits)
- [Star History](#star-history)
- [License](#license)

# Features
- Hide individual servers with a right-click
- Hide entire folders with a right-click
- Option to only hide servers when in Streamer Mode
- Option to also hide servers when using Quick-Switcher (CTRL+K)
- Option to Manage Discord behaviour for incoming mentions from hidden servers/folders (Both in real-time & on startup)
- Manage hidden servers/folders through Vencord plugin settings

## Installation (Desktop Version)
**Prerequiries** : [git](https://git-scm.com/downloads) / [NodeJS](https://nodejs.org/en/download) / [pnpm](https://pnpm.io/installation)
- Open a CMD window, you will need a clone of Vencord's Repository, command : `git clone https://github.com/Vendicated/Vencord`
- Navigate to the path where you cloned the repository and be sure to enter the 'Vencord' folder (Ex : "`cd C:\Documents\Vencord`") then type : `pnpm install --frozen-lockfile`
- Now inside the 'Vencord' Folder, navigate to "`cd .\src\`" and type : "`md userplugins`"
- Navigate to "`cd .\userplugins\`", and clone CleanCord within : `git clone https://github.com/TetraSsky/CleanCord/`
- Then build : `pnpm build`
- And lastly inject : `pnpm inject` (Select your Discord path (Stable / Canary))

You're now ready to use CleanCord (be sure to enable it in Vencord's plugin settings) !

## Installation (Web Version)
**⚠️ Be sure to have completed all of the steps above ⚠️**

*You can however exclude both last commands : `pnpm build` & `pnpm inject`, since they're not needed for the web version*

*PS : If you have previously installed the official Vencord extension, you might want to disable/uninstall it to avoid conflicts*

- You will need to build as a web browser extension with : `pnpm buildWeb`
- This will generate a new folder in the main Vencord folder, path : 'Vencord\dist'
- Head on your web browser and open "chrome://extensions" (This can vary depending on your browser)
- Enable "Developer Mode" (*if available/needed*)
- Click on "Load Unpacked" and select the "dist/chromium-unpacked" folder for chromium based browsers or "dist/firefox-unpacked" for Firefox

You're now ready to use CleanCord, on your browser (same, be sure to enable it in Vencord's plugin settings) !

## Usage

### Hiding Servers/Folders
1. Right-click on any server or folder in your server list
2. Select "Hide Server" or "Hide Folder" from the context menu
3. The server/folder will immediately disappear from your view

### Managing Hidden Items
1. Go to Vencord Settings > Plugins > CleanCord (Or right-click --> "Manage CleanCord's settings")
2. You'll see two sections:
   - **Hidden Servers**: Lists all currently hidden servers
   - **Hidden Folders**: Lists all currently hidden folders
3. Toggle the checkboxes to show/hide items
4. Use "Unhide All" to reset everything

### Streamer Mode Integration
Enable the "Only hide in Streamer Mode" option to:
- Keep servers/folders visible normally
- Automatically hide them when Streamer Mode is active
- Automatically handle notifications & mentions when Streamer Mode is active

## Options
| Option | Description | Default | Clearing Type |
|--------|-------------|---------|------|
| Show Options | Displays the hide/unhide options in right-click menus | Enabled | - |
| Only Hide in Streamer Mode | Servers/folders will only be hidden when Streamer Mode is active | Disabled | - |
| Hide In Quick Switcher | Also hide servers from the quick switcher (Ctrl+K) | Disabled | - |
| Suppression Mode | Default - Keep initial Discord behaviour for notifications / Silent - Block all notifications in real-time from hidden servers/folders (Resets on startup) | Silent | Clears in Real-Time |
| Auto Clear Mentions | Automatically clear all unread badges from hidden servers/folders on startup (Recommended to use with Suppression Mode set to 'Silent') | Disabled | Clears on Startup |
| Hidden Servers | Manage your list of hidden servers | - | - |
| Hidden Folders | Manage your list of hidden folders | - | - |

## FAQ

**❓: Do hidden servers still show notifications?**
- No, hidden servers won't display unread messages, mention counts or play notifications sounds.
(Only when **Suppresion Mode** is set to <ins>Silent</ins> & (Preferably) **Auto Clear Mentions** is <ins>enabled</ins>)

**❓: Can I still access hidden servers?**
- Yes, you can still access them through Quick Switcher (Ctrl+K), joining one of your friends' activity, etc... or by unhiding them in settings.

**❓: Does this plugin breaks interaction with hidden servers?**
- No, people from any hidden server can still interact with you and vise versa. The "icons" Discord displays in the server listing are only hidden with Custom CSS injection.

**❓ : Will people know I'm using CleanCord?**
- No, this is purely a visual change on your client. Moreover, there is a setting to completely hide CleanCord's right-click options!
(Same goes whilst streaming, by enabling the option, CleanCord will silently hide your hidden elements the moment **Streamer Mode** is on)

**❓: Will my hidden elements stay hidden after restarting Discord?**
- Yes, your preferences are saved between sessions thanks to Vencord!

## Screenshots
<table>
  <tr>
    <td width="50%"><img src="https://github.com/user-attachments/assets/b731f5f3-1d9b-4920-b769-633f0205efc0" alt="Context menu" style="width:100%"></td>
    <td width="50%"><img src="https://github.com/user-attachments/assets/85e66d52-b003-45c3-a274-7fcb92efebb0" alt="Settings panel" style="width:100%"></td>
  </tr>
  <tr>
    <td width="50%"><img src="https://github.com/user-attachments/assets/eb2f9d8d-0107-4030-b915-361d25288bf0" alt="Streamer mode example" style="width:100%"></td>
    <td width="50%"><img src="https://github.com/user-attachments/assets/9d57bac4-6c60-4723-b307-4c8c010dad4d" alt="Streamer mode example 2" style="width:100%"></td>
  </tr>
  <tr>
    <td width="50%"><img src="https://github.com/user-attachments/assets/789037da-7cde-4169-ad4c-ad9e2da0a61f" alt="Hidden elements showcase" style="width:100%"></td>
  </tr>
</table>

## Support
If you encounter any issues or have feature requests (This will entirely depend of my free time. Be aware.):
[Open an issue](https://github.com/yourusername/CleanCord/issues)

## Credits
This plugin is built for and requires [Vencord](https://github.com/Vendicated/Vencord), a Discord client mod! Big thanks to them ❤️❤️❤️!

## Star History
[![Star History Chart](https://api.star-history.com/svg?repos=TetraSsky/CleanCord&type=Date)](https://www.star-history.com/#TetraSsky/CleanCord&Date)

## License
MIT License - See [LICENSE](LICENSE) for details.
