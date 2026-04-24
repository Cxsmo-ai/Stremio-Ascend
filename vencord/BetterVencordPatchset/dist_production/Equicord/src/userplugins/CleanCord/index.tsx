/*
* Vencord, a Discord client mod
* Copyright (c) 2025 Vendicated and contributors*
* SPDX-License-Identifier: GPL-3.0-or-later
*/

import { definePluginSettings } from "@api/Settings";
import { Logger } from "@utils/Logger";
import definePlugin, { OptionType } from "@utils/types";
import { FluxDispatcher } from "@webpack/common";
import { React } from "@webpack/common";

import { HiddenItemsList } from "./hiddenItemsList";
import { CleanCordContext } from "./contextMenuComponents";
import { DiscordStores } from "./storesManager";

interface HiddenData {
    servers: string[];
    folders: string[];
}

const logger = new Logger("CleanCord");
let hiddenData: HiddenData = { servers: [], folders: [] };
let originalDispatch: any = null;
let stores: DiscordStores;
let originalQuickSwitcherGuildFunction: any = null;
let originalQuickSwitcherChannelFunction: any = null;

const settings = definePluginSettings({
    showOptions: {
        description: "Display the options upon right-clicking a server/folder",
        type: OptionType.BOOLEAN,
        default: true,
    },

    onlyHideInStream: {
        description: "Only hide servers/folders when in Streamer Mode",
        type: OptionType.BOOLEAN,
        default: false,
        onChange: (newValue: boolean) => {
            const plugin = Vencord.Plugins.plugins.CleanCord;
            if (plugin) {
                plugin.updateStreamerModeListener();
            }
            updateCSSClasses();
        }
    },

    hideInQuickSwitcher: {
        description: "Hide servers/folders in the Quick Switcher shortcut (Ctrl+K)",
        type: OptionType.BOOLEAN,
        default: true,
        onChange: (newValue: boolean) => {
            const plugin = Vencord.Plugins.plugins.CleanCord;
            if (plugin) {
                if (newValue) {
                    plugin.patchQuickSwitcher();
                } else {
                    plugin.unpatchQuickSwitcher();
                }
            }
        }
    },

    suppressionMode: {
        description: "Select how you want CleanCord to handle notifications from your hidden servers/folders",
        type: OptionType.SELECT,
        options: [
            { label: "Default - Keep initial Discord behaviour for notifications", value: "off" },
            { label: "Silent - Suppress all notifications coming from hidden servers/folders (Resets on startup)", value: "on" },
        ],
        default: "on",
        restartNeeded: true,
    },

    autoClearMentions: {
        description: "Automatically clear all unread badges from hidden servers/folders on startup (Recommended to use with 'Silent' mode)",
        type: OptionType.BOOLEAN,
        default: false,
        restartNeeded: true
    },

    // debugMode: {
    //     description: "Cool dev menu option B)",
    //     type: OptionType.BOOLEAN,
    //     default: false,
    // },

    hiddenServers: {
        type: OptionType.COMPONENT,
        component: () => {
            const [hiddenServers, setHiddenServers] = React.useState<string[]>([]);

            React.useEffect(() => {
                loadHiddenData();
                setHiddenServers([...hiddenData.servers]);
            }, []);

            const toggle = React.useCallback((serverId: string) => {
                const newItems = hiddenServers.includes(serverId)
                    ? hiddenServers.filter(id => id !== serverId)
                    : [...hiddenServers, serverId];
                setHiddenServers(newItems);
                hiddenData.servers = newItems;
                saveHiddenData();
                updateCSSClasses();
            }, [hiddenServers]);

            const clearAll = React.useCallback(() => {
                setHiddenServers([]);
                hiddenData.servers = [];
                saveHiddenData();
                updateCSSClasses();
            }, []);

            return React.createElement(HiddenItemsList, {
                type: "server",
                items: hiddenServers,
                onToggle: toggle,
                onClearAll: clearAll,
                onlyHideInStreamEnabled: settings.store.onlyHideInStream,
                description: "Manage hidden servers (Individually or with 'Unhide All')"
            });
        }
    },

    hiddenFolders: {
        type: OptionType.COMPONENT,
        component: () => {
            const [hiddenFolders, setHiddenFolders] = React.useState<string[]>([]);

            React.useEffect(() => {
                loadHiddenData();
                setHiddenFolders([...hiddenData.folders]);
            }, []);

            const toggle = React.useCallback((folderId: string) => {
                const newItems = hiddenFolders.includes(folderId)
                    ? hiddenFolders.filter(id => id !== folderId)
                    : [...hiddenFolders, folderId];
                setHiddenFolders(newItems);
                hiddenData.folders = newItems;
                saveHiddenData();
                updateCSSClasses();
            }, [hiddenFolders]);

            const clearAll = React.useCallback(() => {
                setHiddenFolders([]);
                hiddenData.folders = [];
                saveHiddenData();
                updateCSSClasses();
            }, []);

            return React.createElement(HiddenItemsList, {
                type: "folder",
                items: hiddenFolders,
                onToggle: toggle,
                onClearAll: clearAll,
                onlyHideInStreamEnabled: settings.store.onlyHideInStream,
                description: "Manage hidden folders (Individually or with 'Unhide All')"
            });
        }
    }
});

function loadHiddenData() {
    try {
        const storedServers = settings.store.hiddenServers;
        const storedFolders = settings.store.hiddenFolders;

        const servers = storedServers ? JSON.parse(storedServers) : [];
        const folders = storedFolders ? JSON.parse(storedFolders) : [];

        hiddenData = { servers, folders };
    } catch (e) {
        logger.error("Failed to load hidden data:", e);
        hiddenData = { servers: [], folders: [] };
    }
}

function saveHiddenData() {
    try {
        settings.store.hiddenServers = JSON.stringify(hiddenData.servers);
        settings.store.hiddenFolders = JSON.stringify(hiddenData.folders);
    } catch (e) {
        logger.error("Failed to save hidden data:", e);
    }
}

function toggleServer(serverId: string) {
    if (!serverId) return;

    const index = hiddenData.servers.indexOf(serverId);
    if (index > -1) {
        hiddenData.servers.splice(index, 1);
    } else {
        hiddenData.servers.push(serverId);
        if (settings.store.debugMode) {
            logger.info(`Hid server ${serverId}`);
        }
    }

    saveHiddenData();
    updateCSSClasses();
}

function toggleFolder(folderId: string) {
    if (!folderId) return;

    const index = hiddenData.folders.indexOf(folderId);
    if (index > -1) {
        hiddenData.folders.splice(index, 1);
    } else {
        hiddenData.folders.push(folderId);
        if (settings.store.debugMode) {
            logger.info(`Hid folder ${folderId}`);
        }
    }

    saveHiddenData();
    updateCSSClasses();
}

function shouldHideInQuickSwitcher(): boolean {
    if (!settings.store.hideInQuickSwitcher) return false;

    if (settings.store.onlyHideInStream) {
        return stores.isStreamingMode();
    }

    return true;
}

function isServerHidden(guildId: string): boolean {
    if (!guildId || !shouldHideInQuickSwitcher()) return false;

    if (hiddenData.servers.includes(guildId)) return true;

    const serversInHiddenFolders = getServersFromHiddenFolders();
    return serversInHiddenFolders.includes(guildId);
}

function patchQuickSwitcher() {
    if (!settings.store.hideInQuickSwitcher) return;

    try {
        const QuickSwitcherUtils = stores.getQuickSwitcherUtils();

        if (!QuickSwitcherUtils) {
            logger.warn("Could not find QuickSwitcher utils for patching");
            return;
        }

        if (QuickSwitcherUtils.queryGuilds && !originalQuickSwitcherGuildFunction) {
            originalQuickSwitcherGuildFunction = QuickSwitcherUtils.queryGuilds;

            QuickSwitcherUtils.queryGuilds = function(query: string, limit?: number) {
                const results = originalQuickSwitcherGuildFunction.call(this, query, limit);

                if (!shouldHideInQuickSwitcher()) return results;

                const filteredResults = results.filter((result: any) => {
                    if (!result || !result.record) return true;

                    const guildId = result.record.id || result.record.guild?.id;
                    const shouldHide = isServerHidden(guildId);

                    if (shouldHide && settings.store.debugMode) {
                        logger.info(`Filtered guild from quick switcher: ${result.record.name || guildId}`);
                    }

                    return !shouldHide;
                });

                return filteredResults;
            };
        }

        if (QuickSwitcherUtils.queryChannels && !originalQuickSwitcherChannelFunction) {
            originalQuickSwitcherChannelFunction = QuickSwitcherUtils.queryChannels;

            QuickSwitcherUtils.queryChannels = function(query: string, limit?: number) {
                const results = originalQuickSwitcherChannelFunction.call(this, query, limit);

                if (!shouldHideInQuickSwitcher()) return results;

                const filteredResults = results.filter((result: any) => {
                    if (!result || !result.record) return true;

                    const guildId = result.record.guild_id || result.record.guildId;
                    const shouldHide = isServerHidden(guildId);

                    if (shouldHide && settings.store.debugMode) {
                        logger.info(`Filtered channel from quick switcher: ${result.record.name || result.record.id} (guild: ${guildId})`);
                    }

                    return !shouldHide;
                });

                return filteredResults;
            };
        }

        logger.info("Successfully patched Quick Switcher");

    } catch (error) {
        logger.error("Failed to patch Quick Switcher:", error);
    }
}

function unpatchQuickSwitcher() {
    try {
        const QuickSwitcherUtils = stores.getQuickSwitcherUtils();

        if (QuickSwitcherUtils) {
            if (originalQuickSwitcherGuildFunction) {
                QuickSwitcherUtils.queryGuilds = originalQuickSwitcherGuildFunction;
                originalQuickSwitcherGuildFunction = null;
            }
            if (originalQuickSwitcherChannelFunction) {
                QuickSwitcherUtils.queryChannels = originalQuickSwitcherChannelFunction;
                originalQuickSwitcherChannelFunction = null;
            }
        }

        logger.info("Restored original Quick Switcher functions");
    } catch (error) {
        logger.error("Failed to unpatch Quick Switcher:", error);
    }
}

function getServersFromHiddenFolders(): string[] {
    return stores.getServersFromFolders(hiddenData.folders);
}

function shouldSuppressCheck(guildId: string): boolean {
    if (settings.store.suppressionMode === "off") return false;
    if (!guildId) return false;

    const isHiddenServer = hiddenData.servers.includes(guildId);
    const serversInHiddenFolders = getServersFromHiddenFolders();
    const isInHiddenFolder = serversInHiddenFolders.includes(guildId);
    const shouldSuppress = isHiddenServer || isInHiddenFolder;

    if (settings.store.onlyHideInStream) {
        const isStreaming = stores.isStreamingMode();
        return shouldSuppress && isStreaming;
    }

    return shouldSuppress;
}

function shouldSuppressMessage(action: any): { suppress: boolean; modifiedAction?: any } {
    if (!(settings.store.onlyHideInStream && !stores.isStreamingMode())) {

        if (!action || typeof action !== 'object') return { suppress: false };

        const message = action.message || action;

        // MESSAGE_CREATE (To Prevent : Unread badges, notification sounds and visual indicators)
        if (action.type === 'MESSAGE_CREATE') {

            if (settings.store.debugMode) {
                logger.info("[DEBUG] - MESSAGE_CREATE intercepted:", {
                    guildId: message.guild_id,
                    content: message
                });
            }

            if (message.guild_id && shouldSuppressCheck(message.guild_id)) {

                const currentGuildId = stores.getCurrentGuildId();
                if (message.guild_id === currentGuildId) {
                    logger.warn("Allowing unmodified MESSAGE_CREATE - User is in the server");
                    return { suppress: false };
                }

                const currentUserId = stores.getCurrentUserId();
                const guildMuted = stores.isGuildMuted(message.guild_id);

                const hasUserMentions = message.mentions?.length > 0 && currentUserId && message.mentions.some(m => m.id === currentUserId);
                const hasRoleMentions = message.mention_roles?.length > 0 && stores.hasMentionedRole(message.guild_id, message.mention_roles, currentUserId);
                const hasEveryoneMention = message.mention_everyone;

                const hasMentions = hasUserMentions || hasRoleMentions || hasEveryoneMention;

                if ((guildMuted && hasMentions) || !guildMuted) {
                    if (settings.store.debugMode) {
                        logger.info("MESSAGE_CREATE intercepted:", {
                            guildId: message.guild_id,
                            channelId: message.channel_id,
                            authorId: message.author?.id,
                            content: message.content?.substring(0, 50) + "...",
                            mentions: message.mentions?.length || 0,
                            mentionEveryone: message.mention_everyone,
                            mentionRoles: message.mention_roles,
                            hasUserMentions,
                            hasRoleMentions,
                            type: message.type,
                            flags: message.flags,
                            original_message: message
                        });
                    }

                    const modifiedAction = JSON.parse(JSON.stringify(action));
                    const modifiedMessage = modifiedAction.message || modifiedAction;

                    // Silent Flag 4096 = "1 << 12" - SUPPRESS_NOTIFICATIONS
                    // https://docs.discord.com/developers/resources/messages
                    modifiedMessage.flags = (modifiedMessage.flags || 0) | 1 << 12;

                    // Mark the message as already read to prevent unread badges
                    // We dispatch a MESSAGE_ACK after the message is processed
                    setTimeout(() => {
                        try {
                            FluxDispatcher.dispatch({
                                type: "MESSAGE_ACK",
                                channelId: modifiedMessage.channel_id,
                                messageId: modifiedMessage.id,
                                version: Date.now(),
                                isExplicit: false
                            });
                        } catch (ackError) {
                            if (settings.store.debugMode) {
                                logger.error("Failed to auto-ACK hidden server message:", ackError);
                            }
                        }
                    }, 0);

                    if (settings.store.debugMode) {
                        const isDirectlyHidden = hiddenData.servers.includes(message.guild_id);
                        const reason = isDirectlyHidden ? "hidden server" : "server in hidden folder";
                        logger.info(`Modifying message from ${reason} to appear muted`, {
                            channel: message.channel_id,
                            everyone: message.mention_everyone,
                            roles: message.mention_roles,
                            guildId: message.guild_id,
                            guildMuted: guildMuted,
                            mentioned: hasUserMentions,
                            roleMentioned: hasRoleMentions,
                            originalFlags: message.flags,
                            newFlags: modifiedMessage.flags
                        });
                    }

                    return { suppress: false, modifiedAction };
                }
            }
        }
    }

    return { suppress: false };
}

function clearHiddenMentions() {
    if (!settings.store.autoClearMentions) {
        return;
    }

    if (!(settings.store.onlyHideInStream && !stores.isStreamingMode())) {
        try {
            const missingStores = stores.validateStores();
            if (missingStores.length > 0) {
                logger.error("Required stores not found for clearing mentions:", missingStores);
                return;
            }

            const serversInHiddenFolders = getServersFromHiddenFolders();
            const allHiddenServerIds = [...new Set([...hiddenData.servers, ...serversInHiddenFolders])];

            if (allHiddenServerIds.length === 0) {
                logger.info("No hidden servers/folders found - nothing to clear !");
                return;
            }

            const channelsToAck: Array<{
                channelId: string;
                messageId: string | null;
                readStateType: number;
            }> = [];

            let totalChannelsChecked = 0;
            let serversProcessed = 0;

            allHiddenServerIds.forEach(guildId => {
                if (!guildId) return;

                try {
                    const guild = stores.getGuild(guildId);
                    if (!guild) {
                        if (settings.store.debugMode) {
                            logger.warn(`Guild ${guildId} not found in GuildStore`);
                        }
                        return;
                    }
                    serversProcessed++;

                    const channels = stores.getGuildChannels(guildId);

                    if (settings.store.debugMode) {
                        logger.info(`Processing guild ${guild.name || guildId}: found ${channels.length} channels`);
                    }

                    channels.forEach((channel: any) => {
                        if (!channel?.id || channel.id === guildId) return;

                        totalChannelsChecked++;

                        const guildMuted = stores.isGuildMuted(guildId);

                        if (guildMuted) {
                            const mentionCount = stores.getMentionCount(channel.id);

                            if (mentionCount > 0) {
                                const lastMessageId = stores.getLastMessageId(channel.id);

                                channelsToAck.push({
                                    channelId: channel.id,
                                    messageId: lastMessageId,
                                    readStateType: 0
                                });

                                if (settings.store.debugMode) {
                                    logger.info("Found mentions in muted guild channel :", {
                                        channelName: channel.name,
                                        channelId: channel.id,
                                        mentionCount: mentionCount,
                                        lastMessageId: lastMessageId
                                    });
                                }
                            }
                        } else {
                            const hasUnread = stores.hasUnread(channel.id);
                            const mentionCount = stores.getMentionCount(channel.id);

                            if (hasUnread || mentionCount > 0) {
                                const lastMessageId = stores.getLastMessageId(channel.id);

                                channelsToAck.push({
                                    channelId: channel.id,
                                    messageId: lastMessageId,
                                    readStateType: 0
                                });

                                if (settings.store.debugMode) {
                                    logger.info("Found unread in unmuted guild channel :", {
                                        channelName: channel.name,
                                        channelId: channel.id,
                                        mentionCount: mentionCount,
                                        hasUnread: hasUnread,
                                        lastMessageId: lastMessageId
                                    });
                                }
                            }
                        }
                    });

                } catch (guildError) {
                    if (settings.store.debugMode) {
                        logger.error(`Error processing guild ${guildId}:`, guildError);
                    }
                }
            });

            if (settings.store.debugMode) {
                logger.info(`Processed ${serversProcessed} servers, checked ${totalChannelsChecked} channels, found ${channelsToAck.length} channels to acknowledge`);
            }

            if (channelsToAck.length > 0) {
                try {
                    FluxDispatcher.dispatch({
                        type: "BULK_ACK",
                        context: "APP",
                        channels: channelsToAck
                    });

                    logger.info(`Successfully dispatched BULK_ACK for ${channelsToAck.length} channels from hidden servers/folders`);
                } catch (bulkError) {
                    if (settings.store.debugMode) {
                        logger.warn("BULK_ACK failed, falling back to individual MESSAGE_ACK events:", bulkError);
                    }

                    let successCount = 0;
                    channelsToAck.forEach(({ channelId, messageId }) => {
                        try {
                            if (messageId) {
                                FluxDispatcher.dispatch({
                                    type: "MESSAGE_ACK",
                                    channelId: channelId,
                                    messageId: messageId,
                                    version: Date.now()
                                });
                                successCount++;
                            }
                        } catch (ackError) {
                            if (settings.store.debugMode) {
                                logger.error(`Individual ACK (also) failed for channel ${channelId}:`, ackError);
                            }
                        }
                    });

                    if (successCount > 0) {
                        logger.info(`Successfully dispatched ${successCount} individual MESSAGE_ACK events`);
                    }
                }
            } else {
                logger.info("There's nothing to clear from hidden servers/folders !");
            }

        } catch (error) {
            if (settings.store.debugMode) {
                logger.error("Mentions clearing failed :", error);
            }
        }
    } else {
        if (settings.store.debugMode) {
            logger.warn(`Skipping mentions clearing - "onlyHideInStream" is ON but Streamer Mode is OFF !`);
        }
    }
}

function patchFluxDispatcher() {
    if (!FluxDispatcher || originalDispatch) return;

    try {
        originalDispatch = FluxDispatcher.dispatch;
        FluxDispatcher.dispatch = function(action: any) {
            const suppressionResult = shouldSuppressMessage(action);
            if (suppressionResult.suppress) {
                return Promise.resolve();
            }

            const actionToDispatch = suppressionResult.modifiedAction || action;
            const result = originalDispatch.call(this, actionToDispatch);

            if (result && typeof result.then === 'function') {
                return result;
            } else {
                return Promise.resolve(result);
            }
        };

        logger.info("Successfully patched FluxDispatcher for mention suppression");
    } catch (error) {
        logger.error("Failed to patch FluxDispatcher:", error);
    }
}

function unpatchFluxDispatcher() {
    if (!FluxDispatcher || !originalDispatch) return;
    try {
        FluxDispatcher.dispatch = originalDispatch;
        originalDispatch = null;
        logger.info("Restored original FluxDispatcher");
    } catch (error) {
        logger.error("Failed to restore FluxDispatcher:", error);
    }
}


const CSS_ELEMENT_ID = 'clean-cord-dynamic-styles';
function updateCSSClasses() {
    const shouldHide = !settings.store.onlyHideInStream || stores.isStreamingMode();
    document.documentElement.setAttribute('data-clean-cord-enabled', shouldHide.toString());

    let styleElement = document.getElementById(CSS_ELEMENT_ID) as HTMLStyleElement;
    if (!styleElement) {
        styleElement = document.createElement('style');
        styleElement.id = CSS_ELEMENT_ID;
        document.head.appendChild(styleElement);
    }

    if (!shouldHide) {
        styleElement.textContent = '';
        return;
    }

    const cssRules: string[] = [];

    hiddenData.servers.forEach(serverId => {
        cssRules.push(
            `html[data-clean-cord-enabled="true"] .listItem__650eb:has([data-list-item-id="guildsnav___${serverId}"]) { display: none !important; }`,
            `html[data-clean-cord-enabled="true"] [class*="-listItem"]:has([data-list-item-id="guildsnav___${serverId}"]) { display: none !important; }`,
            `html[data-clean-cord-enabled="true"] [data-list-item-id="guildsnav___${serverId}"] { display: none !important; }`,
            `html[data-clean-cord-enabled="true"] .folderPreviewGuildIcon__48112[style*="${serverId}"] { display: none !important; }`,
            `html[data-clean-cord-enabled="true"] .folderPreviewGuildIcon__48112[style*="icons/${serverId}/"] { display: none !important; }`
        );
    });

    hiddenData.folders.forEach(folderId => {
        cssRules.push(
            `html[data-clean-cord-enabled="true"] .listItem__650eb:has([data-list-item-id*="${folderId}"]) { display: none !important; }`,
            `html[data-clean-cord-enabled="true"] [class*="-listItem"]:has([data-list-item-id*="${folderId}"]) { display: none !important; }`,
            `html[data-clean-cord-enabled="true"] [data-list-item-id*="${folderId}"] { display: none !important; }`,
            `html[data-clean-cord-enabled="true"] .folderGroup__48112:has([data-list-item-id*="${folderId}"]) { display: none !important; }`,
            `html[data-clean-cord-enabled="true"] [class*="-folderGroup"]:has([data-list-item-id*="${folderId}"]) { display: none !important; }`
        );

        try {
            const guildFolders = stores.getGuildFolders();

            guildFolders.forEach((folder: any) => {
                const folderId = folder.folderId || folder.id;

                if (hiddenData.folders.includes(folderId)) return;

                const hasHiddenServers = folder.guildIds?.some((guildId: string) =>
                    hiddenData.servers.includes(guildId)
                );

                if (hasHiddenServers) {

                    // Count servers that are NOT currently hidden
                    const folderHeight = folder.guildIds.filter((guildId: string) => !hiddenData.servers.includes(guildId)).length;

                    if (folderHeight > 0) {
                        cssRules.push(
                            `html[data-clean-cord-enabled="true"] .folderGroup__48112.isExpanded__48112:has([data-list-item-id*="${folderId}"]) { height: calc((${folderHeight} * var(--guildbar-folder-size)) + var(--guildbar-folder-size)) !important; }`,
                            `html[data-clean-cord-enabled="true"] [class*="-folderGroup"][class*="-isExpanded"]:has([data-list-item-id*="${folderId}"]) { height: calc((${folderHeight} * var(--guildbar-folder-size)) + var(--guildbar-folder-size)) !important; }`
                            // We now use "--guildbar-folder-size" already defined in the :root of Discord
                            // In the case they change the servers icons' size within folders, now this value won't be hard-coded in the calculations
                            // + --guildbar-folder-size to account for the server we're hiding
                        );
                    }
                }
            });
        } catch (error) {
            if (settings.store.debugMode) {
                logger.error("Failure for CSS adjustments:", error);
            }
        }
    });

    styleElement.textContent = cssRules.join('\n');
}

export default definePlugin({
    name: "CleanCord",
    description: "Allows you to hide specific servers and folders from your Discord server list with various settings",
    authors: [{ name: "Tetra_Sky", id: 406453997294190594n }],
    settings,

    streamerModeListener: null as (() => void) | null,

    start() {
        stores = DiscordStores.getInstance();

        loadHiddenData();
        this.updateStreamerModeListener();
        updateCSSClasses();

        if (settings.store.suppressionMode !== "off") {
            this.patchFluxDispatcher();
            if (settings.store.autoClearMentions) {
                this.clearHiddenMentions();
            }
        } else {
            this.unpatchFluxDispatcher();
        }

        if (settings.store.hideInQuickSwitcher) {
            this.patchQuickSwitcher();
        }
    },

    stop() {
        this.removeStreamerModeListener();
        this.unpatchFluxDispatcher();
        this.unpatchQuickSwitcher();

        const styleElement = document.getElementById(CSS_ELEMENT_ID);
        if (styleElement) {
            styleElement.remove();
        }

        document.documentElement.removeAttribute('data-clean-cord-enabled');
    },

    isStreamingMode() {
        return stores.isStreamingMode();
    },

    updateStreamerModeListener() {
        this.removeStreamerModeListener();
        if (settings.store.onlyHideInStream && stores.StreamerModeStore) {
            this.streamerModeListener = () => updateCSSClasses();
            stores.StreamerModeStore.addChangeListener(this.streamerModeListener);
        }
    },

    removeStreamerModeListener() {
        if (stores.StreamerModeStore && this.streamerModeListener) {
            stores.StreamerModeStore.removeChangeListener(this.streamerModeListener);
            this.streamerModeListener = null;
        }
    },

    patchFluxDispatcher() {
        patchFluxDispatcher();
    },

    unpatchFluxDispatcher() {
        unpatchFluxDispatcher();
    },

    patchQuickSwitcher() {
        patchQuickSwitcher();
    },

    unpatchQuickSwitcher() {
        unpatchQuickSwitcher();
    },

    clearHiddenMentions() {
        clearHiddenMentions();
    },

    contextMenus: {
        "guild-context": CleanCordContext(() => hiddenData, settings, toggleServer, toggleFolder)
    }
});
