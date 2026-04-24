# BetterVencord

BetterVencord is a patchset for Vencord (and now Equicord) that adds BetterDiscord compatibility.
It allows BetterDiscord plugins to run in Vencord/Equicord.

## Installation

You need pnpm, git and Node.js installed.

You can also use Deno v2 instead of Node.js, I like it more personally.

### For Discord Desktop

1. Clone the repository:
   ```bash
   git clone --recurse-submodules https://github.com/Davilarek/BetterVencordPatchset
   cd BetterVencordPatchset
   ```

2. Install dependencies:
   ```bash
   pnpm install
   ```

3. Build BetterVencord:
   ### For Vencord:
   ```bash
   # Using tsx (if you only have pnpm):
   pnpm dlx tsx scripts/build.ts

   # Using Deno (if you have Deno installed):
   deno task build:deno
   ```
   ### For Equicord:
   ```bash
   # Using tsx (if you only have pnpm):
   pnpm dlx tsx scripts/build.ts --equicord

   # Using Deno (if you have Deno installed):
   deno task buildEquicord:deno
   ```

4. Inject into Discord:
   ### For Vencord:
   ```bash
   cd dist/Vencord
   pnpm inject
   ```
   ### For Equicord:
   ```bash
   cd dist/Equicord
   pnpm inject
   ```

### For Web Browser

1. After building with either method above, look in `dist/Vencord/dist/` (or `dist/Equicord/dist/`) for:
   - Equicord/Vencord`.user.js` (UserScript)
   - `extension-chrome.zip` (Chrome extension)
   - `extension-firefox.zip` (Firefox extension)

2. For UserScript: Add Equicord/Vencord`.user.js` to your favorite manager

3. For extensions: Load unpacked extension

## Troubleshooting
### My plugin that uses network fails to load, what to do?
In BD Compat Layer, there is a toggle "Enable Experimental Request Polyfills" that allows plugins to use network.
### My BV install shows filesystem failed to load, what to do?
There are some occasions you might see that error,
#### Issue #1
Steps to confirm:
1. Open console
2. Scroll up to the point you see " Vencord   PluginManager  Starting plugin BD Compatibility Layer"
3. Look around there for errors
4. If you see something like `Access to fetch at https://xxxxxx/xxxxx from origin 'discord.com' has been blocked by CORS policy` 4 times close to eachother, it's likely this is your issue.

Solution:
1. Find a suitable replacement for your CORS proxy url. It's up to the user to find an appropriate substitute for the cors proxy url. The default one is just an example.
2. Open BD Compat Layer settings
3. Paste the url you found in first step into "CORS proxy used to bypass CORS" field
4. Reload
#### Issue #2
Steps to confirm:
1. You have enabled "Use Indexed DB Instead".
2. You have a small amount of RAM installed or a small amount of free space.
3. Open console
4. See Out of Memory Error

Solution:
There is no known fix for this issue right now. Try adding more RAM, perhaps.
#### Issue #3
Stepts to confirm:
1. You have not enabled "Use Indexed DB Instead".
2. You store large data (>10 MB) in Virtual Filesystem.

Solution:
There is a limit on localStorage size that varies on different platforms. If possible try migrating to IndexedDB.

## Using
Once installed, BetterVencord functions similar to Vencord but with BD Compatibility Layer under Plugins. This needs to be enabled first before you can add [BetterDiscord](https://betterdiscord.app/) plugin(s). A successful enabling of BD Compatibility Layer will show up an extra menu entry (on the left of discord UI) as Virtual Filesystem, under Backup & Restore. To then add BetterDiscord plugins, in Virtual Filesystem, left click on `/`, then `BD`, then right click on `plugins`, and click on Import a file here.

### Importing BD plugins
#### First BD plugin import
BetterVencord will not function properly if BD plugins are missing [ZeresPluginLibrary](https://github.com/rauenzi/BDPluginLibrary), the BD Compatibility Layer does not provide this library either. You will need to click on the link download the file somewhere temporarily, then import the ZeresPluginLibrary. See the next section about adding BD plugins.

#### Subsequent importing BD plugins
Newly imported plugins will not be immediately visible. To make it visible, collapse the plugins directory/folder then expand it again. This should ideally be done to visually confirm that the BD plugin has imported into the Virtual Filesystem, prior to enabling BD plugins to be visible within Vencord's plugin list. To do that, you will need to click on Reload BD Plugins, so that these changes should take effect under Vencord → Plugins. Confirm that the BD plugin has its own entry within Vencord. If the imported BD plugin does not have its own entry within the list of Plugins, it may not be compatible with BetterVencord, and should therefore be removed.

### Removing BD plugins
To remove BD plugins from BetterVencord, navigate to plugins directory/folder as mentioned above. Right click on the BD plugin that you wish to remove, and click on Delete file. You should also visually confirm that the removed BD plugin is no longer visible via collapsing and expanding plugins directory/folder. Once that is done, make sure you hit the Reload BD Plugins button to have changes take effect.

## Updating
You should keep the source code you cloned in first step to be able to update BV.

First, you `cd` to your directory where you cloned the source code.

Then,
```
git fetch
git pull
```
and then repeat compiling steps.

## License

Undecided.
