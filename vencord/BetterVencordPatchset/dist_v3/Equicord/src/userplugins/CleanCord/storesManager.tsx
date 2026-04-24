/*
* Vencord, a Discord client mod
* Copyright (c) 2025 Vendicated and contributors
* SPDX-License-Identifier: GPL-3.0-or-later
*
* Centralized Discord store management file
* Handles lazy initialization and helper methods
*
* Way easier to deploy a fix when something changes with stores on Discord's end
*/

import { Logger } from "@utils/Logger";

const logger = new Logger("CleanCord:StoresManager");

export class DiscordStores {
    private static _instance: DiscordStores | null = null;
    private _initialized = false;

    public SortedGuildStore: any = null;
    public GuildStore: any = null;
    public ChannelStore: any = null;
    public GuildChannelStore: any = null;
    public ReadStateStore: any = null;
    public UserStore: any = null;
    public SelectedGuildStore: any = null;
    public UserGuildSettingsStore: any = null;
    public StreamerModeStore: any = null;
    public QuickSwitcherUtils: any = null;
    public GuildMemberStore: any = null;

    private constructor() {
        // Lazily initialization
    }

    private initializeStores(): void {
        if (this._initialized || typeof Vencord === 'undefined') return;

        try {
            logger.info("Initializing Discord stores...");

            this.SortedGuildStore = Vencord.Webpack.findStore("SortedGuildStore");
            this.GuildStore = Vencord.Webpack.findStore("GuildStore") || Vencord.Webpack.findByProps("getGuild", "getGuilds");
            this.ChannelStore = Vencord.Webpack.findStore("ChannelStore") || Vencord.Webpack.findByProps("getChannel", "getChannels");
            this.GuildChannelStore = Vencord.Webpack.findStore("GuildChannelStore") || Vencord.Webpack.findByProps("getChannels", "getSelectableChannels");
            this.ReadStateStore = Vencord.Webpack.findStore("ReadStateStore") || Vencord.Webpack.findByProps("hasUnread", "getMentionCount");
            this.UserStore = Vencord.Webpack.findStore("UserStore");
            this.SelectedGuildStore = Vencord.Webpack.findStore("SelectedGuildStore");
            this.UserGuildSettingsStore = Vencord.Webpack.findStore("UserGuildSettingsStore") || Vencord.Webpack.findByProps("getGuildSettings", "isMuted") || Vencord.Webpack.findByProps("getUserGuildSettings");
            this.StreamerModeStore = Vencord.Webpack.findStore("StreamerModeStore") ||  Vencord.Webpack.getByProps("StreamerModeStore")?.StreamerModeStore;
            this.QuickSwitcherUtils = Vencord.Webpack.findByProps("queryGuilds", "queryChannels");
            this.GuildMemberStore = Vencord.Webpack.findStore("GuildMemberStore") || Vencord.Webpack.findByProps("getMember", "getMembers");

            this._initialized = true;
            logger.info("Discord stores initialized successfully");

            // REMINDER : 5 names per line
            const storeNames = [
                'SortedGuildStore', 'GuildStore', 'ChannelStore', 'GuildChannelStore', 'ReadStateStore',
                'UserStore', 'SelectedGuildStore', 'UserGuildSettingsStore', 'StreamerModeStore', 'QuickSwitcherUtils',
                'GuildMemberStore'
            ];

            const failedStores = storeNames.filter(name => !this[name]);
            if (failedStores.length > 0) {
                logger.warn("Failed to initialize stores:", failedStores);
            }

        } catch (error) {
            logger.error("Failed to initialize Discord stores:", error);
        }
    }

    public static getInstance(): DiscordStores {
        if (!DiscordStores._instance) {
            DiscordStores._instance = new DiscordStores();
        }
        DiscordStores._instance.initializeStores();
        return DiscordStores._instance;
    }

    public reinitialize(): void {
        this._initialized = false;
        this.initializeStores();
    }

    public get isInitialized(): boolean {
        return this._initialized;
    }

    public getCurrentUserId(): string | null {
        this.initializeStores();
        return this.UserStore?.getCurrentUser()?.id || null;
    }

    public getCurrentGuildId(): string | null {
        this.initializeStores();
        return this.SelectedGuildStore?.getGuildId() || null;
    }

    public getGuildFolders(): any[] {
        this.initializeStores();
        return this.SortedGuildStore?.getGuildFolders?.() || [];
    }

    public isGuildMuted(guildId: string): boolean {
        this.initializeStores();

        if (!guildId) return false;

        try {
            // Try UserGuildSettingsStore first
            if (this.UserGuildSettingsStore?.isMuted &&
                typeof this.UserGuildSettingsStore.isMuted === 'function') {
                return this.UserGuildSettingsStore.isMuted(guildId);
            }

            return false;
        } catch (error) {
            logger.warn(`Could not determine mute status for guild ${guildId}:`, error);
            return false;
        }
    }

    public getGuildChannels(guildId: string): any[] {
        this.initializeStores();

        if (!guildId || !this.GuildChannelStore?.getChannels) return [];

        try {
            const guildChannels = this.GuildChannelStore.getChannels(guildId);
            if (guildChannels?.SELECTABLE) {
                return guildChannels.SELECTABLE
                    .map((item: any) => item.channel)
                    .filter(Boolean);
            }
        } catch (error) {
            logger.warn(`Could not get channels for guild ${guildId}:`, error);
        }

        return [];
    }

    public isStreamingMode(): boolean {
        this.initializeStores();

        try {
            return this.StreamerModeStore?.enabled || false;
        } catch (error) {
            logger.error("Error checking streamer mode:", error);
            return false;
        }
    }

    public getGuild(guildId: string): any {
        this.initializeStores();
        return this.GuildStore?.getGuild?.(guildId) || null;
    }

    public getMentionCount(channelId: string): number {
        this.initializeStores();
        return this.ReadStateStore?.getMentionCount?.(channelId) || 0;
    }

    public hasUnread(channelId: string): boolean {
        this.initializeStores();
        return this.ReadStateStore?.hasUnread?.(channelId) || false;
    }

    public getLastMessageId(channelId: string): string | null {
        this.initializeStores();
        return this.ReadStateStore?.lastMessageId?.(channelId) || null;
    }

    public getServersFromFolders(folderIds: string[]): string[] {
        const serversInFolders: string[] = [];

        try {
            const guildFolders = this.getGuildFolders();

            folderIds.forEach(folderId => {
                const folder = guildFolders.find((folder: any) =>
                    folder.folderId === folderId || folder.id === folderId
                );

                if (folder?.guildIds) {
                    folder.guildIds.forEach((guildId: string) => {
                        if (guildId && !serversInFolders.includes(guildId)) {
                            serversInFolders.push(guildId);
                        }
                    });
                }
            });
        } catch (error) {
            logger.error("Error getting servers from folders:", error);
        }

        return serversInFolders;
    }

    public getQuickSwitcherUtils(): any {
        this.initializeStores();
        return this.QuickSwitcherUtils;
    }

    public getUserRoles(guildId: string, userId?: string): string[] {
        this.initializeStores();

        if (!guildId) return [];

        try {
            const targetUserId = userId || this.getCurrentUserId();
            if (!targetUserId) return [];

            if (this.GuildMemberStore?.getMember) {
                const member = this.GuildMemberStore.getMember(guildId, targetUserId);
                if (member?.roles) {
                    return Array.isArray(member.roles) ? member.roles : [];
                }
            }

            return [];
        } catch (error) {
            logger.warn(`Could not get roles for user ${userId} in guild ${guildId}:`, error);
            return [];
        }
    }

    public hasMentionedRole(guildId: string, mentionedRoles: string[], userId?: string): boolean {
        if (!guildId || !mentionedRoles || mentionedRoles.length === 0) return false;

        try {
            const userRoles = this.getUserRoles(guildId, userId);
            return mentionedRoles.some(roleId => userRoles.includes(roleId));
        } catch (error) {
            logger.warn(`Could not check role mentions for guild ${guildId}:`, error);
            return false;
        }
    }

    public validateStores(): string[] {
        this.initializeStores();

        const requiredStores = {
            SortedGuildStore: this.SortedGuildStore,
            GuildStore: this.GuildStore,
            ReadStateStore: this.ReadStateStore,
            UserStore: this.UserStore,
            SelectedGuildStore: this.SelectedGuildStore
        };

        return Object.entries(requiredStores)
            .filter(([name, store]) => !store)
            .map(([name]) => name);
    }

    public getDiagnostics() {
        return {
            initialized: this._initialized,
            vencordAvailable: typeof Vencord !== 'undefined',
            missingStores: this.validateStores(),
            currentUserId: this.getCurrentUserId(),
            currentGuildId: this.getCurrentGuildId(),
            isStreaming: this.isStreamingMode(),
            quickSwitcherAvailable: this.getQuickSwitcherUtils()
        };
    }
}
