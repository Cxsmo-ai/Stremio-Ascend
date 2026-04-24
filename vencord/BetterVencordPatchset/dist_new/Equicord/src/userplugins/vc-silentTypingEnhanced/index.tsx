/*
 * Vencord, a modification for Discord's desktop app
 * Copyright (c) 2022 Vendicated and contributors
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
*/

import { ChatBarButton, ChatBarButtonFactory } from "@api/ChatButtons";
import { ApplicationCommandInputType, ApplicationCommandOptionType, findOption, sendBotMessage } from "@api/Commands";
import { definePluginSettings } from "@api/Settings";
import { Devs } from "@utils/constants";
import definePlugin, { IconComponent, OptionType } from "@utils/types";
import { ChannelStore, FluxDispatcher, React } from "@webpack/common";

const settings = definePluginSettings({
    showIcon: {
        type: OptionType.BOOLEAN,
        default: true,
        description: "Show an icon for toggling the plugin",
        restartNeeded: true,
    },
    isEnabled: {
        type: OptionType.BOOLEAN,
        description: "Toggle functionality",
        default: true,
    },
    specificChats: {
        type: OptionType.BOOLEAN,
        default: false,
        description: "Disable silent typing for specific chats instead (use icon to toggle)",
        restartNeeded: false,
    },
    disabledFor: {
        type: OptionType.STRING,
        description: "Disable functionality for these chats (comma separated list of guild or user IDs)",
        default: "",
    },
});

function SilentTypingEnabledIcon() {
    return (
        <SilentTypingIcon>
            <mask id="silent-typing-msg-mask">
                <path fill="#fff" d="M0 0h24v24H0Z"></path>
                <path stroke="#000" strokeWidth="5.99068" d="M0 24 24 0" transform="translate(-2, -3)"></path>
            </mask>
            <path fill="var(--status-danger)" d="m21.178 1.70703 1.414 1.414L4.12103 21.593l-1.414-1.415L21.178 1.70703Z" />
        </SilentTypingIcon>
    );
}

const SilentTypingIcon: IconComponent = ({ height = 20, width = 20, className, children }) => {
    return (
        <svg
            width={width}
            height={height}
            className={className}
            viewBox="0 0 24 24"
            style={{ scale: "1.2" }}
        >
            <path fill="currentColor" mask="url(#silent-typing-msg-mask)" d="M18.333 15.556H1.667a1.667 1.667 0 0 1 -1.667 -1.667v-10a1.667 1.667 0 0 1 1.667 -1.667h16.667a1.667 1.667 0 0 1 1.667 1.667v10a1.667 1.667 0 0 1 -1.667 1.667M4.444 6.25V4.861a0.417 0.417 0 0 0 -0.417 -0.417H2.639a0.417 0.417 0 0 0 -0.417 0.417V6.25a0.417 0.417 0 0 0 0.417 0.417h1.389a0.417 0.417 0 0 0 0.417 -0.417m3.333 0V4.861a0.417 0.417 0 0 0 -0.417 -0.417H5.973a0.417 0.417 0 0 0 -0.417 0.417V6.25a0.417 0.417 0 0 0 0.417 0.417h1.389a0.417 0.417 0 0 0 0.417 -0.417m3.333 0V4.861a0.417 0.417 0 0 0 -0.417 -0.417h-1.389a0.417 0.417 0 0 0 -0.417 0.417V6.25a0.417 0.417 0 0 0 0.417 0.417h1.389a0.417 0.417 0 0 0 0.417 -0.417m3.333 0V4.861a0.417 0.417 0 0 0 -0.417 -0.417h-1.389a0.417 0.417 0 0 0 -0.417 0.417V6.25a0.417 0.417 0 0 0 0.417 0.417h1.389a0.417 0.417 0 0 0 0.417 -0.417m3.333 0V4.861a0.417 0.417 0 0 0 -0.417 -0.417h-1.389a0.417 0.417 0 0 0 -0.417 0.417V6.25a0.417 0.417 0 0 0 0.417 0.417h1.389a0.417 0.417 0 0 0 0.417 -0.417m-11.667 3.333V8.194a0.417 0.417 0 0 0 -0.417 -0.417H4.306a0.417 0.417 0 0 0 -0.417 0.417V9.583a0.417 0.417 0 0 0 0.417 0.417h1.389a0.417 0.417 0 0 0 0.417 -0.417m3.333 0V8.194a0.417 0.417 0 0 0 -0.417 -0.417H7.639a0.417 0.417 0 0 0 -0.417 0.417V9.583a0.417 0.417 0 0 0 0.417 0.417h1.389a0.417 0.417 0 0 0 0.417 -0.417m3.333 0V8.194a0.417 0.417 0 0 0 -0.417 -0.417h-1.389a0.417 0.417 0 0 0 -0.417 0.417V9.583a0.417 0.417 0 0 0 0.417 0.417h1.389a0.417 0.417 0 0 0 0.417 -0.417m3.333 0V8.194a0.417 0.417 0 0 0 -0.417 -0.417h-1.389a0.417 0.417 0 0 0 -0.417 0.417V9.583a0.417 0.417 0 0 0 0.417 0.417h1.389a0.417 0.417 0 0 0 0.417 -0.417m-11.667 3.333v-1.389a0.417 0.417 0 0 0 -0.417 -0.417H2.639a0.417 0.417 0 0 0 -0.417 0.417V12.917a0.417 0.417 0 0 0 0.417 0.417h1.389a0.417 0.417 0 0 0 0.417 -0.417m10 0v-1.389a0.417 0.417 0 0 0 -0.417 -0.417H5.973a0.417 0.417 0 0 0 -0.417 0.417V12.917a0.417 0.417 0 0 0 0.417 0.417h8.056a0.417 0.417 0 0 0 0.417 -0.417m3.333 0v-1.389a0.417 0.417 0 0 0 -0.417 -0.417h-1.389a0.417 0.417 0 0 0 -0.417 0.417V12.917a0.417 0.417 0 0 0 0.417 0.417h1.389a0.417 0.417 0 0 0 0.417 -0.417" transform="translate(2, 3)" />
            {children}
        </svg>
    );
};

const SilentTypingToggle: ChatBarButtonFactory = ({ isMainChat, channel }) => {
    const { isEnabled, showIcon, specificChats, disabledFor } = settings.use(["isEnabled", "showIcon", "specificChats", "disabledFor"]);
    const id = channel.guild_id ?? channel.id;

    const toggleGlobal = () => {
        settings.store.isEnabled = !settings.store.isEnabled;
    };
    const toggle = () => {
        if (specificChats) {
            if (!settings.store.isEnabled) {
                toggleGlobal();
            } else {
                const disabledChannels = getDisabledChannelsList(disabledFor);
                if (disabledChannels.includes(id)) {
                    disabledChannels.splice(disabledChannels.indexOf(id), 1);
                } else {
                    disabledChannels.push(id);
                }
                settings.store.disabledFor = disabledChannels.join(", ");
            }
        } else {
            toggleGlobal();
        }
    };
    const shouldEnable = isEnabled && (!specificChats || !getDisabledChannelsList(disabledFor).includes(id));

    let tooltip = shouldEnable ? "Disable Silent Typing" : "Enable Silent Typing";
    if (specificChats) {
        if (!isEnabled) {
            tooltip = "Re-enable Silent Typing globally";
        } else {
            const chatType = channel.guild_id ? "guild" : "user";
            tooltip = shouldEnable ? `Disable Silent Typing for current ${chatType} (right-click to toggle globally)`
                : `Enable Silent Typing for current ${chatType} (right-click to toggle globally)`;
        }
    }

    if (!isMainChat || !showIcon) return null;

    return (
        <ChatBarButton
            tooltip={tooltip}
            onClick={toggle}
            onContextMenu={toggleGlobal}
        >
            {shouldEnable ? (
                <SilentTypingEnabledIcon />
            ) : (
                <SilentTypingIcon>
                    {specificChats && !settings.store.isEnabled && (
                        <path
                            transform="matrix(0.27724514,0,0,0.27724514,34.252062,-35.543268)"
                            d="M 1827.701,303.065 698.835,1431.801 92.299,825.266 0,917.564 698.835,1616.4 1919.869,395.234 Z"
                            stroke="var(--green-500)"
                            strokeWidth="150" strokeLinecap="round"
                            fillRule="evenodd" />
                    )}
                </SilentTypingIcon>
            )}
        </ChatBarButton>
    );
};

function getDisabledChannelsList(list = settings.store.disabledFor) {
    try {
        return list.split(",").map(x => x.trim()).filter(Boolean);
    } catch (e) {
        settings.store.disabledFor = "";
        return [];
    }
}

function isEnabled(channelId: string) {
    if (!settings.store.isEnabled) return false;
    if (settings.store.specificChats) {
        // need to resolve guild id for guild channels
        const guildId = ChannelStore.getChannel(channelId)?.guild_id;
        return !getDisabledChannelsList().includes(guildId ?? channelId);
    }
    return true;
}

export default definePlugin({
    name: "SilentTyping",
    authors: [Devs.Ven, Devs.Rini, Devs.D3SOX],
    description: "Hide that you are typing",
    dependencies: ["ChatInputButtonAPI"],
    settings,

    patches: [
        {
            find: '.dispatch({type:"TYPING_START_LOCAL"',
            replacement: {
                match: /startTyping\(\i\){.+?},stop/,
                replace: "startTyping:$self.startTyping,stop"
            }
        },
    ],

    commands: [{
        name: "silenttype",
        description: "Toggle whether you're hiding that you're typing or not.",
        inputType: ApplicationCommandInputType.BUILT_IN,
        options: [
            {
                name: "value",
                description: "whether to hide or not that you're typing (default is toggle)",
                required: false,
                type: ApplicationCommandOptionType.BOOLEAN,
            },
        ],
        execute: async (args, ctx) => {
            settings.store.isEnabled = !!findOption(args, "value", !settings.store.isEnabled);
            sendBotMessage(ctx.channel.id, {
                content: settings.store.isEnabled ? "Silent typing enabled!" : "Silent typing disabled!",
            });
        },
    }],

    async startTyping(channelId: string) {
        if (isEnabled(channelId)) return;
        FluxDispatcher.dispatch({ type: "TYPING_START_LOCAL", channelId });
    },

    chatBarButton: {
        icon: SilentTypingIcon,
        render: SilentTypingToggle
    }
});
