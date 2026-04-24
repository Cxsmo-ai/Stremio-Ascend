# Local Message Editor

A Vencord plugin for **security education and demonstration purposes** that allows you to edit and delete any Discord message locally on your client. 

> ⚠️ **IMPORTANT**: This plugin is designed to demonstrate why Discord should **never be used for high-value transactions or trades**. All changes are LOCAL ONLY and do not affect what others see or what's actually stored on Discord's servers.

## 🎯 Purpose

This plugin demonstrates a critical security vulnerability concept: **client-side message manipulation**. By showing how easy it is to fake message history locally, it educates users about:

- Why screenshots of Discord messages are not trustworthy evidence
- Why Discord DMs are unsafe for financial transactions
- How easily "proof" can be fabricated
- The importance of using secure, verified platforms for trades

## ✨ Features

- **Edit Any Message**: Right-click any message and select "Edit Message (Local Demo)" to change its content
- **Delete Any Message**: Use Discord's delete function (now works on all messages) to hide messages locally  
- **Restore Original**: Undo any local edits or deletions with the "Restore Original Message" option
- **Clean UI**: Uses Discord's native modal interface for a seamless experience
- **Perfect for Demos**: Instantly show viewers how message history can be manipulated
- **Note: The Restore Original option isnt working rn, If you want to change it back to the original, Click on Restore original then go to edit message locally and click save. That will restore the message**

## 📦 Installation

1. Make sure you have [Vencord](https://vencord.dev/) installed (Make sure you also have Node.js installed)
2. Download this plugin and place it in your Vencord plugins folder:
   ```
   src/plugins/localMessagesEditor/
   ```
3. Open terminal and open your vencord folder.
   ```Run
   cd Vencord
   ```
3. Build Vencord:
   ```bash
   pnpm build
   ```
4. Inject Vencord:
   ```bash
   pnpm inject
   ```
4. Enable the plugin in Vencord settings

## 🚀 Usage

### Editing Messages
1. Right-click on any message in Discord
2. Select **"Edit Message (Local Demo)"**
3. A modal will appear with the current message content
4. Edit the text to whatever you want
5. Click **"Save Local Edit"**
6. The message now shows your edited version (only on your screen!)

### Deleting Messages
1. Right-click on any message
2. Select Discord's normal **"Delete Message"** option
3. The message is hidden locally (only for you)

### Restoring Originals
1. Right-click on a message you've edited or deleted
2. Select **"Restore Original Message"**
3. The message returns to its original state

## 🎓 Educational Use Cases

Perfect for:
- **Security awareness streams/videos** demonstrating Discord vulnerabilities
- **Trading safety education** showing why Discord isn't secure for transactions  
- **Scam prevention workshops** teaching people not to trust Discord screenshots
- **Digital literacy training** about client-side manipulation

## ⚙️ How It Works

The plugin uses multiple techniques to achieve local message manipulation:

1. **Permission Override**: Bypasses Discord's permission checks to show edit/delete options on all messages
2. **Context Menu Integration**: Adds custom menu items using Vencord's context menu API
3. **DOM Manipulation**: Directly modifies the displayed message content in the browser
4. **Delete Interception**: Intercepts Discord's delete function to hide messages locally instead of sending delete requests

All changes are **purely visual** and exist only in your browser session. Nothing is transmitted to Discord's servers.

## 🔒 Limitations

- Changes are **LOCAL ONLY** - other users see the original messages
- Edits persist only during your session (refresh Discord = changes lost)
- Cannot modify message metadata like timestamps or reactions  
- Does not work on system messages

## 📝 Technical Details

**Plugin Structure:**
- Context menu patches for edit/delete options
- Custom React modal component for editing interface
- DOM manipulation for instant visual updates
- Local storage maps for tracking edits and deletes

**Key Files:**
- `index.tsx` - Main plugin file with all functionality

## 🤝 Contributing

This is an educational tool. If you find bugs or have suggestions for improving the demonstration value, feel free to open an issue or pull request.

## ⚖️ Legal & Ethical Notice

This plugin is provided for **educational and security awareness purposes only**. 

**DO NOT USE THIS TO:**
- Deceive others or fabricate evidence
- Scam or defraud people
- Harass or manipulate others
- Violate Discord's Terms of Service in harmful ways

**Intended Use:**
- Security education and awareness
- Demonstrating platform vulnerabilities
- Teaching digital literacy
- Warning others about trusting Discord for transactions

By using this plugin, you agree to use it ethically and responsibly for educational purposes only.

## 👨‍💻 Author

**juiceroyals** - Security education & awareness

## 📄 License

This plugin is provided as-is for educational purposes. Use responsibly.

---

**Remember**: If someone shows you Discord messages as "proof" of payment or agreement, they could be using tools like this. Always use secure, verified platforms for any transactions involving money or valuable items.
